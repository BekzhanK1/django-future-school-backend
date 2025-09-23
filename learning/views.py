from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from .models import Resource, Assignment, AssignmentAttachment, Submission, SubmissionAttachment, Grade, Attendance, AttendanceRecord, AttendanceStatus
from .serializers import (
    ResourceSerializer, ResourceTreeSerializer, AssignmentSerializer, AssignmentAttachmentSerializer,
    SubmissionSerializer, SubmissionAttachmentSerializer, GradeSerializer, BulkGradeSerializer,
    AttendanceSerializer, AttendanceCreateSerializer, AttendanceUpdateSerializer, 
    StudentAttendanceHistorySerializer, AttendanceMetricsSerializer
)
from .role_permissions import RoleBasedPermission
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from users.models import UserRole


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.select_related('course_section', 'parent_resource').all()
    serializer_class = ResourceSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course_section', 'type', 'parent_resource']
    search_fields = ['title', 'description']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see resources for their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(course_section__subject_group__course__in=student_courses)
        # Teachers can see resources for their subject groups
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(course_section__subject_group__teacher=user)
        # School admins can see resources from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all resources (default queryset)
        
        # By default, only show root resources (no parent)
        if self.action == 'list' and 'show_all' not in self.request.query_params:
            queryset = queryset.filter(parent_resource__isnull=True)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        """Bulk update resource positions.
        Body: [{"id": <id>, "position": <pos>}, ...]
        """
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = Resource.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        Resource.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['get'], url_path='all')
    def all_resources(self, request):
        """Get all resources for a course section (including children)"""
        course_section_id = request.query_params.get('course_section_id')
        if not course_section_id:
            return Response({'error': 'course_section_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        resources = Resource.objects.filter(
            course_section_id=course_section_id
        ).order_by('position', 'id')
        
        serializer = ResourceSerializer(resources, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        """Get resource tree for a course section (root resources with nested children)"""
        course_section_id = request.query_params.get('course_section_id')
        if not course_section_id:
            return Response({'error': 'course_section_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get root resources (no parent)
        root_resources = Resource.objects.filter(
            course_section_id=course_section_id,
            parent_resource__isnull=True
        ).order_by('position', 'id')
        
        serializer = ResourceTreeSerializer(root_resources, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """Move resource to different position or parent"""
        resource = self.get_object()
        new_position = request.data.get('position', resource.position)
        new_parent_id = request.data.get('parent_id')
        
        if new_parent_id is not None:
            try:
                new_parent = Resource.objects.get(id=new_parent_id)
                if new_parent.course_section != resource.course_section:
                    return Response({'error': 'Parent must be in same course section'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                resource.parent_resource = new_parent
            except Resource.DoesNotExist:
                return Response({'error': 'Parent resource not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            resource.parent_resource = None
        
        resource.position = new_position
        resource.save()
        
        serializer = ResourceSerializer(resource, context={'request': request})
        return Response(serializer.data)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('course_section', 'teacher').prefetch_related('attachments').all()
    serializer_class = AssignmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course_section', 'teacher']
    search_fields = ['title', 'description']
    ordering_fields = ['due_at', 'title']
    ordering = ['due_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see assignments for their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(course_section__subject_group__course__in=student_courses)
        # Teachers can see assignments they created
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        # School admins can see assignments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all assignments (default queryset)
        
        return queryset


class AssignmentAttachmentViewSet(viewsets.ModelViewSet):
    queryset = AssignmentAttachment.objects.select_related('assignment').all()
    serializer_class = AssignmentAttachmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assignment', 'type']
    search_fields = ['title', 'content']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attachments for assignments in their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(assignment__course_section__subject_group__course__in=student_courses)
        # Teachers can see attachments for their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(assignment__teacher=user)
        # School admins can see attachments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(assignment__course_section__subject_group__classroom__school=user.school)
        # Superadmins can see all attachments (default queryset)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = AssignmentAttachment.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        AssignmentAttachment.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create attachments for an assignment"""
        assignment_id = request.data.get('assignment_id')
        attachments_data = request.data.get('attachments', [])
        
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_attachments = []
        for attachment_data in attachments_data:
            attachment_data['assignment'] = assignment_id
            serializer = AssignmentAttachmentSerializer(data=attachment_data)
            if serializer.is_valid():
                attachment = serializer.save()
                created_attachments.append(attachment)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        response_serializer = AssignmentAttachmentSerializer(created_attachments, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.select_related('assignment', 'student').prefetch_related('attachments').all()
    serializer_class = SubmissionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assignment', 'student']
    search_fields = ['student__username', 'student__email']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Teachers can see submissions for their assignments only
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(assignment__teacher=user)
        # School admins can see submissions from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(student__school=user.school)
        # Superadmins can see all submissions (default queryset)
        
        return queryset


class SubmissionAttachmentViewSet(viewsets.ModelViewSet):
    queryset = SubmissionAttachment.objects.select_related('submission').all()
    serializer_class = SubmissionAttachmentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['submission', 'type']
    search_fields = ['title', 'content']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attachments for their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(submission__student=user)
        # Teachers can see attachments for submissions to their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(submission__assignment__teacher=user)
        # School admins can see attachments from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(submission__student__school=user.school)
        # Superadmins can see all attachments (default queryset)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
        objs = SubmissionAttachment.objects.filter(id__in=id_to_pos.keys())
        for obj in objs:
            obj.position = id_to_pos.get(obj.id, obj.position)
        SubmissionAttachment.objects.bulk_update(objs, ['position'])
        return Response({'updated': len(objs)})
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create attachments for a submission"""
        submission_id = request.data.get('submission_id')
        attachments_data = request.data.get('attachments', [])
        
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_attachments = []
        for attachment_data in attachments_data:
            attachment_data['submission'] = submission_id
            serializer = SubmissionAttachmentSerializer(data=attachment_data)
            if serializer.is_valid():
                attachment = serializer.save()
                created_attachments.append(attachment)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        response_serializer = SubmissionAttachmentSerializer(created_attachments, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related('submission', 'graded_by').all()
    serializer_class = GradeSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['submission', 'graded_by']
    search_fields = ['submission__student__username', 'feedback']
    ordering_fields = ['graded_at', 'grade_value']
    ordering = ['-graded_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see grades for their own submissions
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(submission__student=user)
        # Teachers can see grades for submissions to their assignments
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(submission__assignment__teacher=user)
        # School admins can see grades from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(submission__student__school=user.school)
        # Superadmins can see all grades (default queryset)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-grade')
    def bulk_grade(self, request):
        """Bulk grade multiple submissions"""
        serializer = BulkGradeSerializer(data=request.data, many=True)
        if serializer.is_valid():
            grades = []
            for item in serializer.validated_data:
                submission = Submission.objects.get(id=item['submission_id'])
                grade, created = Grade.objects.get_or_create(
                    submission=submission,
                    defaults={
                        'graded_by': request.user,
                        'grade_value': item['grade_value'],
                        'feedback': item.get('feedback', ''),
                    }
                )
                if not created:
                    grade.grade_value = item['grade_value']
                    grade.feedback = item.get('feedback', '')
                    grade.graded_by = request.user
                    grade.save()
                grades.append(grade)
            
            response_serializer = GradeSerializer(grades, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('subject_group', 'taken_by').prefetch_related('records__student').all()
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_group', 'taken_by', 'taken_at']
    search_fields = ['subject_group__course__name', 'notes']
    ordering_fields = ['taken_at']
    ordering = ['-taken_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttendanceUpdateSerializer
        return AttendanceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see attendance for their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(subject_group__course__in=student_courses)
        # Teachers can see attendance for their subject groups
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(subject_group__teacher=user)
        # School admins can see attendance from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(subject_group__classroom__school=user.school)
        # Superadmins can see all attendance (default queryset)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(taken_by=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='student-history')
    def student_history(self, request):
        """Get attendance history for a specific student"""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Check permissions
        if user.role == UserRole.STUDENT and str(user.id) != str(student_id):
            return Response({'error': 'You can only view your own attendance history'}, 
                          status=status.HTTP_403_FORBIDDEN)
        elif user.role == UserRole.TEACHER:
            # Teachers can only see students from their subject groups
            teacher_subject_groups = user.subject_groups.values_list('id', flat=True)
            records = AttendanceRecord.objects.filter(
                student_id=student_id,
                attendance__subject_group__in=teacher_subject_groups
            ).select_related('attendance__subject_group__course', 'attendance__subject_group__classroom', 'attendance__taken_by')
        elif user.role == UserRole.SCHOOLADMIN:
            # School admins can see students from their school
            records = AttendanceRecord.objects.filter(
                student_id=student_id,
                attendance__subject_group__classroom__school=user.school
            ).select_related('attendance__subject_group__course', 'attendance__subject_group__classroom', 'attendance__taken_by')
        else:
            # Superadmin can see all
            records = AttendanceRecord.objects.filter(
                student_id=student_id
            ).select_related('attendance__subject_group__course', 'attendance__subject_group__classroom', 'attendance__taken_by')
        
        serializer = StudentAttendanceHistorySerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        """Get attendance metrics for different user roles"""
        user = request.user
        subject_group_id = request.query_params.get('subject_group_id')
        
        if user.role == UserRole.STUDENT:
            return Response({'error': 'Students cannot access metrics'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Build base queryset based on user role
        if user.role == UserRole.TEACHER:
            queryset = Attendance.objects.filter(subject_group__teacher=user)
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = Attendance.objects.filter(subject_group__classroom__school=user.school)
        else:  # Superadmin
            queryset = Attendance.objects.all()
        
        # Filter by subject group if specified
        if subject_group_id:
            queryset = queryset.filter(subject_group_id=subject_group_id)
        
        # Calculate metrics
        metrics_data = []
        
        if subject_group_id:
            # Single subject group metrics
            attendance = queryset.first()
            if attendance:
                metrics_data.append({
                    'subject_group_name': str(attendance.subject_group),
                    'classroom_name': str(attendance.subject_group.classroom),
                    'course_name': attendance.subject_group.course.name,
                    'total_sessions': queryset.count(),
                    'present_count': sum(a.present_count for a in queryset),
                    'excused_count': sum(a.excused_count for a in queryset),
                    'not_present_count': sum(a.not_present_count for a in queryset),
                    'attendance_percentage': round(
                        sum(a.attendance_percentage for a in queryset) / queryset.count() if queryset.count() > 0 else 0, 2
                    )
                })
        else:
            # Multiple subject groups metrics
            subject_groups = queryset.values('subject_group').distinct()
            
            for sg_data in subject_groups:
                sg_id = sg_data['subject_group']
                sg_attendances = queryset.filter(subject_group_id=sg_id)
                
                if sg_attendances.exists():
                    first_attendance = sg_attendances.first()
                    metrics_data.append({
                        'subject_group_name': str(first_attendance.subject_group),
                        'classroom_name': str(first_attendance.subject_group.classroom),
                        'course_name': first_attendance.subject_group.course.name,
                        'total_sessions': sg_attendances.count(),
                        'present_count': sum(a.present_count for a in sg_attendances),
                        'excused_count': sum(a.excused_count for a in sg_attendances),
                        'not_present_count': sum(a.not_present_count for a in sg_attendances),
                        'attendance_percentage': round(
                            sum(a.attendance_percentage for a in sg_attendances) / sg_attendances.count() if sg_attendances.count() > 0 else 0, 2
                        )
                    })
        
        serializer = AttendanceMetricsSerializer(metrics_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='mark-attendance')
    def mark_attendance(self, request, pk=None):
        """Mark attendance for all students in a subject group"""
        attendance = self.get_object()
        records_data = request.data.get('records', [])
        
        # Clear existing records
        attendance.records.all().delete()
        
        # Create new records
        for record_data in records_data:
            AttendanceRecord.objects.create(
                attendance=attendance,
                student_id=record_data['student_id'],
                status=record_data['status'],
                notes=record_data.get('notes', '')
            )
        
        serializer = AttendanceSerializer(attendance, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='subject-group-students')
    def subject_group_students(self, request):
        """Get students for a subject group to mark attendance"""
        subject_group_id = request.query_params.get('subject_group_id')
        if not subject_group_id:
            return Response({'error': 'subject_group_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from courses.models import SubjectGroup
            subject_group = SubjectGroup.objects.get(id=subject_group_id)
        except SubjectGroup.DoesNotExist:
            return Response({'error': 'Subject group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        user = request.user
        if user.role == UserRole.TEACHER and subject_group.teacher != user:
            return Response({'error': 'You can only view students for your own subject groups'}, 
                          status=status.HTTP_403_FORBIDDEN)
        elif user.role == UserRole.SCHOOLADMIN and subject_group.classroom.school != user.school:
            return Response({'error': 'You can only view students from your school'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get students in the classroom
        students = subject_group.classroom.classroom_users.filter(
            user__role=UserRole.STUDENT
        ).select_related('user').values(
            'user__id', 'user__username', 'user__first_name', 'user__last_name', 'user__email'
        )
        
        return Response(list(students))