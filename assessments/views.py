from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Sum, Q

from .models import Test, Question, Attempt, Answer
from .serializers import (
    TestSerializer, QuestionSerializer, AttemptSerializer, AnswerSerializer,
    CreateAttemptSerializer, SubmitAnswerSerializer, BulkGradeAnswersSerializer
)
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from learning.role_permissions import RoleBasedPermission
from users.models import UserRole


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.select_related('course', 'teacher').prefetch_related('questions').all()
    serializer_class = TestSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'teacher', 'is_published']
    search_fields = ['title', 'description']
    ordering_fields = ['scheduled_at', 'title', 'created_at']
    ordering = ['-scheduled_at', '-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see tests for their courses
        if user.role == UserRole.STUDENT:
            student_courses = user.classroom_users.values_list('classroom__subject_groups__course', flat=True)
            queryset = queryset.filter(course__in=student_courses)
        # Teachers can see tests they created
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        # School admins can see tests from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(course__subject_groups__classroom__school=user.school)
        # Superadmins can see all tests (default queryset)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """Publish a test"""
        test = self.get_object()
        test.is_published = True
        test.save()
        serializer = self.get_serializer(test)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='unpublish')
    def unpublish(self, request, pk=None):
        """Unpublish a test"""
        test = self.get_object()
        test.is_published = False
        test.save()
        serializer = self.get_serializer(test)
        return Response(serializer.data)


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related('test').all()
    serializer_class = QuestionSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['test', 'type']
    search_fields = ['text']
    ordering_fields = ['position', 'points']
    ordering = ['position', 'id']


class AttemptViewSet(viewsets.ModelViewSet):
    queryset = Attempt.objects.select_related('test', 'student').prefetch_related('answers').all()
    serializer_class = AttemptSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['test', 'student']
    search_fields = ['student__username', 'student__email']
    ordering_fields = ['started_at', 'submitted_at', 'score']
    ordering = ['-submitted_at', '-started_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see their own attempts
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(student=user)
        # Teachers can see attempts for their tests
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(test__teacher=user)
        # School admins can see attempts from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(student__school=user.school)
        # Superadmins can see all attempts (default queryset)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='start')
    def start_attempt(self, request):
        """Start a new test attempt"""
        serializer = CreateAttemptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            attempt = serializer.save()
            response_serializer = AttemptSerializer(attempt, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='submit')
    def submit_attempt(self, request, pk=None):
        """Submit a test attempt"""
        attempt = self.get_object()
        
        if attempt.submitted_at:
            return Response({'error': 'Attempt already submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Auto-grade multiple choice questions
        total_score = 0
        max_score = 0
        
        for answer in attempt.answers.all():
            question = answer.question
            max_score += question.points
            
            if question.type in ['single_choice', 'multiple_choice']:
                # Auto-grade based on correct_json
                if answer.selected_json == question.correct_json:
                    answer.score = question.points
                    total_score += question.points
                else:
                    answer.score = 0
                answer.save()
        
        attempt.submitted_at = timezone.now()
        attempt.score = total_score
        attempt.max_score = max_score
        attempt.save()
        
        serializer = self.get_serializer(attempt)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='submit-answer')
    def submit_answer(self, request, pk=None):
        """Submit an answer for a question in an attempt"""
        attempt = self.get_object()
        
        if attempt.submitted_at:
            return Response({'error': 'Attempt already submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = SubmitAnswerSerializer(data=request.data)
        if serializer.is_valid():
            question_id = serializer.validated_data['question_id']
            
            try:
                question = Question.objects.get(id=question_id, test=attempt.test)
            except Question.DoesNotExist:
                return Response({'error': 'Question not found in this test'}, status=status.HTTP_400_BAD_REQUEST)
            
            answer, created = Answer.objects.get_or_create(
                attempt=attempt,
                question=question,
                defaults=serializer.validated_data
            )
            
            if not created:
                for field, value in serializer.validated_data.items():
                    setattr(answer, field, value)
                answer.save()
            
            response_serializer = AnswerSerializer(answer)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.select_related('attempt', 'question').all()
    serializer_class = AnswerSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['attempt', 'question']
    search_fields = ['text_answer']
    ordering_fields = ['question__position']
    ordering = ['question__position']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see answers for their own attempts
        if user.role == UserRole.STUDENT:
            queryset = queryset.filter(attempt__student=user)
        # Teachers can see answers for their tests
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(attempt__test__teacher=user)
        # School admins can see answers from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(attempt__student__school=user.school)
        # Superadmins can see all answers (default queryset)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-grade')
    def bulk_grade(self, request):
        """Bulk grade answers (for open questions)"""
        serializer = BulkGradeAnswersSerializer(data=request.data, many=True)
        if serializer.is_valid():
            answers = []
            for item in serializer.validated_data:
                answer = Answer.objects.get(id=item['answer_id'])
                answer.score = item.get('score')
                answer.save()
                answers.append(answer)
            
            response_serializer = AnswerSerializer(answers, many=True)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)