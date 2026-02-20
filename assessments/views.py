"""
Assessment views for managing tests, questions, options, attempts, and answers.

This module provides comprehensive API endpoints for:
- Test creation, management, and teacher results viewing
- Question and option management
- Student test attempts and answer submission
- Bulk grading and score updates
"""

from django.db import transaction
from django.db.models import Q, Sum
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
from users.models import UserRole, User

from .models import Test, Question, Option, Attempt, Answer, QuestionType
from .serializers import (
    TestSerializer, QuestionSerializer, OptionSerializer, AttemptSerializer, AnswerSerializer,
    CreateAttemptSerializer, SubmitAnswerSerializer, BulkGradeAnswersSerializer,
    ViewResultsSerializer, CreateQuestionSerializer, CreateTestSerializer
)
from courses.models import Course, CourseSection


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
        'course_section__course',  # For template sections
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
        'start_date',
        'title',
        'created_at',
        'total_points'
    ]
    ordering = ['-start_date', '-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateTestSerializer
        return TestSerializer

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)
        # Notifications for new/published test are sent via users.signals_notifications.test_created_or_published

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Check if filtering for template tests
        is_template_filter = self.request.query_params.get('is_template', '').lower() == 'true'

        # Students can only see tests for their courses (never template tests)
        if user.role == UserRole.STUDENT:
            if is_template_filter:
                queryset = queryset.none()
            else:
                student_course_sections = user.classroom_users.values_list(
                    'classroom__subject_groups__sections', flat=True
                )
                queryset = queryset.filter(
                    course_section__in=student_course_sections,
                    course_section__isnull=False,  # Must have a section
                    course_section__subject_group__isnull=False,  # Exclude template sections
                    course_section__course__isnull=True  # Only regular sections
                )
        # Parents can see tests for their children's courses (never template tests)
        elif user.role == UserRole.PARENT:
            if is_template_filter:
                queryset = queryset.none()
            else:
                student_id = self.request.query_params.get('student') or self.request.query_params.get('student_id')
                if student_id:
                    try:
                        student_id = int(student_id)
                        if user.children.filter(id=student_id, role=UserRole.STUDENT).exists():
                            child_sections = User.objects.filter(id=student_id).values_list(
                                'classroom_users__classroom__subject_groups__sections', flat=True
                            ).distinct()
                            queryset = queryset.filter(
                                course_section__in=child_sections,
                                course_section__isnull=False,
                                course_section__subject_group__isnull=False,
                                course_section__course__isnull=True
                            )
                        else:
                            queryset = queryset.none()
                    except (TypeError, ValueError):
                        queryset = queryset.none()
                else:
                    children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
                    children_course_sections = Q()
                    for child_id in children_ids:
                        child = User.objects.get(id=child_id)
                        child_sections = child.classroom_users.values_list(
                            'classroom__subject_groups__sections', flat=True
                        )
                        children_course_sections |= Q(course_section__in=child_sections)
                    queryset = queryset.filter(
                        children_course_sections,
                        course_section__isnull=False,
                        course_section__subject_group__isnull=False,
                        course_section__course__isnull=True
                    )
        # Teachers can see tests they created, and template tests for courses they teach
        elif user.role == UserRole.TEACHER:
            if is_template_filter:
                # Show template tests for courses the teacher teaches
                teacher_courses = user.subject_groups.values_list('course', flat=True).distinct()
                queryset = queryset.filter(course_id__in=teacher_courses)
                # Filter by course if provided
                course_id = self.request.query_params.get('course')
                if course_id:
                    try:
                        queryset = queryset.filter(course_id=int(course_id))
                    except (ValueError, TypeError):
                        pass
            else:
                # Show tests created by teacher (regular tests, not templates)
                queryset = queryset.filter(
                    teacher=user,
                    course_section__isnull=False,
                    course_section__subject_group__isnull=False,  # Exclude template sections
                    course_section__course__isnull=True  # Only regular sections
                )
        # School admins can see tests from their school
        elif user.role == UserRole.SCHOOLADMIN:
            if is_template_filter:
                # School admins can see template tests for courses used in their school
                school_courses = Course.objects.filter(
                    subject_groups__classroom__school=user.school
                ).distinct()
                queryset = queryset.filter(course_id__in=school_courses)
            else:
                queryset = queryset.filter(
                    course_section__subject_group__classroom__school=user.school,
                    course_section__isnull=False,
                    course_section__subject_group__isnull=False,
                    course_section__course__isnull=True
                )
        # Superadmins can see all tests (default queryset)
        # But still respect is_template filter
        elif user.role == UserRole.SUPERADMIN:
            if is_template_filter:
                # Show only template tests:
                # - tests with course set (template tests)
                queryset = queryset.filter(course__isnull=False)
                # Filter by course if provided
                course_id = self.request.query_params.get('course')
                if course_id:
                    try:
                        queryset = queryset.filter(course_id=int(course_id))
                    except (ValueError, TypeError):
                        pass
            else:
                # By default, exclude template tests for superadmins too
                queryset = queryset.filter(
                    course_section__isnull=False,
                    course_section__subject_group__isnull=False,
                    course_section__course__isnull=True
                )

        return queryset

    def get_object(self):
        """
        Override get_object to ensure template tests can be accessed for deletion/update/retrieve
        even when is_template filter is not set.
        """
        # For delete/update/retrieve/copy operations, try to get the object from the base queryset
        # to avoid filtering issues (especially for template tests)
        if self.action in ['destroy', 'update', 'partial_update', 'retrieve', 'copy_from_template']:
            # Use base queryset without filters for these operations
            queryset = Test.objects.all()
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = queryset.get(**filter_kwargs)
            
            # Check permissions
            self.check_object_permissions(self.request, obj)
            return obj
        
        # For other operations, use the filtered queryset
        return super().get_object()

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """Publish a test"""
        test = self.get_object()
        test.is_published = True
        test.save()
        # Notifications sent via users.signals_notifications.test_created_or_published (elif branch)
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

    @extend_schema(
        operation_id='tests_open_to_review',
        summary='Open test results for students to review',
        request=None,
        responses={200: TestSerializer, 403: OpenApiTypes.OBJECT},
        tags=['Tests']
    )
    @action(detail=True, methods=['post'], url_path='open-to-review')
    def open_to_review(self, request, pk=None):
        """
        Allow students to see their results (answers/score) before the original reveal time.

        This sets `reveal_results_at` to current time so that:
        - `TestSerializer.can_see_results` becomes True
        - `Attempt.can_view_results` starts returning True for completed attempts.

        Intended to be used as a teacher "Open to review" button.
        """
        test = self.get_object()

        # Only the test teacher or superadmin can open results for review
        if request.user != test.teacher and request.user.role != UserRole.SUPERADMIN:
            return Response(
                {'error': 'You can only open results for your own tests'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        test.reveal_results_at = timezone.now()
        test.save(update_fields=['reveal_results_at'])

        serializer = self.get_serializer(test)
        return Response(serializer.data)

    @extend_schema(
        operation_id='tests_close_to_review',
        summary='Close test results from students review',
        request=None,
        responses={200: TestSerializer, 403: OpenApiTypes.OBJECT},
        tags=['Tests']
    )
    @action(detail=True, methods=['post'], url_path='close-to-review')
    def close_to_review(self, request, pk=None):
        """
        Hide test results from students by setting `reveal_results_at` to None.

        This makes:
        - `TestSerializer.can_see_results` become False
        - `Attempt.can_view_results` start returning False for completed attempts.

        Intended to be used as a teacher "Close to review" button.
        """
        test = self.get_object()

        # Only the test teacher or superadmin can close results for review
        if request.user != test.teacher and request.user.role != UserRole.SUPERADMIN:
            return Response(
                {'error': 'You can only close results for your own tests'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Only allow closing if test doesn't have show_score_immediately=True
        if getattr(test, 'show_score_immediately', False):
            return Response(
                {'error': 'Cannot close results for tests with immediate score visibility'},
                status=status.HTTP_400_BAD_REQUEST
            )

        test.reveal_results_at = None
        test.save(update_fields=['reveal_results_at'])

        serializer = self.get_serializer(test)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='copy-from-template')
    def copy_from_template(self, request, pk=None):
        """
        Copy a template test to a target course section.
        
        This endpoint allows teachers to copy a test from a template section
        to their own course section. The copied test will be linked to the
        template via template_test field.
        
        Request body:
        {
            "target_course_section_id": <int>
        }
        """
        template_test = self.get_object()
        
        # Verify that this is a template test
        # Template test: course_section is null OR course_section is a template section
        is_template = (
            template_test.course_section is None or
            (template_test.course_section.course and not template_test.course_section.subject_group)
        )
        
        if not is_template:
            return Response(
                {'error': 'This test is not a template test. Only template tests can be copied.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target_section_id = request.data.get('target_course_section_id')
        subject_group_id = request.data.get('subject_group_id')  # Optional: for auto-finding section
        
        # If template test has a course_section, try to find corresponding section in subject_group
        if not target_section_id and template_test.course_section and subject_group_id:
            try:
                from courses.models import SubjectGroup
                subject_group = SubjectGroup.objects.get(id=subject_group_id)
                # Find section in subject_group that corresponds to template section
                corresponding_section = CourseSection.objects.filter(
                    subject_group=subject_group,
                    template_section=template_test.course_section
                ).first()
                
                if corresponding_section:
                    target_section_id = corresponding_section.id
            except SubjectGroup.DoesNotExist:
                pass
        
        if not target_section_id:
            return Response(
                {'error': 'target_course_section_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_section = CourseSection.objects.get(id=target_section_id)
        except CourseSection.DoesNotExist:
            return Response(
                {'error': 'Target course section not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify that target section is not a template section
        if target_section.course and not target_section.subject_group:
            return Response(
                {'error': 'Cannot copy to a template section. Target must be a regular section.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify teacher has access to the target section
        if request.user.role == UserRole.TEACHER:
            if target_section.subject_group.teacher != request.user:
                return Response(
                    {'error': 'You do not have access to this course section'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check if test already exists in target section (linked to this template)
        existing_test = Test.objects.filter(
            course_section=target_section,
            template_test=template_test
        ).first()
        
        if existing_test:
            return Response(
                {'error': 'This test has already been copied to the target section'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Copy the test with all questions and options
        with transaction.atomic():
            # Create the test copy
            new_test = Test.objects.create(
                course_section=target_section,
                teacher=request.user,
                title=template_test.title,
                description=template_test.description,
                is_published=template_test.is_published,  # Use template's published status
                reveal_results_at=template_test.reveal_results_at,
                start_date=template_test.start_date,
                end_date=template_test.end_date,
                time_limit_minutes=template_test.time_limit_minutes,
                allow_multiple_attempts=template_test.allow_multiple_attempts,
                max_attempts=template_test.max_attempts,
                show_correct_answers=template_test.show_correct_answers,
                show_feedback=template_test.show_feedback,
                show_score_immediately=template_test.show_score_immediately,
                template_test=template_test,
                is_unlinked_from_template=False
            )
            
            # Copy all questions
            for template_question in template_test.questions.all().order_by('position', 'id'):
                new_question = Question.objects.create(
                    test=new_test,
                    type=template_question.type,
                    text=template_question.text,
                    points=template_question.points,
                    position=template_question.position,
                    correct_answer_text=template_question.correct_answer_text,
                    sample_answer=template_question.sample_answer,
                    key_words=template_question.key_words,
                    matching_pairs_json=template_question.matching_pairs_json
                )
                
                # Copy all options for this question
                for template_option in template_question.options.all().order_by('position', 'id'):
                    Option.objects.create(
                        question=new_question,
                        text=template_option.text,
                        image_url=template_option.image_url,
                        is_correct=template_option.is_correct,
                        position=template_option.position
                    )
        
        serializer = self.get_serializer(new_test)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='unlink-from-template')
    def unlink_from_template(self, request, pk=None):
        """
        Unlink this test from its template so it will no longer be auto-synced.
        """
        test = self.get_object()
        if not test.template_test:
            return Response(
                {'error': 'This test is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        test.is_unlinked_from_template = True
        test.save(update_fields=['is_unlinked_from_template'])
        serializer = self.get_serializer(test, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='relink-to-template')
    def relink_to_template(self, request, pk=None):
        """
        Relink this test to its template so it will be auto-synced again.
        """
        test = self.get_object()
        if not test.template_test:
            return Response(
                {'error': 'This test is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        test.is_unlinked_from_template = False
        test.save(update_fields=['is_unlinked_from_template'])
        serializer = self.get_serializer(test, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='sync-status')
    def sync_status(self, request, pk=None):
        """
        Check if test is in sync with its template.
        Returns sync status for admin and teacher users.
        """
        test = self.get_object()
        
        if not test.template_test:
            return Response({
                'is_linked': False,
                'is_unlinked': False,
                'is_outdated': False,
                'message': 'Test is not linked to any template'
            })
        
        template = test.template_test
        is_unlinked = test.is_unlinked_from_template
        
        # Check if test is outdated (compare key fields with template)
        is_outdated = False
        outdated_fields = []
        
        if not is_unlinked:
            # Compare test metadata
            if test.title != template.title:
                is_outdated = True
                outdated_fields.append('title')
            if test.description != template.description:
                is_outdated = True
                outdated_fields.append('description')
            if test.start_date != template.start_date:
                is_outdated = True
                outdated_fields.append('start_date')
            if test.end_date != template.end_date:
                is_outdated = True
                outdated_fields.append('end_date')
            if test.time_limit_minutes != template.time_limit_minutes:
                is_outdated = True
                outdated_fields.append('time_limit_minutes')
            if test.allow_multiple_attempts != template.allow_multiple_attempts:
                is_outdated = True
                outdated_fields.append('allow_multiple_attempts')
            if test.max_attempts != template.max_attempts:
                is_outdated = True
                outdated_fields.append('max_attempts')
            if test.show_correct_answers != template.show_correct_answers:
                is_outdated = True
                outdated_fields.append('show_correct_answers')
            if test.show_feedback != template.show_feedback:
                is_outdated = True
                outdated_fields.append('show_feedback')
            if test.show_score_immediately != template.show_score_immediately:
                is_outdated = True
                outdated_fields.append('show_score_immediately')
            if test.reveal_results_at != template.reveal_results_at:
                is_outdated = True
                outdated_fields.append('reveal_results_at')
            
            # Compare questions count and structure
            template_questions = template.questions.all().order_by('position', 'id')
            test_questions = test.questions.all().order_by('position', 'id')
            
            if template_questions.count() != test_questions.count():
                is_outdated = True
                outdated_fields.append('questions_count')
            else:
                # Compare each question
                for tq, q in zip(template_questions, test_questions):
                    if (tq.type != q.type or 
                        tq.text != q.text or 
                        tq.points != q.points or
                        tq.correct_answer_text != q.correct_answer_text or
                        tq.sample_answer != q.sample_answer or
                        tq.key_words != q.key_words or
                        tq.matching_pairs_json != q.matching_pairs_json):
                        is_outdated = True
                        outdated_fields.append('questions')
                        break
                    
                    # Compare options
                    template_options = tq.options.all().order_by('position', 'id')
                    test_options = q.options.all().order_by('position', 'id')
                    
                    if template_options.count() != test_options.count():
                        is_outdated = True
                        outdated_fields.append('options_count')
                        break
                    
                    for to, o in zip(template_options, test_options):
                        if (to.text != o.text or 
                            to.image_url != o.image_url or
                            to.is_correct != o.is_correct):
                            is_outdated = True
                            outdated_fields.append('options')
                            break
                    
                    if is_outdated:
                        break
        
        return Response({
            'is_linked': True,
            'is_unlinked': is_unlinked,
            'is_outdated': is_outdated,
            'outdated_fields': outdated_fields,
            'template_id': template.id,
            'message': 'Test is linked to template' if not is_outdated else 'Test is outdated compared to template'
        })

    @action(detail=True, methods=['post'], url_path='sync-from-template')
    def sync_from_template(self, request, pk=None):
        """
        Sync this test with its template.
        Only available for superadmins.
        """
        from schools.permissions import IsSuperAdmin
        
        if not IsSuperAdmin().has_permission(request, self):
            return Response(
                {'error': 'Only superadmins can sync individual tests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test = self.get_object()
        
        if not test.template_test:
            return Response(
                {'error': 'Test is not linked to any template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if test.is_unlinked_from_template:
            return Response(
                {'error': 'Test is unlinked from template and cannot be synced'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        template = test.template_test
        
        with transaction.atomic():
            # Check if test has completed attempts (submitted)
            has_completed_attempts = Attempt.objects.filter(
                test=test,
                submitted_at__isnull=False
            ).exists()
            
            # Update test fields (safe to update even with attempts)
            test.title = template.title
            test.description = template.description
            test.reveal_results_at = template.reveal_results_at
            test.start_date = template.start_date
            test.end_date = template.end_date
            test.time_limit_minutes = template.time_limit_minutes
            test.allow_multiple_attempts = template.allow_multiple_attempts
            test.max_attempts = template.max_attempts
            test.show_correct_answers = template.show_correct_answers
            test.show_feedback = template.show_feedback
            test.show_score_immediately = template.show_score_immediately
            test.save()
            
            # Sync questions and options (same logic as in sync_content)
            template_questions = template.questions.all().order_by('position', 'id')
            test_questions = test.questions.all().order_by('position', 'id')
            
            # Create a map of existing questions by position
            existing_questions_by_pos = {q.position: q for q in test_questions}
            
            for tq in template_questions:
                existing_q = existing_questions_by_pos.get(tq.position)
                
                if existing_q:
                    # Update existing question
                    # Check if question has answers
                    question_has_answers = False
                    options_with_answers = set()
                    if has_completed_attempts:
                        question_has_answers = Answer.objects.filter(
                            question=existing_q,
                            attempt__test=test,
                            attempt__submitted_at__isnull=False
                        ).exists()
                        
                        if question_has_answers:
                            options_with_answers = set(
                                Answer.objects.filter(
                                    question=existing_q,
                                    attempt__test=test,
                                    attempt__submitted_at__isnull=False
                                ).values_list('selected_options__id', flat=True)
                            )
                    
                    # Update question fields (be careful with correct_answer_text if has answers)
                    if not question_has_answers or tq.correct_answer_text == existing_q.correct_answer_text:
                        existing_q.type = tq.type
                        existing_q.text = tq.text
                        existing_q.points = tq.points
                        existing_q.correct_answer_text = tq.correct_answer_text
                        existing_q.sample_answer = tq.sample_answer
                        existing_q.key_words = tq.key_words
                        existing_q.matching_pairs_json = tq.matching_pairs_json
                        existing_q.save()
                    else:
                        # Only update safe fields if question has answers
                        existing_q.type = tq.type
                        existing_q.text = tq.text
                        existing_q.points = tq.points
                        existing_q.sample_answer = tq.sample_answer
                        existing_q.key_words = tq.key_words
                        existing_q.matching_pairs_json = tq.matching_pairs_json
                        existing_q.save()
                    
                    # Sync options
                    template_options = tq.options.all().order_by('position', 'id')
                    existing_options = existing_q.options.all().order_by('position', 'id')
                    existing_options_by_pos = {opt.position: opt for opt in existing_options}
                    
                    # Remove options that no longer exist in template (but not if they have answers)
                    for existing_opt in existing_options:
                        if not any(to.position == existing_opt.position for to in template_options):
                            if existing_opt.id not in options_with_answers:
                                existing_opt.delete()
                    
                    # Create or update options
                    for to in template_options:
                        existing_opt = existing_options_by_pos.get(to.position)
                        
                        if existing_opt:
                            # Update text and image (safe)
                            existing_opt.text = to.text
                            existing_opt.image_url = to.image_url
                            
                            # Only update is_correct if this option has no answers
                            opt_has_answers = existing_opt.id in options_with_answers
                            if not opt_has_answers:
                                existing_opt.is_correct = to.is_correct
                                existing_opt.save(update_fields=['text', 'image_url', 'is_correct'])
                            else:
                                existing_opt.save(update_fields=['text', 'image_url'])
                        else:
                            Option.objects.create(
                                question=existing_q,
                                text=to.text,
                                image_url=to.image_url,
                                is_correct=to.is_correct,
                                position=to.position
                            )
                else:
                    # Create new question
                    new_q = Question.objects.create(
                        test=test,
                        type=tq.type,
                        text=tq.text,
                        points=tq.points,
                        position=tq.position,
                        correct_answer_text=tq.correct_answer_text,
                        sample_answer=tq.sample_answer,
                        key_words=tq.key_words,
                        matching_pairs_json=tq.matching_pairs_json
                    )
                    
                    # Copy options for new question
                    for to in tq.options.all().order_by('position', 'id'):
                        Option.objects.create(
                            question=new_q,
                            text=to.text,
                            image_url=to.image_url,
                            is_correct=to.is_correct,
                            position=to.position
                        )
            
            # Remove questions that no longer exist in template (but not if they have answers)
            template_positions = {tq.position for tq in template_questions}
            for existing_q in test_questions:
                if existing_q.position not in template_positions:
                    if has_completed_attempts:
                        has_answers = Answer.objects.filter(
                            question=existing_q,
                            attempt__test=test,
                            attempt__submitted_at__isnull=False
                        ).exists()
                        if has_answers:
                            continue  # Don't delete questions with answers
                    existing_q.delete()
        
        serializer = self.get_serializer(test)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create-full')
    def create_full(self, request):
        """Create a test and its questions in a single request.
        Payload matches CreateTestSerializer, with `questions` as a list
        where each question omits the `test` field.
        """
        serializer = CreateTestSerializer(
            data=request.data, context={'request': request})
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

        # Validate teacher or superadmin access
        if request.user != test.teacher and request.user.role != UserRole.SUPERADMIN:
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

        from django.utils import timezone
        from .serializers import TestSerializer
        
        # Get test serializer to include computed fields like can_see_results
        test_serializer = TestSerializer(test, context={'request': self.request})
        
        # Determine if test is opened to review
        # Test is opened if reveal_results_at is set (not None)
        is_opened_to_review = test.reveal_results_at is not None
        
        return {
            'test': {
                'id': test.id,
                'title': test.title,
                'total_points': test.total_points,
                'total_questions': questions.count(),
                'total_students': attempts.count(),
                'can_see_results': test_serializer.data.get('can_see_results', False),
                'reveal_results_at': test.reveal_results_at.isoformat() if test.reveal_results_at else None,
                'show_score_immediately': getattr(test, 'show_score_immediately', False),
                'is_opened_to_review': is_opened_to_review
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
            answer = Answer.objects.select_related(
                'attempt__test').get(id=answer_id)

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
        answer.is_correct = (
            new_score == answer.max_score) if new_score is not None else None
        answer.save()

    def _recalculate_attempt_score(self, attempt, test):
        """Recalculate attempt total score and percentage."""
        total_score = attempt.answers.aggregate(
            Sum('score'))['score__sum'] or 0
        attempt.score = total_score
        attempt.percentage = (
            total_score / test.total_points * 100) if test.total_points > 0 else 0
        attempt.is_graded = True
        attempt.graded_at = timezone.now()
        attempt.save()

        from users.notifications_helper import notify_test_graded
        notify_test_graded(attempt, attempt.student, test.teacher)

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

    queryset = Question.objects.select_related(
        'test').prefetch_related('options').all()
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
        # Parents can see attempts of their children
        elif user.role == UserRole.PARENT:
            children_ids = user.children.filter(role=UserRole.STUDENT).values_list('id', flat=True)
            queryset = queryset.filter(student_id__in=children_ids)
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
        serializer = CreateAttemptSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            attempt = serializer.save()
            response_serializer = AttemptSerializer(
                attempt, context={'request': request})
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
        serializer = CreateAttemptSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            attempt = serializer.save()
            response_serializer = AttemptSerializer(
                attempt, context={'request': request})
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

        # If there is a time limit and it is exceeded, we still allow submission,
        # but no further answers can be added (handled in submit-answer).

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

        # Enforce per-test time limit: once time is over, answers cannot be changed/added
        if attempt.is_time_limit_exceeded:
            return Response(
                {'error': 'Time limit for this test has been exceeded. You cannot submit more answers.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmitAnswerSerializer(data=request.data)
        if serializer.is_valid():
            question_id = serializer.validated_data['question_id']

            try:
                question = Question.objects.get(
                    id=question_id, test=attempt.test)
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
        operation_id='attempts_next_question',
        summary='Get next unanswered question for an attempt',
        request=None,
        responses={200: QuestionSerializer,
                   204: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        tags=['Attempts']
    )
    @action(detail=True, methods=['get'], url_path='next-question')
    def next_question(self, request, pk=None):
        """
        Return the next unanswered question for this attempt, based on question position.

        This lets the frontend fetch questions one by one without knowing their IDs.
        If all questions are answered, returns 204 No Content.
        """
        attempt = self.get_object()

        if attempt.submitted_at:
            return Response({'error': 'Attempt already submitted'}, status=status.HTTP_400_BAD_REQUEST)

        # Respect per-test time limit: if time is over, do not provide more questions
        if attempt.is_time_limit_exceeded:
            return Response(
                {'error': 'Time limit for this test has been exceeded. No more questions can be answered.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find first question (by position, id) that has no Answer for this attempt
        answered_ids = attempt.answers.values_list('question_id', flat=True)
        next_q = attempt.test.questions.exclude(
            id__in=answered_ids).order_by('position', 'id').first()

        if not next_q:
            # All questions are already answered
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = QuestionSerializer(next_q, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id='attempts_view_results',
        summary='Mark results as viewed',
        request=None,
        responses={200: AttemptSerializer,
                   400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
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
                    answer.is_correct = (
                        answer.score == answer.max_score) if answer.score is not None else None
                    answer.save()
                    answers.append(answer)

            response_serializer = AnswerSerializer(answers, many=True)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
