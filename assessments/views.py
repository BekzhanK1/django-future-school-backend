from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction

from .models import Test, Question, Option, Attempt, Answer, QuestionType
from .serializers import (
    TestSerializer, QuestionSerializer, OptionSerializer, AttemptSerializer, AnswerSerializer,
    CreateAttemptSerializer, SubmitAnswerSerializer, BulkGradeAnswersSerializer,
    ViewResultsSerializer, CreateQuestionSerializer, CreateTestSerializer
)
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove
from learning.role_permissions import RoleBasedPermission
from users.models import UserRole


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.select_related(
        'course_section__subject_group__course',
        'course_section__subject_group__classroom__school',
        'teacher'
    ).prefetch_related('questions__options').all()
    serializer_class = TestSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course_section', 'teacher', 'is_published', 'allow_multiple_attempts']
    search_fields = ['title', 'description']
    ordering_fields = ['scheduled_at', 'title', 'created_at', 'total_points']
    ordering = ['-scheduled_at', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateTestSerializer
        return TestSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see tests for their courses
        if user.role == UserRole.STUDENT:
            student_course_sections = user.classroom_users.values_list(
                'classroom__subject_groups__sections', flat=True
            )
            queryset = queryset.filter(course_section__in=student_course_sections)
        # Teachers can see tests they created
        elif user.role == UserRole.TEACHER:
            queryset = queryset.filter(teacher=user)
        # School admins can see tests from their school
        elif user.role == UserRole.SCHOOLADMIN:
            queryset = queryset.filter(
                course_section__subject_group__classroom__school=user.school
            )
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

    @action(detail=False, methods=['post'], url_path='create-full')
    def create_full(self, request):
        """Create a test and its questions in a single request.
        Payload matches CreateTestSerializer, with `questions` as a list
        where each question omits the `test` field.
        """
        serializer = CreateTestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            test = serializer.save()
            response = TestSerializer(test, context={'request': request})
            return Response(response.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.select_related('question__test').all()
    serializer_class = OptionSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['question', 'is_correct']
    search_fields = ['text']
    ordering_fields = ['position']
    ordering = ['position', 'id']


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related('test').prefetch_related('options').all()
    serializer_class = QuestionSerializer
    permission_classes = [IsTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['test', 'type']
    search_fields = ['text']
    ordering_fields = ['position', 'points']
    ordering = ['position', 'id']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateQuestionSerializer
        return QuestionSerializer


class AttemptViewSet(viewsets.ModelViewSet):
    queryset = Attempt.objects.select_related(
        'test__course_section__subject_group__course',
        'student'
    ).prefetch_related('answers__question', 'answers__selected_options').all()
    serializer_class = AttemptSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['test', 'student', 'is_completed', 'is_graded']
    search_fields = ['student__username', 'student__email', 'test__title']
    ordering_fields = ['started_at', 'submitted_at', 'score', 'attempt_number']
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
            queryset = queryset.filter(
                test__course_section__subject_group__classroom__school=user.school
            )
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
        
        with transaction.atomic():
            # Auto-grade questions that can be auto-graded
            total_score = 0
            max_score = 0
            
            for answer in attempt.answers.all():
                question = answer.question
                max_score += question.points
                
                # Calculate score based on question type
                calculated_score = answer.calculate_score()
                if calculated_score is not None:
                    answer.score = calculated_score
                    answer.max_score = question.points
                    answer.is_correct = (calculated_score == question.points)
                    total_score += calculated_score
                else:
                    # Open questions need manual grading
                    answer.max_score = question.points
                    answer.is_correct = None
                
                answer.save()
            
            # Update attempt
            attempt.submitted_at = timezone.now()
            attempt.score = total_score
            attempt.max_score = max_score
            attempt.is_completed = True
            attempt.is_graded = all(
                answer.score is not None for answer in attempt.answers.all()
            )
            attempt.save()
            
            # Calculate percentage
            if max_score > 0:
                attempt.percentage = (total_score / max_score) * 100
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
                question=question
            )
            
            # Update answer fields
            for field, value in serializer.validated_data.items():
                if field != 'question_id':
                    setattr(answer, field, value)
            
            # Handle selected options for multiple choice questions
            if 'selected_option_ids' in serializer.validated_data:
                selected_option_ids = serializer.validated_data['selected_option_ids']
                if selected_option_ids:
                    selected_options = Option.objects.filter(
                        id__in=selected_option_ids,
                        question=question
                    )
                    answer.selected_options.set(selected_options)
                else:
                    answer.selected_options.clear()
            
            answer.save()
            
            response_serializer = AnswerSerializer(answer)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='view-results')
    def view_results(self, request, pk=None):
        """Mark results as viewed by student"""
        attempt = self.get_object()
        
        if attempt.student != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        if not attempt.can_view_results:
            return Response({'error': 'Results not yet available'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not attempt.results_viewed_at:
            attempt.results_viewed_at = timezone.now()
            attempt.save()
        
        serializer = self.get_serializer(attempt)
        return Response(serializer.data)


class AnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.select_related(
        'attempt__test__course_section__subject_group__course',
        'attempt__student',
        'question'
    ).prefetch_related('selected_options').all()
    serializer_class = AnswerSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['attempt', 'question', 'is_correct']
    search_fields = ['text_answer', 'teacher_feedback']
    ordering_fields = ['question__position', 'score']
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
            queryset = queryset.filter(
                attempt__test__course_section__subject_group__classroom__school=user.school
            )
        # Superadmins can see all answers (default queryset)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-grade')
    def bulk_grade(self, request):
        """Bulk grade answers (for open questions)"""
        serializer = BulkGradeAnswersSerializer(data=request.data, many=True)
        if serializer.is_valid():
            answers = []
            with transaction.atomic():
                for item in serializer.validated_data:
                    answer = Answer.objects.get(id=item['answer_id'])
                    answer.score = item.get('score')
                    answer.teacher_feedback = item.get('teacher_feedback', '')
                    answer.is_correct = (answer.score == answer.max_score) if answer.score is not None else None
                    answer.save()
                    answers.append(answer)
            
            response_serializer = AnswerSerializer(answers, many=True)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)