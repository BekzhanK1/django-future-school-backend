from rest_framework import serializers
from django.utils import timezone
from .models import Test, Question, Attempt, Answer


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'test', 'type', 'text', 'options_json', 'correct_json', 'points', 'position']


class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    attempt_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    can_see_results = serializers.SerializerMethodField()
    
    class Meta:
        model = Test
        fields = ['id', 'course', 'teacher', 'title', 'description', 'is_published', 
                 'scheduled_at', 'reveal_results_at', 'course_name', 'course_code', 
                 'teacher_username', 'attempt_count', 'is_available', 'can_see_results', 'questions']
    
    def get_attempt_count(self, obj):
        return obj.attempts.count()
    
    def get_is_available(self, obj):
        if not obj.is_published:
            return False
        if obj.scheduled_at and obj.scheduled_at > timezone.now():
            return False
        return True
    
    def get_can_see_results(self, obj):
        if not obj.reveal_results_at:
            return True
        return obj.reveal_results_at <= timezone.now()


class AttemptSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    test_title = serializers.CharField(source='test.title', read_only=True)
    answers = serializers.SerializerMethodField()
    
    class Meta:
        model = Attempt
        fields = ['id', 'test', 'student', 'started_at', 'submitted_at', 'graded_at',
                 'score', 'max_score', 'student_username', 'student_email', 'test_title', 'answers']
    
    def get_answers(self, obj):
        answers = obj.answers.all().order_by('question__position')
        return AnswerSerializer(answers, many=True, context=self.context).data


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.type', read_only=True)
    question_points = serializers.IntegerField(source='question.points', read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'attempt', 'question', 'selected_json', 'text_answer', 
                 'match_json', 'score', 'question_text', 'question_type', 'question_points']


class CreateAttemptSerializer(serializers.Serializer):
    test_id = serializers.IntegerField()
    
    def validate_test_id(self, value):
        try:
            test = Test.objects.get(id=value)
        except Test.DoesNotExist:
            raise serializers.ValidationError("Test does not exist")
        
        if not test.is_published:
            raise serializers.ValidationError("Test is not published")
        
        if test.scheduled_at and test.scheduled_at > timezone.now():
            raise serializers.ValidationError("Test is not yet available")
        
        return value
    
    def create(self, validated_data):
        test_id = validated_data['test_id']
        student = self.context['request'].user
        
        # Check if student already has an active attempt
        existing_attempt = Attempt.objects.filter(
            test_id=test_id, 
            student=student, 
            submitted_at__isnull=True
        ).first()
        
        if existing_attempt:
            return existing_attempt
        
        return Attempt.objects.create(
            test_id=test_id,
            student=student,
            started_at=timezone.now()
        )


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_json = serializers.CharField(required=False, allow_blank=True)
    text_answer = serializers.CharField(required=False, allow_blank=True)
    match_json = serializers.CharField(required=False, allow_blank=True)
    
    def validate_question_id(self, value):
        try:
            Question.objects.get(id=value)
        except Question.DoesNotExist:
            raise serializers.ValidationError("Question does not exist")
        return value


class BulkGradeAnswersSerializer(serializers.Serializer):
    answer_id = serializers.IntegerField()
    score = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_answer_id(self, value):
        try:
            Answer.objects.get(id=value)
        except Answer.DoesNotExist:
            raise serializers.ValidationError("Answer does not exist")
        return value
