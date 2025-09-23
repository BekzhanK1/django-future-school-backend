from rest_framework import serializers
from .models import Resource, Assignment, AssignmentAttachment, Submission, SubmissionAttachment, Grade, Attendance, AttendanceRecord, AttendanceStatus


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


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student', 'status', 'notes', 'student_username', 'student_first_name', 'student_last_name', 'student_email']
        read_only_fields = ['id']


class AttendanceSerializer(serializers.ModelSerializer):
    subject_group_course_name = serializers.CharField(source='subject_group.course.name', read_only=True)
    subject_group_course_code = serializers.CharField(source='subject_group.course.course_code', read_only=True)
    classroom_name = serializers.CharField(source='subject_group.classroom', read_only=True)
    taken_by_username = serializers.CharField(source='taken_by.username', read_only=True)
    taken_by_first_name = serializers.CharField(source='taken_by.first_name', read_only=True)
    taken_by_last_name = serializers.CharField(source='taken_by.last_name', read_only=True)
    
    # Metrics
    total_students = serializers.ReadOnlyField()
    present_count = serializers.ReadOnlyField()
    excused_count = serializers.ReadOnlyField()
    not_present_count = serializers.ReadOnlyField()
    attendance_percentage = serializers.ReadOnlyField()
    
    # Records
    records = AttendanceRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = Attendance
        fields = ['id', 'subject_group', 'taken_by', 'taken_at', 'notes',
                 'subject_group_course_name', 'subject_group_course_code', 'classroom_name',
                 'taken_by_username', 'taken_by_first_name', 'taken_by_last_name',
                 'total_students', 'present_count', 'excused_count', 'not_present_count', 
                 'attendance_percentage', 'records']
        read_only_fields = ['id', 'taken_at']


class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attendance with bulk student records"""
    records = AttendanceRecordSerializer(many=True)
    
    class Meta:
        model = Attendance
        fields = ['subject_group', 'notes', 'records']
    
    def create(self, validated_data):
        records_data = validated_data.pop('records')
        attendance = Attendance.objects.create(**validated_data)
        
        for record_data in records_data:
            AttendanceRecord.objects.create(attendance=attendance, **record_data)
        
        return attendance
    
    def validate_subject_group(self, value):
        """Ensure the user has permission to take attendance for this subject group"""
        user = self.context['request'].user
        
        # Check if user is teacher of this subject group
        if user.role == 'teacher' and value.teacher != user:
            raise serializers.ValidationError("You can only take attendance for subject groups you teach.")
        
        # Superadmin and school admin can take attendance for any subject group
        if user.role not in ['teacher', 'superadmin', 'schooladmin']:
            raise serializers.ValidationError("You don't have permission to take attendance.")
        
        return value


class AttendanceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating attendance records"""
    records = AttendanceRecordSerializer(many=True)
    
    class Meta:
        model = Attendance
        fields = ['notes', 'records']
    
    def update(self, instance, validated_data):
        records_data = validated_data.pop('records', None)
        
        # Update attendance notes
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        
        # Update records if provided
        if records_data is not None:
            # Delete existing records
            instance.records.all().delete()
            
            # Create new records
            for record_data in records_data:
                AttendanceRecord.objects.create(attendance=instance, **record_data)
        
        return instance


class StudentAttendanceHistorySerializer(serializers.ModelSerializer):
    """Serializer for student's attendance history"""
    subject_group_course_name = serializers.CharField(source='attendance.subject_group.course.name', read_only=True)
    subject_group_course_code = serializers.CharField(source='attendance.subject_group.course.course_code', read_only=True)
    classroom_name = serializers.CharField(source='attendance.subject_group.classroom', read_only=True)
    taken_at = serializers.DateTimeField(source='attendance.taken_at', read_only=True)
    taken_by_username = serializers.CharField(source='attendance.taken_by.username', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = ['id', 'status', 'notes', 'subject_group_course_name', 'subject_group_course_code',
                 'classroom_name', 'taken_at', 'taken_by_username']


class AttendanceMetricsSerializer(serializers.Serializer):
    """Serializer for attendance metrics and statistics"""
    total_sessions = serializers.IntegerField()
    present_count = serializers.IntegerField()
    excused_count = serializers.IntegerField()
    not_present_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
    subject_group_name = serializers.CharField()
    classroom_name = serializers.CharField()
    course_name = serializers.CharField()
