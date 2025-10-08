from rest_framework import serializers
from django.utils import timezone
from .models import Test, Question, Option, Attempt, Answer, QuestionType
from courses.models import CourseSection, SubjectGroup


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'image_url', 'is_correct', 'position']
        read_only_fields = ['id']


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
    course_section_title = serializers.CharField(source='course_section.title', read_only=True)
    course_name = serializers.CharField(source='course_section.subject_group.course.name', read_only=True)
    course_code = serializers.CharField(source='course_section.subject_group.course.course_code', read_only=True)
    subject_group = serializers.IntegerField(source='course_section.subject_group.id', read_only=True)
    classroom_name = serializers.CharField(source='course_section.subject_group.classroom.__str__', read_only=True)
    classroom_grade = serializers.IntegerField(source='course_section.subject_group.classroom.grade', read_only=True)
    classroom_letter = serializers.CharField(source='course_section.subject_group.classroom.letter', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_fullname = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_first_name = serializers.CharField(source='teacher.first_name', read_only=True)
    teacher_last_name = serializers.CharField(source='teacher.last_name', read_only=True)
    total_points = serializers.ReadOnlyField()
    attempt_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    can_see_results = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    is_deadline_passed = serializers.SerializerMethodField()
    has_attempted = serializers.SerializerMethodField()
    my_active_attempt_id = serializers.SerializerMethodField()
    last_submitted_attempt_id = serializers.SerializerMethodField()
    my_latest_attempt_can_view_results = serializers.SerializerMethodField()
    
    class Meta:
        model = Test
        fields = [
            'id', 'course_section', 'teacher', 'title', 'description', 'is_published',
            'scheduled_at', 'reveal_results_at', 'start_date', 'end_date', 'allow_multiple_attempts',
            'max_attempts', 'show_correct_answers', 'show_feedback', 'show_score_immediately',
            'course_section_title', 'course_name', 'course_code', 'subject_group',
            'classroom_name', 'classroom_grade', 'classroom_letter', 'teacher_username',
            'teacher_first_name', 'teacher_last_name', 'total_points', 'attempt_count',
            'is_available', 'can_see_results', 'can_attempt', 'is_deadline_passed', 'has_attempted',
            'my_active_attempt_id', 'last_submitted_attempt_id', 'my_latest_attempt_can_view_results',
            'questions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attempt_count(self, obj):
        return obj.attempts.count()
    
    def get_is_available(self, obj):
        if not obj.is_published:
            return False
        if obj.start_date and timezone.now() < obj.start_date:
            return False
        if obj.end_date and timezone.now() > obj.end_date:
            return False
        return True
    
    def get_can_see_results(self, obj):
        if not obj.reveal_results_at:
            return True
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

    def get_my_active_attempt_id(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return None
        try:
            active_attempt = obj.attempts.filter(student=user, submitted_at__isnull=True).order_by('-started_at').first()
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
        latest_attempt = obj.attempts.filter(student=user).order_by('-submitted_at', '-attempt_number', '-started_at').first()
        if not latest_attempt:
            return False
        return bool(latest_attempt.can_view_results)


class AttemptSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    answers = serializers.SerializerMethodField()
    can_view_results = serializers.ReadOnlyField()
    time_spent_minutes = serializers.ReadOnlyField()
    percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Attempt
        fields = [
            'id', 'test', 'student', 'attempt_number', 'started_at', 'submitted_at', 'graded_at',
            'score', 'max_score', 'percentage', 'is_completed', 'is_graded', 'results_viewed_at',
            'student_username', 'student_email', 'student_first_name', 'student_last_name',
            'test_title', 'can_view_results', 'time_spent_minutes', 'answers'
        ]
        read_only_fields = ['id', 'student', 'attempt_number', 'started_at', 'submitted_at', 'graded_at', 'score', 'max_score', 'percentage', 'is_completed', 'is_graded', 'results_viewed_at']
    
    def get_answers(self, obj):
        answers = obj.answers.all().order_by('question__position')
        return AnswerSerializer(answers, many=True, context=self.context).data


class AnswerSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_options = OptionSerializer(many=True, read_only=True)
    max_score = serializers.ReadOnlyField()
    is_correct = serializers.ReadOnlyField()
    
    # Student information
    student_id = serializers.IntegerField(source='attempt.student.id', read_only=True)
    student_username = serializers.CharField(source='attempt.student.username', read_only=True)
    student_email = serializers.CharField(source='attempt.student.email', read_only=True)
    student_first_name = serializers.CharField(source='attempt.student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='attempt.student.last_name', read_only=True)
    
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
        
        if test.scheduled_at and test.scheduled_at > timezone.now():
            raise serializers.ValidationError("Test is not yet available")
        
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
        
        attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1
        
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
    matching_answers_json = serializers.JSONField(required=False, allow_null=True)
    
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
                    raise serializers.ValidationError(f"Invalid option IDs: {list(invalid_ids)}")
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
    """Serializer for creating questions nested under Test create.
    Does not require or accept the `test` field; it will be set by the parent.
    """
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'type', 'text', 'points', 'position',
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
            'scheduled_at', 'reveal_results_at', 'start_date', 'end_date',
            'allow_multiple_attempts', 'max_attempts', 'show_correct_answers',
            'show_feedback', 'show_score_immediately', 'questions'
        ]
    
    def validate(self, data):
        """Auto-assign course_section based on scheduled_at and subject_group if not provided"""
        course_section = data.get('course_section')
        subject_group = data.get('subject_group')
        scheduled_at = data.get('scheduled_at')
        
        # If course_section is not provided but scheduled_at is, try to auto-assign
        if not course_section and scheduled_at:
            from django.utils import timezone
            
            # Convert scheduled_at to date for comparison
            test_date = scheduled_at.date() if hasattr(scheduled_at, 'date') else scheduled_at
            
            # Build query to find course section that contains this date
            query = CourseSection.objects.filter(
                start_date__lte=test_date,
                end_date__gte=test_date
            )
            
            # If subject_group is provided, filter by it
            if subject_group:
                query = query.filter(subject_group=subject_group)
            
            course_section = query.first()
            
            if course_section:
                data['course_section'] = course_section
            else:
                error_msg = f"No course section found for the scheduled date {test_date}"
                if subject_group:
                    error_msg += f" in subject group {subject_group.id}"
                error_msg += ". Please provide a course_section or ensure there's a section with start_date <= {test_date} <= end_date."
                raise serializers.ValidationError(error_msg)
        
        # If neither course_section nor scheduled_at is provided, raise error
        if not course_section:
            raise serializers.ValidationError(
                "Either course_section must be provided or scheduled_at must be provided "
                "to auto-assign a course section."
            )
        
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
        
        test = Test.objects.create(**validated_data)
        
        for question_data in questions_data:
            options_data = question_data.pop('options', [])
            question = Question.objects.create(test=test, **question_data)
            
            for option_data in options_data:
                Option.objects.create(question=question, **option_data)
        
        return test
