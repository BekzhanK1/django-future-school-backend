from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import School, Classroom, ClassroomUser
from .serializers import SchoolSerializer, ClassroomSerializer, ClassroomUserSerializer, BulkClassroomUserSerializer
from .permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'city', 'country']
    ordering_fields = ['name', 'city']
    ordering = ['name']


class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.select_related('school').all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['school', 'grade', 'language']
    search_fields = ['letter', 'school__name']
    ordering_fields = ['grade', 'letter', 'school__name']
    ordering = ['school__name', 'grade', 'letter']


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