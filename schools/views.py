from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import School, Classroom, ClassroomUser
from .serializers import (
    SchoolSerializer, 
    ClassroomSerializer, 
    ClassroomDetailSerializer,
    ClassroomUserSerializer, 
    BulkClassroomUserSerializer
)
from .permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from users.models import User


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'city', 'country']
    ordering_fields = ['name', 'city']
    ordering = ['name']


class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.select_related('school').prefetch_related('classroom_users__user').all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['school', 'grade', 'language']
    search_fields = ['letter', 'school__name']
    ordering_fields = ['grade', 'letter', 'school__name']
    ordering = ['school__name', 'grade', 'letter']
    
    def get_serializer_class(self):
        # Use detailed serializer for retrieve action (get single classroom)
        if self.action == 'retrieve':
            return ClassroomDetailSerializer
        return ClassroomSerializer
    
    @action(detail=True, methods=['post'], url_path='add-student')
    def add_student(self, request, pk=None):
        """Add a single student to a classroom"""
        classroom = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if student is already in a classroom
        existing_classroom = ClassroomUser.objects.filter(user=student).first()
        if existing_classroom:
            return Response(
                {'error': f'Student is already in classroom {existing_classroom.classroom}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add student to classroom
        classroom_user = ClassroomUser.objects.create(
            classroom=classroom,
            user=student
        )
        
        return Response(
            {
                'message': 'Student added successfully',
                'classroom_user_id': classroom_user.id
            }, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='remove-student')
    def remove_student(self, request, pk=None):
        """Remove a single student from a classroom"""
        classroom = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find the ClassroomUser entry
            classroom_user = ClassroomUser.objects.get(
                classroom=classroom,
                user_id=student_id
            )
            classroom_user.delete()
            
            return Response(
                {'message': 'Student removed successfully'}, 
                status=status.HTTP_200_OK
            )
        except ClassroomUser.DoesNotExist:
            return Response(
                {'error': 'Student is not in this classroom'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ClassroomUserViewSet(viewsets.ModelViewSet):
    queryset = ClassroomUser.objects.select_related('classroom', 'user').all()
    serializer_class = ClassroomUserSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['classroom', 'user']
    search_fields = ['user__username', 'user__email', 'classroom__letter']
    ordering_fields = ['user__username', 'classroom__grade', 'classroom__letter']
    ordering = ['classroom__school__name', 'classroom__grade', 'classroom__letter', 'user__username']
    
    @action(detail=False, methods=['post'], url_path='bulk-add')
    def bulk_add(self, request):
        """Bulk add users to a classroom"""
        serializer = BulkClassroomUserSerializer(data=request.data)
        if serializer.is_valid():
            classroom_users = serializer.save()
            response_serializer = ClassroomUserSerializer(classroom_users, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'], url_path='bulk-remove')
    def bulk_remove(self, request):
        """Bulk remove users from a classroom"""
        classroom_id = request.data.get('classroom_id')
        user_ids = request.data.get('user_ids', [])
        
        if not classroom_id:
            return Response({'error': 'classroom_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count, _ = ClassroomUser.objects.filter(
            classroom_id=classroom_id,
            user_id__in=user_ids
        ).delete()
        
        return Response({'deleted_count': deleted_count}, status=status.HTTP_200_OK)