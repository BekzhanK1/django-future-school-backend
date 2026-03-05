import rest_framework.serializers as serializers
from .models_ktp import AcademicPlan, PlanSubjectGroup, PlanQuarterDetail, Section, LearningObjective, Lesson
from courses.serializers import CourseSerializer, SubjectGroupSerializer, QuarterSerializer

class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = '__all__'


class LessonSerializer(serializers.ModelSerializer):
    objectives = LearningObjectiveSerializer(many=True, read_only=True)
    objective_ids = serializers.PrimaryKeyRelatedField(
        queryset=LearningObjective.objects.all(), 
        many=True, 
        write_only=True, 
        source='objectives',
        required=False
    )

    class Meta:
        model = Lesson
        fields = '__all__'


class SectionSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = '__all__'


class PlanQuarterDetailSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    quarter = QuarterSerializer(read_only=True)
    quarter_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PlanQuarterDetail
        fields = '__all__'


class PlanSubjectGroupSerializer(serializers.ModelSerializer):
    subject_group = SubjectGroupSerializer(read_only=True)
    subject_group_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PlanSubjectGroup
        fields = '__all__'


class AcademicPlanSerializer(serializers.ModelSerializer):
    plan_subject_groups = PlanSubjectGroupSerializer(many=True, read_only=True)
    quarter_details = PlanQuarterDetailSerializer(many=True, read_only=True)
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AcademicPlan
        fields = '__all__'
