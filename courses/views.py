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
        queryset = Course.objects.prefetch_related('subject_groups__classroom', 'subject_groups__teacher').all()
        serializer = CourseFullSerializer(queryset, many=True)
        return Response(serializer.data)


class SubjectGroupViewSet(viewsets.ModelViewSet):
    queryset = SubjectGroup.objects.select_related('course', 'classroom', 'teacher').all()
    serializer_class = SubjectGroupSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'classroom', 'teacher']
    search_fields = ['course__name', 'course__course_code', 'classroom__letter', 'teacher__username']
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
            subject_group = SubjectGroup.objects.select_related('course', 'classroom', 'teacher', 'classroom__school').get(id=pk)
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
            is_in_classroom = user.classroom_users.filter(classroom_id=subject_group.classroom_id).exists()
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
    queryset = CourseSection.objects.select_related('subject_group').prefetch_related(
        'resources__children__children__children',  # Support up to 3 levels deep
        'assignments__teacher',
        'assignments__attachments',
        'tests__questions__options',
        'tests__teacher'
    ).all()
    serializer_class = CourseSectionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_group']
    search_fields = ['title']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see course sections from their enrolled classrooms
        if user.role == UserRole.STUDENT:
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            queryset = queryset.filter(subject_group__classroom__in=student_classrooms)
        # Teachers can see course sections from their subject groups
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(subject_group__teacher=user)
        # School admins can see course sections from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(subject_group__classroom__school=user.school)
        # Superadmins can see all course sections (default queryset)
        
        return queryset

    @action(detail=False, methods=['patch'], url_path='change-items-order')
    def change_items_order(self, request):
        """Bulk update course section positions.
        Body: [{"id": <id>, "position": <pos>}, ...]
        """
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Expected a list payload'}, status=status.HTTP_400_BAD_REQUEST)
        id_to_pos = {item.get('id'): item.get('position') for item in items if 'id' in item and 'position' in item}
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