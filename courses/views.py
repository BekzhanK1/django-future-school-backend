from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from .models import Course, SubjectGroup, CourseSection
from .serializers import (
    CourseSerializer, SubjectGroupSerializer, CourseSectionSerializer,
    AutoCreateWeekSectionsSerializer, CourseFullSerializer
)
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from learning.role_permissions import RoleBasedPermission
from users.models import UserRole


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['grade']
    search_fields = ['course_code', 'name', 'description']
    ordering_fields = ['course_code', 'name', 'grade']
    ordering = ['course_code']

    @action(detail=False, methods=['get'], url_path='full')
    def full(self, request):
        """Return all courses with their associated subject groups"""
        queryset = Course.objects.prefetch_related(
            'subject_groups__classroom', 'subject_groups__teacher').all()
        serializer = CourseFullSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='sync-content')
    def sync_content(self, request, pk=None):
        """
        Sync template CourseSections, Resources, and Assignments from this Course
        into all SubjectGroups of the course.

        Usage:
        - Prepare template sections for the Course (CourseSection with course set, subject_group null).
        - Call POST /api/courses/{id}/sync-content/ to propagate content to all SubjectGroups.
        """
        from datetime import date, timedelta, datetime
        from django.utils import timezone
        from learning.models import Resource, Assignment, AssignmentAttachment

        course = self.get_object()

        # Academic year start date: can be provided explicitly or inferred
        academic_start_str = request.data.get("academic_start_date")

        def infer_academic_start(today: date) -> date:
            """
            Infer academic year start date if not explicitly provided.
            Simplest rule: Sep 1 of the academic year that contains 'today'
            (Sep 1..Dec 31 belong to this year, Jan 1..Aug 31 belong to previous).
            """
            if today.month >= 9:
                year = today.year
            else:
                year = today.year - 1
            return date(year, 9, 1)

        today = timezone.now().date()
        if academic_start_str:
            try:
                academic_start_date = date.fromisoformat(academic_start_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid academic_start_date, expected YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            academic_start_date = infer_academic_start(today)

        # 1) Get template sections for this course (subject_group is null)
        template_sections = CourseSection.objects.filter(
            course=course,
            subject_group__isnull=True,
        ).order_by("position", "id")

        if not template_sections.exists():
            return Response(
                {"detail": "No template sections found for this course."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) For each SubjectGroup of this course, ensure derived sections & content exist
        subject_groups = course.subject_groups.all()

        if not subject_groups.exists():
            return Response(
                {"detail": "No subject groups found for this course. Please create at least one subject group before syncing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def clone_resource_tree(template_res: Resource, target_section: CourseSection, parent: Resource | None):
            """
            Recursively clone a template resource and its children into target_section.
            Updates existing resources if they are linked to the template.
            """
            # Check if a clone already exists for this template in this section
            existing = Resource.objects.filter(
                course_section=target_section,
                template_resource=template_res,
            ).first()

            if existing:
                # Update existing resource if it's not unlinked from template
                if not existing.is_unlinked_from_template:
                    existing.type = template_res.type
                    existing.title = template_res.title
                    existing.description = template_res.description
                    existing.url = template_res.url
                    # Update file if template has a file (copy the file reference)
                    if template_res.file:
                        existing.file = template_res.file
                    existing.position = template_res.position
                    existing.save(update_fields=[
                        'type', 'title', 'description', 'url', 'file', 'position'
                    ])

                clone = existing
            else:
                # Create new clone
                clone = Resource.objects.create(
                    course_section=target_section,
                    parent_resource=parent,
                    template_resource=template_res,
                    type=template_res.type,
                    title=template_res.title,
                    description=template_res.description,
                    url=template_res.url,
                    file=template_res.file,
                    position=template_res.position,
                )

            # Sync children (recursively)
            for child in template_res.children.all().order_by("position", "id"):
                clone_resource_tree(child, target_section, clone)

            return clone

        for sg in subject_groups:
            # Remove automatically created sections that are not linked to templates
            # These were created by the signal when SubjectGroup was created
            # We'll replace them with template-derived sections
            CourseSection.objects.filter(
                subject_group=sg,
                template_section__isnull=True,
                course__isnull=True
            ).delete()

            # For each template section, ensure a derived section for this SubjectGroup exists
            for tmpl_sec in template_sections:
                derived_sec, created = CourseSection.objects.get_or_create(
                    subject_group=sg,
                    template_section=tmpl_sec,
                    defaults={
                        "course": None,
                        "title": tmpl_sec.title,
                        "is_general": tmpl_sec.is_general,
                        "position": tmpl_sec.position,
                        # start_date/end_date will be computed below
                    },
                )

                # Compute concrete section dates based on template-relative fields
                if derived_sec.start_date is None or created:
                    # Determine offset in days from academic_start_date
                    offset_days = None
                    if tmpl_sec.template_start_offset_days is not None:
                        offset_days = tmpl_sec.template_start_offset_days
                    elif tmpl_sec.template_week_index is not None:
                        offset_days = tmpl_sec.template_week_index * 7

                    if offset_days is not None:
                        start_date = academic_start_date + \
                            timedelta(days=offset_days)
                        duration = tmpl_sec.template_duration_days
                        if not duration and tmpl_sec.start_date and tmpl_sec.end_date:
                            duration = (tmpl_sec.end_date -
                                        tmpl_sec.start_date).days + 1
                        if not duration:
                            duration = 7
                        end_date = start_date + timedelta(days=duration - 1)
                        derived_sec.start_date = start_date
                        derived_sec.end_date = end_date
                        derived_sec.save(
                            update_fields=["start_date", "end_date"])
                    else:
                        # Fallback: copy absolute dates if template-relative data is missing
                        if tmpl_sec.start_date and tmpl_sec.end_date:
                            derived_sec.start_date = tmpl_sec.start_date
                            derived_sec.end_date = tmpl_sec.end_date
                            derived_sec.save(
                                update_fields=["start_date", "end_date"])

                # Sync resources: clone missing template resources into derived section
                tmpl_resources = Resource.objects.filter(
                    course_section=tmpl_sec,
                    parent_resource__isnull=True,
                ).order_by("position", "id")

                for tmpl_res in tmpl_resources:
                    clone_resource_tree(tmpl_res, derived_sec, parent=None)

                # Sync assignments: one-to-one mapping via template_assignment
                tmpl_assignments = Assignment.objects.filter(
                    course_section=tmpl_sec,
                    template_assignment__isnull=True,  # Only root template assignments
                ).order_by("due_at", "id")
                for tmpl_asg in tmpl_assignments:
                    derived_asg = Assignment.objects.filter(
                        course_section=derived_sec,
                        template_assignment=tmpl_asg,
                    ).first()

                    # Calculate due_at based on template-relative fields if available
                    due_at = tmpl_asg.due_at
                    if (
                        derived_sec.start_date
                        and tmpl_asg.template_offset_days_from_section_start is not None
                        and tmpl_asg.template_due_time is not None
                    ):
                        due_date = derived_sec.start_date + timedelta(
                            days=tmpl_asg.template_offset_days_from_section_start
                        )
                        due_at = datetime.combine(
                            due_date,
                            tmpl_asg.template_due_time,
                            tzinfo=timezone.get_current_timezone(),
                        )

                    if derived_asg:
                        # Update existing assignment if it's not unlinked from template
                        if not derived_asg.is_unlinked_from_template:
                            derived_asg.title = tmpl_asg.title
                            derived_asg.description = tmpl_asg.description
                            derived_asg.due_at = due_at
                            derived_asg.max_grade = tmpl_asg.max_grade
                            # Update file if template has a file
                            if tmpl_asg.file:
                                derived_asg.file = tmpl_asg.file
                            derived_asg.save(update_fields=[
                                'title', 'description', 'due_at', 'max_grade', 'file'
                            ])

                            # Sync attachments: remove old ones and create new ones
                            # (or update if they match by position/type)
                            existing_attachments = list(
                                derived_asg.attachments.all())
                            template_attachments = list(
                                tmpl_asg.attachments.all().order_by("position", "id"))

                            # Remove attachments that no longer exist in template
                            for existing_att in existing_attachments:
                                if not any(
                                    ta.position == existing_att.position and
                                    ta.type == existing_att.type
                                    for ta in template_attachments
                                ):
                                    existing_att.delete()

                            # Create or update attachments
                            for att in template_attachments:
                                existing_att = derived_asg.attachments.filter(
                                    position=att.position,
                                    type=att.type
                                ).first()

                                if existing_att:
                                    # Update existing attachment
                                    existing_att.title = att.title
                                    existing_att.content = att.content
                                    existing_att.file_url = att.file_url
                                    if att.file and not existing_att.file:
                                        existing_att.file = att.file
                                    existing_att.save()
                                else:
                                    # Create new attachment
                                    AssignmentAttachment.objects.create(
                                        assignment=derived_asg,
                                        type=att.type,
                                        title=att.title,
                                        content=att.content,
                                        file_url=att.file_url,
                                        file=att.file,
                                        position=att.position,
                                    )
                    else:
                        # Create new assignment
                        derived_asg = Assignment.objects.create(
                            course_section=derived_sec,
                            template_assignment=tmpl_asg,
                            teacher=tmpl_asg.teacher,
                            title=tmpl_asg.title,
                            description=tmpl_asg.description,
                            due_at=due_at,
                            max_grade=tmpl_asg.max_grade,
                            file=tmpl_asg.file,
                        )
                        # Clone attachments
                        for att in tmpl_asg.attachments.all().order_by("position", "id"):
                            AssignmentAttachment.objects.create(
                                assignment=derived_asg,
                                type=att.type,
                                title=att.title,
                                content=att.content,
                                file_url=att.file_url,
                                file=att.file,
                                position=att.position,
                            )

        # Count what was synced
        total_sections = sum(
            1 for sg in subject_groups for _ in template_sections)
        total_resources = sum(
            len(Resource.objects.filter(
                course_section=tmpl_sec, parent_resource__isnull=True))
            for tmpl_sec in template_sections
        )
        total_assignments = sum(
            len(Assignment.objects.filter(
                course_section=tmpl_sec, template_assignment__isnull=True))
            for tmpl_sec in template_sections
        )

        return Response(
            {
                "detail": f"Content synced successfully to {len(subject_groups)} subject group(s). "
                f"Created {total_sections} section(s), synced {total_resources} resource(s), "
                f"and {total_assignments} assignment(s)."
            },
            status=status.HTTP_200_OK,
        )


class SubjectGroupViewSet(viewsets.ModelViewSet):
    queryset = SubjectGroup.objects.select_related(
        'course', 'classroom', 'teacher').all()
    serializer_class = SubjectGroupSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'classroom', 'teacher']
    search_fields = ['course__name', 'course__course_code',
                     'classroom__letter', 'teacher__username']
    ordering_fields = ['course__name', 'classroom__grade', 'classroom__letter']
    ordering = ['course__name', 'classroom__grade', 'classroom__letter']

    def get_permissions(self):
        # Keep SubjectGroup management for superadmins only, but allow role-based access to the
        # read-only `members` endpoint.
        if getattr(self, 'action', None) == 'members':
            return [IsTeacherOrAbove()]  # teachers, school admins, superadmins
        return super().get_permissions()

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        """Return teacher and students of a subject group.

        Access rules:
        - Teacher: only for their own subject group
        - School admin: subject groups in their school
        - Superadmin: any subject group
        - Student: can view only if belongs to the classroom of the subject group
        """
        try:
            subject_group = SubjectGroup.objects.select_related(
                'course', 'classroom', 'teacher', 'classroom__school').get(id=pk)
        except SubjectGroup.DoesNotExist:
            return Response({'error': 'Subject group not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # Role-based visibility checks
        if user.role == UserRole.TEACHER:
            if subject_group.teacher_id != user.id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        elif user.role == UserRole.SCHOOLADMIN:
            if subject_group.classroom.school_id != getattr(user.school, 'id', None):
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        elif user.role == UserRole.STUDENT:
            # Student must belong to the classroom
            is_in_classroom = user.classroom_users.filter(
                classroom_id=subject_group.classroom_id).exists()
            if not is_in_classroom:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        # Superadmin: allowed

        # Build response
        teacher = subject_group.teacher
        teacher_payload = None
        if teacher is not None:
            teacher_payload = {
                'id': teacher.id,
                'username': teacher.username,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'email': teacher.email,
            }

        # Fetch students of the classroom
        students_qs = subject_group.classroom.classroom_users.select_related('user').filter(
            user__role=UserRole.STUDENT
        )
        students = []
        for cu in students_qs:
            u = cu.user
            students.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'email': u.email,
            })

        data = {
            'subject_group': {
                'id': subject_group.id,
                'course_id': subject_group.course_id,
                'course_code': subject_group.course.course_code,
                'course_name': subject_group.course.name,
                'classroom': str(subject_group.classroom),
            },
            'teacher': teacher_payload,
            'students': students,
        }
        return Response(data)


class CourseSectionViewSet(viewsets.ModelViewSet):
    queryset = CourseSection.objects.select_related('subject_group', 'course').prefetch_related(
        'resources__children__children__children',  # Support up to 3 levels deep
        'assignments__teacher',
        'assignments__attachments',
        'tests__questions__options',
        'tests__teacher'
    ).all()
    serializer_class = CourseSectionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_group', 'course']
    search_fields = ['title']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Check if filtering for template sections (subject_group__isnull)
        subject_group_isnull = self.request.query_params.get(
            'subject_group__isnull', '').lower()
        is_template_filter = subject_group_isnull == 'true'

        # IMPORTANT: Template sections have course set and subject_group = null
        # Regular sections have subject_group set and course = null
        # Always exclude one type unless explicitly requested

        # Students can only see course sections from their enrolled classrooms
        if user.role == UserRole.STUDENT:
            if is_template_filter:
                # Students shouldn't see template sections
                queryset = queryset.none()
            else:
                # Only show regular sections (subject_group set, course null)
                student_classrooms = user.classroom_users.values_list(
                    'classroom', flat=True)
                queryset = queryset.filter(
                    subject_group__classroom__in=student_classrooms,
                    subject_group__isnull=False,
                    course__isnull=True
                )
        # Teachers can see course sections from their subject groups
        elif user.role == UserRole.TEACHER:
            if is_template_filter:
                # Teachers can see template sections if they have access to the course
                teacher_courses = user.subject_groups.values_list(
                    'course', flat=True).distinct()
                queryset = queryset.filter(
                    course__in=teacher_courses,
                    subject_group__isnull=True,
                    course__isnull=False
                )
            else:
                # Only show regular sections (subject_group set, course null)
                queryset = queryset.filter(
                    subject_group__teacher=user,
                    subject_group__isnull=False,
                    course__isnull=True
                )
        # School admins can see course sections from their school
        elif user.role == UserRole.SCHOOLADMIN:
            if is_template_filter:
                # School admins can see template sections of courses used in their school
                school_courses = SubjectGroup.objects.filter(
                    classroom__school=user.school
                ).values_list('course', flat=True).distinct()
                queryset = queryset.filter(
                    course__in=school_courses,
                    subject_group__isnull=True,
                    course__isnull=False
                )
            else:
                # Only show regular sections (subject_group set, course null)
                queryset = queryset.filter(
                    subject_group__classroom__school=user.school,
                    subject_group__isnull=False,
                    course__isnull=True
                )
        # Superadmins can see all course sections
        elif user.role == UserRole.SUPERADMIN:
            if is_template_filter:
                # Show only template sections
                queryset = queryset.filter(
                    subject_group__isnull=True, course__isnull=False)
            else:
                # Show only regular sections (exclude template sections)
                queryset = queryset.filter(
                    subject_group__isnull=False, course__isnull=True)

        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        """Bulk update course section positions.
        Body: [{"id": <id>, "position": <pos>}, ...]
        """
        items = request.data if isinstance(
            request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position')
                     for item in items if 'id' in item and 'position' in item}
        objs = CourseSection.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        CourseSection.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})

    @action(detail=False, methods=['post'], url_path='auto-create-weeks')
    def auto_create_weeks(self, request):
        """Auto-create weekly sections for a subject group"""
        serializer = AutoCreateWeekSectionsSerializer(data=request.data)
        if serializer.is_valid():
            sections = serializer.save()
            response_serializer = CourseSectionSerializer(sections, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
