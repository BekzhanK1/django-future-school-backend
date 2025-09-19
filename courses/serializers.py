from rest_framework import serializers
from datetime import datetime, timedelta
from .models import Course, SubjectGroup, CourseSection


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'course_code', 'name', 'description', 'grade']


class SubjectGroupSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    classroom_display = serializers.CharField(source='classroom.__str__', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_email = serializers.CharField(source='teacher.email', read_only=True)
    
    class Meta:
        model = SubjectGroup
        fields = ['id', 'course', 'classroom', 'teacher', 'course_name', 'course_code', 
                 'classroom_display', 'teacher_username', 'teacher_email']


class CourseSectionSerializer(serializers.ModelSerializer):
    resources = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSection
        fields = ['id', 'subject_group', 'title', 'position', 'resources', 'assignments']
    
    def get_resources(self, obj):
        from learning.serializers import ResourceTreeSerializer
        # Get root resources (no parent) for this section
        root_resources = obj.resources.filter(parent_resource__isnull=True).order_by('position', 'id')
        return ResourceTreeSerializer(root_resources, many=True, context=self.context).data
    
    def get_assignments(self, obj):
        from learning.serializers import AssignmentSerializer
        assignments = obj.assignments.all().order_by('due_at')
        return AssignmentSerializer(assignments, many=True, context=self.context).data


class CourseFullSerializer(serializers.ModelSerializer):
    subject_groups = SubjectGroupSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'course_code', 'name', 'description', 'grade', 'subject_groups']


class AutoCreateWeekSectionsSerializer(serializers.Serializer):
    subject_group_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    section_title_template = serializers.CharField(default="Week of {start_date} - {end_date}")
    
    def validate_subject_group_id(self, value):
        try:
            SubjectGroup.objects.get(id=value)
        except SubjectGroup.DoesNotExist:
            raise serializers.ValidationError("Subject group does not exist")
        return value
    
    def validate(self, attrs):
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        return attrs
    
    def create(self, validated_data):
        subject_group_id = validated_data['subject_group_id']
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']
        template = validated_data['section_title_template']
        
        # Calculate weeks
        current_date = start_date
        sections = []
        position = 0
        
        while current_date < end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            
            title = template.format(
                start_date=current_date.strftime('%d %b'),
                end_date=week_end.strftime('%d %b')
            )
            
            sections.append(CourseSection(
                subject_group_id=subject_group_id,
                title=title,
                position=position
            ))
            
            current_date = week_end + timedelta(days=1)
            position += 1
        
        return CourseSection.objects.bulk_create(sections)
