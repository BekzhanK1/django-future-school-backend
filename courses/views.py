from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Course, SubjectGroup, CourseSection
from .serializers import (
    CourseSerializer, SubjectGroupSerializer, CourseSectionSerializer,
    AutoCreateWeekSectionsSerializer, CourseFullSerializer
)
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove


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
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'classroom', 'teacher']
    search_fields = ['course__name', 'course__course_code', 'classroom__letter', 'teacher__username']
    ordering_fields = ['course__name', 'classroom__grade', 'classroom__letter']
    ordering = ['course__name', 'classroom__grade', 'classroom__letter']


class CourseSectionViewSet(viewsets.ModelViewSet):
    queryset = CourseSection.objects.select_related('subject_group').prefetch_related(
        'resources__children__children__children',  # Support up to 3 levels deep
        'assignments__teacher',
        'assignments__attachments',
        'tests__questions__options',
        'tests__teacher'
    ).all()
    serializer_class = CourseSectionSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_group']
    search_fields = ['title']
    ordering_fields = ['position', 'title']
    ordering = ['position', 'id']
    
    @action(detail=False, methods=['post'], url_path='auto-create-weeks')
    def auto_create_weeks(self, request):
        """Auto-create weekly sections for a subject group"""
        serializer = AutoCreateWeekSectionsSerializer(data=request.data)
        if serializer.is_valid():
            sections = serializer.save()
            response_serializer = CourseSectionSerializer(sections, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)