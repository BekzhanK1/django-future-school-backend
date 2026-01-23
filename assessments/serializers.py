from rest_framework import serializers
from django.utils import timezone
from .models import Test, Question, Option, Attempt, Answer, QuestionType
from courses.models import CourseSection, SubjectGroup
from users.models import UserRole


class OptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(
        required=False, allow_null=True)  # Allow id for updates

    class Meta:
        model = Option
        fields = ['id', 'text', 'image_url', 'is_correct', 'position']
        # id is not read_only when updating (for nested updates)


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    options_count = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'test', 'type', 'text', 'points', 'position',
            'correct_answer_text', 'sample_answer', 'key_words', 'matching_pairs_json',
            'options', 'options_count'
        ]
        read_only_fields = ['id']

    def get_options_count(self, obj):
        return obj.options.count()


class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    course_section_title = serializers.CharField(
        source='course_section.title', read_only=True)
    course_name = serializers.CharField(
        source='course_section.subject_group.course.name', read_only=True)
    course_code = serializers.CharField(
        source='course_section.subject_group.course.course_code', read_only=True)
    subject_group = serializers.IntegerField(
        source='course_section.subject_group.id', read_only=True)
    classroom_name = serializers.CharField(
        source='course_section.subject_group.classroom.__str__', read_only=True)
    classroom_grade = serializers.IntegerField(
        source='course_section.subject_group.classroom.grade', read_only=True)
    classroom_letter = serializers.CharField(
        source='course_section.subject_group.classroom.letter', read_only=True)
    teacher_username = serializers.CharField(
        source='teacher.username', read_only=True)
    teacher_fullname = serializers.CharField(
        source='teacher.get_full_name', read_only=True)
    teacher_first_name = serializers.CharField(
        source='teacher.first_name', read_only=True)
    teacher_last_name = serializers.CharField(
        source='teacher.last_name', read_only=True)
    total_points = serializers.ReadOnlyField()
    attempt_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    can_see_results = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    is_deadline_passed = serializers.SerializerMethodField()
    has_attempted = serializers.SerializerMethodField()
    is_submitted = serializers.SerializerMethodField()
    my_active_attempt_id = serializers.SerializerMethodField()
    last_submitted_attempt_id = serializers.SerializerMethodField()
    my_latest_attempt_can_view_results = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            'id', 'course_section', 'teacher', 'title', 'description', 'is_published',
            'reveal_results_at', 'start_date', 'end_date', 'time_limit_minutes',
            'allow_multiple_attempts', 'max_attempts', 'show_correct_answers', 'show_feedback', 'show_score_immediately',
            'course_section_title', 'course_name', 'course_code', 'subject_group',
            'classroom_name', 'classroom_grade', 'classroom_letter', 'teacher_username', 'teacher_fullname',
            'teacher_first_name', 'teacher_last_name', 'total_points', 'attempt_count',
            'is_available', 'can_see_results', 'can_attempt', 'is_deadline_passed', 'has_attempted',
            'is_submitted', 'my_active_attempt_id', 'last_submitted_attempt_id', 'my_latest_attempt_can_view_results',
            'template_test', 'is_unlinked_from_template', 'questions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_attempt_count(self, obj):
        return obj.attempts.count()

    def get_is_available(self, obj):
        """
        Determine if test is available for students.

        Rules:
        - Test must be published
        - If start_date is set, current time must be >= start_date
        - If end_date is set, current time must be <= end_date
        - If both dates are null, test is always available (open test)
        """
        if not obj.is_published:
            return False

        now = timezone.now()

        # If start_date is set, check if test has started
        if obj.start_date is not None and now < obj.start_date:
            return False

        # If end_date is set, check if test has not ended
        if obj.end_date is not None and now > obj.end_date:
            return False

        # If dates are null or within range, test is available
        return True

    def get_can_see_results(self, obj):
        """
        Determine if, in principle, results for this test can be visible to students.

        Rules:
        - If `show_score_immediately` is True, results can be seen right after completion.
        - Otherwise, results are only visible when `reveal_results_at` is set and
          the current time has passed it (including when teacher presses open-to-review,
          which sets `reveal_results_at=now`).
        """
        if getattr(obj, "show_score_immediately", False):
            return True
        if not obj.reveal_results_at:
            return False
        return obj.reveal_results_at <= timezone.now()

    def get_can_attempt(self, obj):
        if not self.get_is_available(obj):
            return False

        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return False

        user = request.user
        if user.role != 'student':
            return False

        # Check if student has reached max attempts
        if obj.max_attempts:
            current_attempts = obj.attempts.filter(student=user).count()
            if current_attempts >= obj.max_attempts:
                return False

        return True

    def get_is_deadline_passed(self, obj):
        if obj.end_date:
            return timezone.now() > obj.end_date
        return False

    def get_has_attempted(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return False
        return obj.attempts.filter(student=user).exists()

    def get_is_submitted(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return False
        return obj.attempts.filter(student=user, submitted_at__isnull=False).exists()

    def get_my_active_attempt_id(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return None
        try:
            active_attempt = obj.attempts.filter(
                student=user, submitted_at__isnull=True).order_by('-started_at').first()
            return active_attempt.id if active_attempt else None
        except Exception:
            return None

    def get_last_submitted_attempt_id(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return None
        try:
            last_finished = obj.attempts.filter(
                student=user,
                submitted_at__isnull=False
            ).order_by('-submitted_at', '-attempt_number', '-started_at').first()
            return last_finished.id if last_finished else None
        except Exception:
            return None

    def get_my_latest_attempt_can_view_results(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return False
        latest_attempt = obj.attempts.filter(student=user).order_by(
            '-submitted_at', '-attempt_number', '-started_at').first()
        if not latest_attempt:
            return False
        return bool(latest_attempt.can_view_results)


class AttemptSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source='student.username', read_only=True)
    student_email = serializers.CharField(
        source='student.email', read_only=True)
    student_first_name = serializers.CharField(
        source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(
        source='student.last_name', read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    answers = serializers.SerializerMethodField()
    can_view_results = serializers.ReadOnlyField()
    time_spent_minutes = serializers.ReadOnlyField()
    percentage = serializers.ReadOnlyField()
    time_limit_minutes = serializers.IntegerField(
        source='test.time_limit_minutes', read_only=True)

    class Meta:
        model = Attempt
        fields = [
            'id', 'test', 'student', 'attempt_number', 'started_at', 'submitted_at', 'graded_at',
            'score', 'max_score', 'percentage', 'is_completed', 'is_graded', 'results_viewed_at',
            'student_username', 'student_email', 'student_first_name', 'student_last_name',
            'test_title', 'can_view_results', 'time_spent_minutes', 'time_limit_minutes', 'answers'
        ]
        read_only_fields = ['id', 'student', 'attempt_number', 'started_at', 'submitted_at', 'graded_at',
                            'score', 'max_score', 'percentage', 'is_completed', 'is_graded', 'results_viewed_at']

    def get_answers(self, obj):
        """
        Return serialized answers for this attempt.

        For students, answers are only visible when `can_view_results` is True.
        Teachers and admins can always see answers.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        # If the current user is the student and results are not yet available, hide answers
        if user and getattr(user, "role", None) == UserRole.STUDENT and not obj.can_view_results:
            return []

        answers = obj.answers.all().order_by('question__position')
        return AnswerSerializer(answers, many=True, context=self.context).data

    def to_representation(self, instance):
        """
        Hide score-related fields for students until results are available.
        """
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        if user and getattr(user, "role", None) == UserRole.STUDENT and not instance.can_view_results:
            # Keep meta (timestamps, status) but hide evaluation details
            data['score'] = None
            data['max_score'] = None
            data['percentage'] = None
            # answers are already hidden via get_answers, but ensure consistency
            data['answers'] = []

        return data


class AnswerSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_options = OptionSerializer(many=True, read_only=True)
    max_score = serializers.ReadOnlyField()
    is_correct = serializers.ReadOnlyField()

    # Student information
    student_id = serializers.IntegerField(
        source='attempt.student.id', read_only=True)
    student_username = serializers.CharField(
        source='attempt.student.username', read_only=True)
    student_email = serializers.CharField(
        source='attempt.student.email', read_only=True)
    student_first_name = serializers.CharField(
        source='attempt.student.first_name', read_only=True)
    student_last_name = serializers.CharField(
        source='attempt.student.last_name', read_only=True)

    class Meta:
        model = Answer
        fields = [
            'id', 'attempt', 'question', 'selected_options', 'text_answer', 'matching_answers_json',
            'score', 'max_score', 'is_correct', 'teacher_feedback', 'auto_feedback',
            'student_id', 'student_username', 'student_email', 'student_first_name', 'student_last_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateAttemptSerializer(serializers.Serializer):
    test = serializers.PrimaryKeyRelatedField(queryset=Test.objects.all())

    def validate_test(self, value):
        # value is a Test instance
        test = value
        if not test.is_published:
            raise serializers.ValidationError("Test is not published")

        if test.start_date and test.start_date > timezone.now():
            raise serializers.ValidationError("Test is not yet available")

        if test.end_date and test.end_date < timezone.now():
            raise serializers.ValidationError("Test has already ended")

        # Check if student has reached max attempts
        student = self.context['request'].user
        if test.max_attempts:
            current_attempts = test.attempts.filter(student=student).count()
            if current_attempts >= test.max_attempts:
                raise serializers.ValidationError("Maximum attempts reached")

        return value

    def create(self, validated_data):
        test = validated_data['test']
        student = self.context['request'].user

        # Check if student already has an active attempt
        existing_attempt = Attempt.objects.filter(
            test=test,
            student=student,
            submitted_at__isnull=True
        ).first()

        if existing_attempt:
            return existing_attempt

        # Get next attempt number
        last_attempt = Attempt.objects.filter(
            test=test,
            student=student
        ).order_by('-attempt_number').first()

        attempt_number = (last_attempt.attempt_number +
                          1) if last_attempt else 1

        return Attempt.objects.create(
            test=test,
            student=student,
            attempt_number=attempt_number
        )


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    text_answer = serializers.CharField(required=False, allow_blank=True)
    matching_answers_json = serializers.JSONField(
        required=False, allow_null=True)

    def validate_question_id(self, value):
        try:
            Question.objects.get(id=value)
        except Question.DoesNotExist:
            raise serializers.ValidationError("Question does not exist")
        return value

    def validate_selected_option_ids(self, value):
        if value:
            # Validate that all option IDs exist and belong to the question
            question_id = self.initial_data.get('question_id')
            if question_id:
                valid_options = Option.objects.filter(
                    question_id=question_id,
                    id__in=value
                ).values_list('id', flat=True)
                invalid_ids = set(value) - set(valid_options)
                if invalid_ids:
                    raise serializers.ValidationError(
                        f"Invalid option IDs: {list(invalid_ids)}")
        return value


class BulkGradeAnswersSerializer(serializers.Serializer):
    answer_id = serializers.IntegerField()
    score = serializers.FloatField(required=False, allow_null=True)
    teacher_feedback = serializers.CharField(required=False, allow_blank=True)

    def validate_answer_id(self, value):
        try:
            Answer.objects.get(id=value)
        except Answer.DoesNotExist:
            raise serializers.ValidationError("Answer does not exist")
        return value


class ViewResultsSerializer(serializers.Serializer):
    """Serializer for marking results as viewed by student"""
    pass


class CreateQuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'test', 'type', 'text', 'points', 'position',
            'correct_answer_text', 'sample_answer', 'key_words', 'matching_pairs_json', 'options'
        ]

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)

        for option_data in options_data:
            Option.objects.create(question=question, **option_data)

        return question


class NestedQuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating questions nested under Test create/update.
    Does not require or accept the `test` field; it will be set by the parent.
    Supports updating existing questions by including `id` field.
    """
    id = serializers.IntegerField(
        required=False, allow_null=True)  # For updating existing questions
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'type', 'text', 'points', 'position',
            'correct_answer_text', 'sample_answer', 'key_words', 'matching_pairs_json', 'options'
        ]


class CreateTestSerializer(serializers.ModelSerializer):
    # Use nested question serializer that doesn't require `test` field
    questions = NestedQuestionCreateSerializer(many=True, required=False)
    course_section = serializers.PrimaryKeyRelatedField(
        queryset=CourseSection.objects.all(),
        required=False,
        allow_null=True
    )
    subject_group = serializers.PrimaryKeyRelatedField(
        queryset=SubjectGroup.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Test
        fields = [
            'course_section', 'subject_group', 'title', 'description', 'is_published',
            'reveal_results_at', 'start_date', 'end_date', 'time_limit_minutes',
            'allow_multiple_attempts', 'max_attempts', 'show_correct_answers',
            'show_feedback', 'show_score_immediately', 'questions'
        ]

    def validate(self, data):
        """Auto-assign course_section based on start_date and subject_group if not provided"""
        course_section = data.get('course_section')
        subject_group = data.get('subject_group')
        start_date = data.get('start_date')

        # IMPORTANT: If course_section is explicitly provided, NEVER auto-assign (respect user's choice)
        # Only auto-assign if course_section is not provided and start_date is provided
        # This is especially important for template tests where user selects a specific section
        original_course_section = course_section  # Save original value

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"CreateTestSerializer.validate: original_course_section={original_course_section}, subject_group={subject_group}, start_date={start_date}")

        if not course_section and start_date and subject_group:
            # Only auto-assign for regular tests (with subject_group), not for template tests
            from django.utils import timezone

            # Convert start_date to date for comparison
            test_date = start_date.date() if hasattr(start_date, 'date') else start_date

            # Build query to find course section that contains this date
            query = CourseSection.objects.filter(
                start_date__lte=test_date,
                end_date__gte=test_date
            )

            # Filter by subject_group
            query = query.filter(subject_group=subject_group)

            auto_assigned_section = query.first()

            if auto_assigned_section:
                data['course_section'] = auto_assigned_section
            else:
                error_msg = f"No course section found for the start date {test_date}"
                error_msg += f" in subject group {subject_group.id}"
                error_msg += ". Please provide a course_section or ensure there's a section with start_date <= {test_date} <= end_date."
                raise serializers.ValidationError(error_msg)

        # CRITICAL: Always preserve explicitly provided course_section (for template tests)
        # This ensures user's selection is never overwritten by auto-assignment
        if original_course_section:
            data['course_section'] = original_course_section
            logger.info(
                f"CreateTestSerializer.validate: Preserving original course_section={original_course_section}")

        # Use original_course_section for final check (preserves user's choice)
        final_course_section = original_course_section if original_course_section else course_section

        # Allow null course_section for template tests (when creating template tests without section)
        # Only require course_section for regular tests (with subject_group)
        if not final_course_section and subject_group:
            raise serializers.ValidationError(
                "Either course_section must be provided or start_date must be provided "
                "to auto-assign a course section."
            )
        # For template tests (no subject_group), course_section can be null

        # Remove subject_group from data since it's not a field on Test model
        if 'subject_group' in data:
            del data['subject_group']

        return data

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])

        # Set teacher from context if not provided
        if 'teacher' not in validated_data:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                validated_data['teacher'] = request.user

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"CreateTestSerializer.create: course_section={validated_data.get('course_section')}, validated_data keys={list(validated_data.keys())}")

        test = Test.objects.create(**validated_data)

        logger.info(
            f"CreateTestSerializer.create: Created test with course_section={test.course_section}")

        for question_data in questions_data:
            options_data = question_data.pop('options', [])
            question = Question.objects.create(test=test, **question_data)

            for option_data in options_data:
                Option.objects.create(question=question, **option_data)

        return test

    def update(self, instance, validated_data):
        """
        Update test and its questions/options.
        Handles nested question updates similar to create.
        """
        from django.db import transaction
        from assessments.models import Attempt, Answer

        questions_data = validated_data.pop('questions', [])

        # Check if test has completed attempts
        has_completed_attempts = Attempt.objects.filter(
            test=instance,
            submitted_at__isnull=False
        ).exists()

        # Update test fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update questions if provided
        if questions_data:
            with transaction.atomic():
                # Get existing questions
                existing_questions = {
                    q.id: q for q in instance.questions.all()}
                existing_question_ids = set(existing_questions.keys())

                # Process questions from request
                new_question_ids = set()

                for question_data in questions_data:
                    question_id = question_data.get('id')
                    options_data = question_data.pop('options', [])

                    if question_id and question_id in existing_questions:
                        # Update existing question
                        existing_q = existing_questions[question_id]

                        # Check if question has answers from completed attempts
                        question_has_answers = False
                        if has_completed_attempts:
                            question_has_answers = Answer.objects.filter(
                                question=existing_q,
                                attempt__test=instance,
                                attempt__submitted_at__isnull=False
                            ).exists()

                        # Update question fields
                        existing_q.text = question_data.get(
                            'text', existing_q.text)
                        existing_q.points = question_data.get(
                            'points', existing_q.points)
                        existing_q.position = question_data.get(
                            'position', existing_q.position)
                        existing_q.type = question_data.get(
                            'type', existing_q.type)
                        existing_q.sample_answer = question_data.get(
                            'sample_answer', existing_q.sample_answer)
                        existing_q.key_words = question_data.get(
                            'key_words', existing_q.key_words)
                        existing_q.matching_pairs_json = question_data.get(
                            'matching_pairs_json', existing_q.matching_pairs_json)

                        # Only update correct_answer_text if no completed attempts
                        if not question_has_answers:
                            existing_q.correct_answer_text = question_data.get(
                                'correct_answer_text', existing_q.correct_answer_text)

                        existing_q.save()
                        new_question_ids.add(existing_q.id)

                        # Update options
                        if options_data:
                            existing_options = {
                                opt.id: opt for opt in existing_q.options.all()}
                            existing_option_ids = set(existing_options.keys())
                            new_option_ids = set()

                            # Check which options have answers
                            options_with_answers = set()
                            if question_has_answers:
                                options_with_answers = set(
                                    Answer.objects.filter(
                                        question=existing_q,
                                        attempt__test=instance,
                                        attempt__submitted_at__isnull=False
                                    ).values_list('selected_options__id', flat=True)
                                )

                            for option_data in options_data:
                                option_id = option_data.get('id')

                                if option_id and option_id in existing_options:
                                    # Update existing option
                                    existing_opt = existing_options[option_id]
                                    existing_opt.text = option_data.get(
                                        'text', existing_opt.text)
                                    existing_opt.image_url = option_data.get(
                                        'image_url', existing_opt.image_url)
                                    existing_opt.position = option_data.get(
                                        'position', existing_opt.position)

                                    # Only update is_correct if no answers
                                    if existing_opt.id not in options_with_answers:
                                        existing_opt.is_correct = option_data.get(
                                            'is_correct', existing_opt.is_correct)

                                    existing_opt.save()
                                    new_option_ids.add(existing_opt.id)
                                else:
                                    # Create new option
                                    new_opt = Option.objects.create(
                                        question=existing_q,
                                        text=option_data.get('text', ''),
                                        image_url=option_data.get('image_url'),
                                        is_correct=option_data.get(
                                            'is_correct', False),
                                        position=option_data.get('position', 0)
                                    )
                                    new_option_ids.add(new_opt.id)

                            # Delete options that are no longer in request (if no answers)
                            for opt_id in existing_option_ids - new_option_ids:
                                if opt_id not in options_with_answers:
                                    existing_options[opt_id].delete()
                    else:
                        # Create new question
                        new_q = Question.objects.create(
                            test=instance,
                            text=question_data.get('text', ''),
                            type=question_data.get('type', 'multiple_choice'),
                            points=question_data.get('points', 1),
                            position=question_data.get('position', 0),
                            correct_answer_text=question_data.get(
                                'correct_answer_text'),
                            sample_answer=question_data.get('sample_answer'),
                            key_words=question_data.get('key_words'),
                            matching_pairs_json=question_data.get(
                                'matching_pairs_json')
                        )
                        new_question_ids.add(new_q.id)

                        # Create options for new question
                        for option_data in options_data:
                            Option.objects.create(
                                question=new_q,
                                text=option_data.get('text', ''),
                                image_url=option_data.get('image_url'),
                                is_correct=option_data.get(
                                    'is_correct', False),
                                position=option_data.get('position', 0)
                            )

                # Delete questions that are no longer in request (if no answers)
                for q_id in existing_question_ids - new_question_ids:
                    if has_completed_attempts:
                        question_has_answers = Answer.objects.filter(
                            question_id=q_id,
                            attempt__test=instance,
                            attempt__submitted_at__isnull=False
                        ).exists()
                        if question_has_answers:
                            continue  # Don't delete questions with answers
                    existing_questions[q_id].delete()

        return instance
