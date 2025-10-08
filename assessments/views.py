"""
Assessment views for managing tests, questions, options, attempts, and answers.

This module provides comprehensive API endpoints for:
- Test creation, management, and teacher results viewing
- Question and option management
- Student test attempts and answer submission
- Bulk grading and score updates
"""

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin, IsTeacherOrAbove, IsStudentOrTeacherOrAbove
from learning.role_permissions import RoleBasedPermission
from users.models import UserRole

from .models import Test, Question, Option, Attempt, Answer, QuestionType
from .serializers import (
    TestSerializer, QuestionSerializer, OptionSerializer, AttemptSerializer, AnswerSerializer,
    CreateAttemptSerializer, SubmitAnswerSerializer, BulkGradeAnswersSerializer,
    ViewResultsSerializer, CreateQuestionSerializer, CreateTestSerializer
)


class TestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tests.
    
    Provides endpoints for:
    - CRUD operations on tests
    - Publishing/unpublishing tests
    - Creating tests with questions in a single request
    - Viewing comprehensive teacher results
    - Updating individual answer scores
    """
    
    queryset = Test.objects.select_related(
        'course_section__subject_group__course',
        'course_section__subject_group__classroom__school',
        'teacher'
    ).prefetch_related('questions__options').all()
    
    serializer_class = TestSerializer
    permission_classes = [IsStudentOrTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    filterset_fields = [
        'course_section', 
        'teacher', 
        'is_published', 
        'allow_multiple_attempts'
    ]
    search_fields = ['title', 'description']
    ordering_fields = [
        'scheduled_at', 
        'title', 
        'created_at', 
        'total_points'
    ]
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

    @action(detail=True, methods=['get'], url_path='teacher-results')
    def teacher_results(self, request, pk=None):
        """
        Get comprehensive test results for teachers.
        
        Returns detailed results in two formats:
        1. Per-student view: Each student's complete test performance
        2. Per-question view: How all students performed on each question
        
        Args:
            request: HTTP request object
            pk: Test primary key
            
        Returns:
            Response containing test metadata and results in both views
            
        Raises:
            403 Forbidden: If user is not the teacher of this test
        """
        test = self.get_object()
        
        # Validate teacher access
        if request.user != test.teacher:
            return Response(
                {'error': 'You can only view results for your own tests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Fetch completed attempts with optimized queries
        attempts = test.attempts.filter(is_completed=True).select_related(
            'student'
        ).prefetch_related(
            'answers__question__options'
        ).order_by('student__first_name', 'student__last_name')
        
        # Fetch questions ordered by position
        questions = test.questions.all().order_by('position')
        
        # Build comprehensive results data
        results_data = self._build_results_data(test, attempts, questions)
        
        return Response(results_data)

    def _build_results_data(self, test, attempts, questions):
        """
        Build comprehensive results data for both per-student and per-question views.
        
        Args:
            test: Test instance
            attempts: QuerySet of completed attempts
            questions: QuerySet of test questions
            
        Returns:
            dict: Formatted results data with test metadata and both views
        """
        # Build per-student view
        students_data = self._build_per_student_view(attempts, questions, test)
        
        # Build per-question view  
        questions_data = self._build_per_question_view(attempts, questions)
        
        return {
            'test': {
                'id': test.id,
                'title': test.title,
                'total_points': test.total_points,
                'total_questions': questions.count(),
                'total_students': attempts.count()
            },
            'per_student_view': students_data,
            'per_question_view': questions_data
        }

    def _build_per_student_view(self, attempts, questions, test):
        """Build per-student results view."""
        students_data = []
        
        for attempt in attempts:
            student_data = {
                'student_id': attempt.student.id,
                'student_name': self._get_student_display_name(attempt.student),
                'student_username': attempt.student.username,
                'attempt_id': attempt.id,
                'attempt_number': attempt.attempt_number,
                'total_score': attempt.score or 0,
                'max_score': attempt.max_score or test.total_points,
                'percentage': attempt.percentage or 0,
                'submitted_at': attempt.submitted_at,
                'time_spent_minutes': attempt.time_spent_minutes,
                'answers': []
            }
            
            # Build answers for this student
            for question in questions:
                answer_data = self._build_answer_data(attempt, question)
                student_data['answers'].append(answer_data)
            
            students_data.append(student_data)
        
        return students_data

    def _build_per_question_view(self, attempts, questions):
        """Build per-question results view."""
        questions_data = []
        
        for question in questions:
            question_data = {
                'question_id': question.id,
                'question_text': question.text,
                'question_type': question.type,
                'question_points': question.points,
                'correct_answer': self._get_correct_answer(question),
                'student_answers': []
            }
            
            # Build student answers for this question
            for attempt in attempts:
                answer = attempt.answers.filter(question=question).first()
                student_answer_data = {
                    'student_id': attempt.student.id,
                    'student_name': self._get_student_display_name(attempt.student),
                    'student_username': attempt.student.username,
                    'attempt_id': attempt.id,
                    'answer_id': answer.id if answer else None,
                    'student_answer': self._format_student_answer(answer, question),
                    'score': answer.score if answer else 0,
                    'max_score': answer.max_score or question.points if answer else question.points,
                    'teacher_feedback': answer.teacher_feedback if answer else '',
                    'is_correct': answer.is_correct if answer else False
                }
                question_data['student_answers'].append(student_answer_data)
            
            questions_data.append(question_data)
        
        return questions_data

    def _build_answer_data(self, attempt, question):
        """Build answer data for a specific student attempt and question."""
        answer = attempt.answers.filter(question=question).first()
        
        if answer:
            return {
                'answer_id': answer.id,
                'question_id': question.id,
                'question_text': question.text,
                'question_type': question.type,
                'question_points': question.points,
                'student_answer': self._format_student_answer(answer, question),
                'correct_answer': self._get_correct_answer(question),
                'score': answer.score,
                'max_score': answer.max_score or question.points,
                'teacher_feedback': answer.teacher_feedback,
                'is_correct': answer.is_correct
            }
        else:
            return {
                'answer_id': None,
                'question_id': question.id,
                'question_text': question.text,
                'question_type': question.type,
                'question_points': question.points,
                'student_answer': 'No answer provided',
                'correct_answer': self._get_correct_answer(question),
                'score': 0,
                'max_score': question.points,
                'teacher_feedback': '',
                'is_correct': False
            }

    def _get_student_display_name(self, student):
        """Get formatted student display name."""
        full_name = f"{student.first_name} {student.last_name}".strip()
        return full_name or student.username

    def _format_student_answer(self, answer, question):
        """
        Format student answer based on question type.
        
        Args:
            answer: Answer instance (can be None)
            question: Question instance
            
        Returns:
            str: Formatted answer text
        """
        if not answer:
            return 'No answer provided'
        
        if question.type == QuestionType.MULTIPLE_CHOICE:
            return self._format_multiple_choice_answer(answer)
        
        elif question.type == QuestionType.CHOOSE_ALL:
            return self._format_choose_all_answer(answer)
        
        elif question.type == QuestionType.OPEN_QUESTION:
            return answer.text_answer or 'No text answer'
        
        elif question.type == QuestionType.MATCHING:
            return str(answer.matching_answers_json) if answer.matching_answers_json else 'No matching answers'
        
        return 'Unknown answer type'

    def _format_multiple_choice_answer(self, answer):
        """Format multiple choice answer."""
        selected_options = answer.selected_options.all()
        if selected_options:
            option = selected_options.first()
            return option.text or f"Image: {option.image_url}" or 'No content'
        return 'No option selected'

    def _format_choose_all_answer(self, answer):
        """Format choose all that apply answer."""
        selected_options = answer.selected_options.all()
        if selected_options:
            formatted_options = [
                opt.text or f"Image: {opt.image_url}" or 'No content' 
                for opt in selected_options
            ]
            return ', '.join(formatted_options)
        return 'No options selected'
    
    def _get_correct_answer(self, question):
        """
        Get the correct answer for a question based on its type.
        
        Args:
            question: Question instance
            
        Returns:
            str: Formatted correct answer
        """
        if question.type == QuestionType.MULTIPLE_CHOICE:
            return self._get_multiple_choice_correct_answer(question)
        
        elif question.type == QuestionType.CHOOSE_ALL:
            return self._get_choose_all_correct_answer(question)
        
        elif question.type == QuestionType.OPEN_QUESTION:
            return question.correct_answer_text or question.sample_answer or 'No sample answer'
        
        elif question.type == QuestionType.MATCHING:
            return str(question.matching_pairs_json) if question.matching_pairs_json else 'No matching pairs'
        
        return 'Unknown question type'

    def _get_multiple_choice_correct_answer(self, question):
        """Get correct answer for multiple choice question."""
        correct_option = question.options.filter(is_correct=True).first()
        if correct_option:
            return correct_option.text or f"Image: {correct_option.image_url}" or 'No content'
        return 'No correct option'

    def _get_choose_all_correct_answer(self, question):
        """Get correct answers for choose all that apply question."""
        correct_options = question.options.filter(is_correct=True)
        if correct_options:
            formatted_options = [
                opt.text or f"Image: {opt.image_url}" or 'No content' 
                for opt in correct_options
            ]
            return ', '.join(formatted_options)
        return 'No correct options'

    @action(detail=True, methods=['patch'], url_path='update-answer-score')
    def update_answer_score(self, request, pk=None):
        """
        Update the score for a specific answer.
        
        This endpoint allows teachers to manually grade or adjust scores for
        individual student answers, with automatic recalculation of attempt totals.
        
        Args:
            request: HTTP request object containing answer_id, score, and teacher_feedback
            pk: Test primary key
            
        Returns:
            Response containing updated answer data and recalculated attempt totals
            
        Raises:
            403 Forbidden: If user is not the teacher of this test
            400 Bad Request: If required fields are missing or invalid
            404 Not Found: If answer doesn't exist
            500 Internal Server Error: If update fails
        """
        test = self.get_object()
        
        # Validate teacher access
        if request.user != test.teacher:
            return Response(
                {'error': 'You can only update scores for your own tests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Extract and validate request data
        answer_id = request.data.get('answer_id')
        new_score = request.data.get('score')
        teacher_feedback = request.data.get('teacher_feedback', '')
        
        if not answer_id or new_score is None:
            return Response(
                {'error': 'answer_id and score are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Fetch and validate answer
            answer = Answer.objects.select_related('attempt__test').get(id=answer_id)
            
            if answer.attempt.test != test:
                return Response(
                    {'error': 'Answer does not belong to this test'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update answer with transaction for data consistency
            with transaction.atomic():
                self._update_answer_score(answer, new_score, teacher_feedback)
                self._recalculate_attempt_score(answer.attempt, test)
            
            return Response(self._build_score_update_response(answer))
            
        except Answer.DoesNotExist:
            return Response(
                {'error': 'Answer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error updating score: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _update_answer_score(self, answer, new_score, teacher_feedback):
        """Update answer score and feedback."""
        answer.score = new_score
        answer.teacher_feedback = teacher_feedback
        answer.is_correct = (new_score == answer.max_score) if new_score is not None else None
        answer.save()

    def _recalculate_attempt_score(self, attempt, test):
        """Recalculate attempt total score and percentage."""
        total_score = attempt.answers.aggregate(Sum('score'))['score__sum'] or 0
        attempt.score = total_score
        attempt.percentage = (total_score / test.total_points * 100) if test.total_points > 0 else 0
        attempt.is_graded = True
        attempt.graded_at = timezone.now()
        attempt.save()

    def _build_score_update_response(self, answer):
        """Build response data for score update."""
        attempt = answer.attempt
        return {
            'answer_id': answer.id,
            'new_score': answer.score,
            'max_score': answer.max_score,
            'teacher_feedback': answer.teacher_feedback,
            'is_correct': answer.is_correct,
            'attempt_total_score': attempt.score,
            'attempt_percentage': attempt.percentage
        }


class OptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing question options.
    
    Provides CRUD operations for test question options including
    multiple choice and choose-all-that-apply questions.
    """
    
    queryset = Option.objects.select_related('question__test').all()
    serializer_class = OptionSerializer
    permission_classes = [IsStudentOrTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['question', 'is_correct']
    search_fields = ['text']
    ordering_fields = ['position']
    ordering = ['position', 'id']


class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing test questions.
    
    Provides CRUD operations for test questions including all question types:
    multiple choice, choose all that apply, open questions, and matching.
    """
    
    queryset = Question.objects.select_related('test').prefetch_related('options').all()
    serializer_class = QuestionSerializer
    permission_classes = [IsStudentOrTeacherOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    filterset_fields = ['test', 'type']
    search_fields = ['text']
    ordering_fields = ['position', 'points']
    ordering = ['position', 'id']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CreateQuestionSerializer
        return QuestionSerializer


class AttemptViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing test attempts.
    
    Provides endpoints for:
    - Viewing test attempts and results
    - Starting new attempts
    - Submitting completed attempts
    - Submitting individual answers
    - Viewing results (for students)
    """
    
    queryset = Attempt.objects.select_related(
        'test__course_section__subject_group__course',
        'student'
    ).prefetch_related('answers__question', 'answers__selected_options').all()
    
    serializer_class = AttemptSerializer
    permission_classes = [IsStudentOrTeacherOrAbove]
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
    
    @extend_schema(
        operation_id='attempts_create',
        summary='Create or resume an attempt',
        request=CreateAttemptSerializer,
        responses={201: AttemptSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
    def create(self, request, *args, **kwargs):
        """Create (or resume) an attempt using the authenticated user.
        Mirrors the logic of the start_attempt action but on POST /attempts/.
        """
        serializer = CreateAttemptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            attempt = serializer.save()
            response_serializer = AttemptSerializer(attempt, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='attempts_start',
        summary='Start or resume an attempt',
        request=CreateAttemptSerializer,
        responses={201: AttemptSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
    @action(detail=False, methods=['post'], url_path='start')
    def start_attempt(self, request):
        """Start a new test attempt"""
        serializer = CreateAttemptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            attempt = serializer.save()
            response_serializer = AttemptSerializer(attempt, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        operation_id='attempts_submit',
        summary='Submit attempt for grading',
        request=None,
        responses={200: AttemptSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
    @action(detail=True, methods=['post'], url_path='submit')
    def submit_attempt(self, request, pk=None):
        """Submit a test attempt"""
        attempt = self.get_object()
        
        if attempt.submitted_at:
            return Response({'error': 'Attempt already submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create zero-score answers for unanswered questions
            answered_question_ids = set(
                attempt.answers.values_list('question_id', flat=True)
            )
            all_questions = attempt.test.questions.all()
            for question in all_questions:
                if question.id not in answered_question_ids:
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        score=0,
                        max_score=question.points,
                        is_correct=False,
                    )

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
            
            # Calculate percentage based on all questions (including previously unanswered)
            if max_score > 0:
                attempt.percentage = (total_score / max_score) * 100
                attempt.save()
        
        serializer = self.get_serializer(attempt)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='attempts_submit_answer',
        summary='Submit or update an answer',
        request=SubmitAnswerSerializer,
        responses={201: AnswerSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
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
    
    @extend_schema(
        operation_id='attempts_view_results',
        summary='Mark results as viewed',
        request=None,
        responses={200: AttemptSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
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
    """
    ViewSet for managing student answers.
    
    Provides endpoints for:
    - Viewing student answers to test questions
    - Bulk grading of answers (especially for open questions)
    - Answer filtering and search functionality
    """
    
    queryset = Answer.objects.select_related(
        'attempt__test__course_section__subject_group__course',
        'attempt__student',
        'question'
    ).prefetch_related('selected_options').all()
    
    serializer_class = AnswerSerializer
    permission_classes = [IsStudentOrTeacherOrAbove]
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
        """
        Bulk grade multiple answers in a single request.
        
        This endpoint is particularly useful for grading open-ended questions
        where teachers need to manually score and provide feedback.
        
        Args:
            request: HTTP request containing list of answer grading data
            
        Returns:
            Response containing updated answer data or validation errors
            
        Raises:
            400 Bad Request: If validation fails
        """
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

