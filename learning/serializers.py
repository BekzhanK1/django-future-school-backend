from rest_framework import serializers
from .models import Resource, Assignment, AssignmentAttachment, Submission, SubmissionAttachment, Grade


class ResourceSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_title = serializers.CharField(source='parent_resource.title', read_only=True)
    
    class Meta:
        model = Resource
        fields = ['id', 'course_section', 'parent_resource', 'parent_title', 'type', 
                 'title', 'description', 'url', 'file', 'position', 'children']
    
    def get_children(self, obj):
        children = obj.children.all().order_by('position', 'id')
        return ResourceSerializer(children, many=True, context=self.context).data


class ResourceTreeSerializer(serializers.ModelSerializer):
    """Serializer for displaying resource tree structure"""
    children = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    
    class Meta:
        model = Resource
        fields = ['id', 'type', 'title', 'description', 'url', 'file', 'position', 'children', 'level']
    
    def get_children(self, obj):
        children = obj.children.all().order_by('position', 'id')
        return ResourceTreeSerializer(children, many=True, context=self.context).data
    
    def get_level(self, obj):
        level = 0
        parent = obj.parent_resource
        while parent:
            level += 1
            parent = parent.parent_resource
        return level


class AssignmentAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentAttachment
        fields = ['id', 'type', 'title', 'content', 'file_url', 'file', 'position', 'assignment']


class AssignmentSerializer(serializers.ModelSerializer):
    course_section_title = serializers.CharField(source='course_section.title', read_only=True)
    subject_group_course_name = serializers.CharField(source='course_section.subject_group.course.name', read_only=True)
    subject_group_course_code = serializers.CharField(source='course_section.subject_group.course.course_code', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    submission_count = serializers.SerializerMethodField()
    attachments = AssignmentAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Assignment
        fields = ['id', 'course_section', 'teacher', 'title', 'description', 'due_at', 'max_grade', 'file',
                 'course_section_title', 'subject_group_course_name', 'subject_group_course_code', 
                 'teacher_username', 'submission_count', 'attachments']
    
    def get_submission_count(self, obj):
        return obj.submissions.count()


class SubmissionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionAttachment
        fields = ['id', 'type', 'title', 'content', 'file_url', 'file', 'position', 'submission']


class SubmissionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_max_grade = serializers.IntegerField(source='assignment.max_grade', read_only=True)
    grade_value = serializers.SerializerMethodField()
    grade_feedback = serializers.SerializerMethodField()
    graded_at = serializers.SerializerMethodField()
    attachments = SubmissionAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'student', 'submitted_at', 'text', 'file',
                 'student_username', 'student_email', 'student_first_name', 'student_last_name', 
                 'assignment_title', 'assignment_max_grade', 'grade_value', 'grade_feedback', 'graded_at', 'attachments']
    
    def get_grade_value(self, obj):
        try:
            return obj.grade.grade_value
        except Grade.DoesNotExist:
            return None
    
    def get_grade_feedback(self, obj):
        try:
            return obj.grade.feedback
        except Grade.DoesNotExist:
            return None
    
    def get_graded_at(self, obj):
        try:
            return obj.grade.graded_at
        except Grade.DoesNotExist:
            return None


class GradeSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='submission.student.username', read_only=True)
    student_first_name = serializers.CharField(source='submission.student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='submission.student.last_name', read_only=True)
    assignment_title = serializers.CharField(source='submission.assignment.title', read_only=True)
    graded_by_username = serializers.CharField(source='graded_by.username', read_only=True)
    graded_by_first_name = serializers.CharField(source='graded_by.first_name', read_only=True)
    graded_by_last_name = serializers.CharField(source='graded_by.last_name', read_only=True)
    
    class Meta:
        model = Grade
        fields = ['id', 'submission', 'graded_by', 'grade_value', 'feedback', 'graded_at',
                 'student_username', 'student_first_name', 'student_last_name', 'assignment_title', 
                 'graded_by_username', 'graded_by_first_name', 'graded_by_last_name']


class BulkGradeSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField()
    grade_value = serializers.IntegerField()
    feedback = serializers.CharField(required=False, allow_blank=True)
    
    def validate_submission_id(self, value):
        try:
            Submission.objects.get(id=value)
        except Submission.DoesNotExist:
            raise serializers.ValidationError("Submission does not exist")
        return value
