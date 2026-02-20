from rest_framework import serializers
from .models import (
    Resource, Assignment, AssignmentAttachment, Submission, SubmissionAttachment,
    Grade, ManualGrade, ManualGradeType, GradeWeight, Attendance, AttendanceRecord, Event,
)
from users.models import UserRole, User


def _parse_form_boolean(value):
    """Parse boolean from form data: 'false'/'true' strings or list of one such string (multipart)."""
    if value in (True, False):
        return bool(value)
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ('true', '1', 'yes'):
        return True
    if s in ('false', '0', 'no', ''):
        return False
    return None


class FormDataBooleanField(serializers.BooleanField):
    """BooleanField that correctly parses multipart form values like 'false' and ['false']."""

    def to_internal_value(self, data):
        parsed = _parse_form_boolean(data)
        if parsed is not None:
            return parsed
        return super().to_internal_value(data)


class ResourceSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_title = serializers.CharField(source='parent_resource.title', read_only=True)
    is_visible_to_students = FormDataBooleanField(required=False, default=True)

    class Meta:
        model = Resource
        fields = ['id', 'course_section', 'parent_resource', 'parent_title', 'type',
                 'title', 'description', 'url', 'file', 'position', 'children',
                 'template_resource', 'is_unlinked_from_template', 'is_visible_to_students']
    
    def get_children(self, obj):
        children = obj.children.all().order_by('position', 'id')
        return ResourceSerializer(children, many=True, context=self.context).data


class ResourceTreeSerializer(serializers.ModelSerializer):
    """Serializer for displaying resource tree structure"""
    children = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    
    class Meta:
        model = Resource
        fields = ['id', 'type', 'title', 'description', 'url', 'file', 'position', 'children', 'level',
                 'template_resource', 'is_unlinked_from_template', 'is_visible_to_students']
    
    def get_children(self, obj):
        children = obj.children.all().order_by('position', 'id')
        
        # Apply permission filtering if user is in context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            if user.role == UserRole.STUDENT:
                # Filter children based on student's classroom enrollment and visibility
                student_classrooms = user.classroom_users.values_list('classroom', flat=True)
                children = children.filter(
                    course_section__subject_group__classroom__in=student_classrooms,
                    is_visible_to_students=True
                )
            elif user.role == UserRole.PARENT:
                children = children.filter(is_visible_to_students=True)
        
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
        extra_kwargs = {
            # Allow nested creation without explicitly providing assignment id
            'assignment': { 'required': False }
        }


class AssignmentSerializer(serializers.ModelSerializer):
    course_section_title = serializers.CharField(source='course_section.title', read_only=True)
    subject_group_course_name = serializers.CharField(source='course_section.subject_group.course.name', read_only=True)
    subject_group_course_code = serializers.CharField(source='course_section.subject_group.course.course_code', read_only=True)
    classroom = serializers.SerializerMethodField()
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_fullname = serializers.CharField(source='teacher.get_full_name', read_only=True)
    submission_count = serializers.SerializerMethodField()
    # Allow reading existing attachments and writing new ones in one request
    attachments = AssignmentAttachmentSerializer(many=True, required=False)
    is_available = serializers.SerializerMethodField()
    is_deadline_passed = serializers.SerializerMethodField()
    is_submitted = serializers.SerializerMethodField()
    student_submission = serializers.SerializerMethodField()
    all_submissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'course_section', 'teacher', 'title', 'description',
            'due_at', 'max_grade', 'file',
            # Template-relative scheduling fields (used primarily for template sections)
            'template_offset_days_from_section_start', 'template_due_time',
            # Template link fields
            'template_assignment', 'is_unlinked_from_template',
            'course_section_title', 'subject_group_course_name', 'subject_group_course_code',
            'teacher_username', 'teacher_fullname', 'submission_count', 'attachments', 'classroom',
            'is_available', 'is_deadline_passed', 'is_submitted', 'student_submission', 'all_submissions',
        ]
    

    def get_classroom(self, obj):
        return obj.course_section.subject_group.classroom.__str__()

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def get_is_available(self, obj):
        from django.utils import timezone
        if not obj.due_at:
            return True
        return timezone.now() < obj.due_at

    def get_is_deadline_passed(self, obj):
        from django.utils import timezone
        if not obj.due_at:
            return False
        return timezone.now() >= obj.due_at

    def get_is_submitted(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        user = request.user
        # Only meaningful for students
        try:
            return obj.submissions.filter(student=user).exists()
        except Exception:
            return False
    
    def get_student_submission(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return None
        user = request.user
        
        # Only return submission for students
        if user.role != UserRole.STUDENT:
            return None
        
        try:
            submission = obj.submissions.filter(student=user).first()
            if submission:
                return SubmissionSerializer(submission, context=self.context).data
            return None
        except Exception:
            return None
    
    def get_all_submissions(self, obj):
        """Return all submissions for teachers, None for students"""
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return None
        user = request.user
        
        # Only return all submissions for teachers
        if user.role != UserRole.TEACHER:
            return None
        
        try:
            submissions = obj.submissions.all().order_by('-submitted_at')
            return SubmissionSerializer(submissions, many=True, context=self.context).data
        except Exception:
            return None

    def create(self, validated_data):
        attachments_data = validated_data.pop('attachments', [])
        assignment = Assignment.objects.create(**validated_data)
        # Create nested attachments if provided
        for attachment_data in attachments_data:
            AssignmentAttachment.objects.create(assignment=assignment, **attachment_data)
        return assignment


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
    grade_id = serializers.SerializerMethodField()
    grade_value = serializers.SerializerMethodField()
    grade_feedback = serializers.SerializerMethodField()
    graded_at = serializers.SerializerMethodField()
    attachments = SubmissionAttachmentSerializer(many=True, read_only=True)
    student = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'student', 'submitted_at', 'text', 'file',
                 'student_username', 'student_email', 'student_first_name', 'student_last_name', 
                 'assignment_title', 'assignment_max_grade', 'grade_id', 'grade_value', 'grade_feedback', 'graded_at', 'attachments']
    
    def get_grade_id(self, obj):
        try:
            return obj.grade.id
        except Grade.DoesNotExist:
            return None
    
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


class ManualGradeSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    subject_group_display = serializers.SerializerMethodField()
    course_section_title = serializers.CharField(source='course_section.title', read_only=True, allow_null=True)
    graded_by_username = serializers.CharField(source='graded_by.username', read_only=True)
    grade_type_display = serializers.CharField(source='get_grade_type_display', read_only=True)

    def get_subject_group_display(self, obj):
        return str(obj.subject_group) if obj.subject_group else None

    class Meta:
        model = ManualGrade
        fields = [
            'id', 'student', 'subject_group', 'course_section',
            'value', 'max_value', 'title', 'grade_type', 'grade_type_display',
            'graded_by', 'graded_at', 'feedback',
            'student_username', 'student_first_name', 'student_last_name',
            'subject_group_display', 'course_section_title', 'graded_by_username',
        ]
        read_only_fields = ['graded_at', 'graded_by']

    def create(self, validated_data):
        validated_data['graded_by'] = self.context['request'].user
        return super().create(validated_data)


class GradeWeightSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)

    class Meta:
        model = GradeWeight
        fields = ['id', 'subject_group', 'source_type', 'source_type_display', 'weight']

    def validate(self, attrs):
        subject_group_id = attrs.get('subject_group') or (self.instance and self.instance.subject_group_id)
        source_type = attrs.get('source_type') or (self.instance and self.instance.source_type)
        weight = attrs.get('weight')
        if weight is None and self.instance:
            weight = self.instance.weight
        if subject_group_id is not None and weight is not None and source_type:
            from .models import GradeWeight
            current = dict(
                GradeWeight.objects.filter(subject_group_id=subject_group_id).values_list('source_type', 'weight')
            )
            current[source_type] = weight
            if set(current.keys()) == {'assignment', 'test', 'manual'} and sum(current.values()) != 100:
                raise serializers.ValidationError(
                    {'weight': 'Сумма весов по предмету должна быть 100%.'}
                )
        return attrs


class GradeWeightBulkSerializer(serializers.Serializer):
    """Сохранение всех трёх весов одним запросом (сумма должна быть 100%)."""
    subject_group = serializers.IntegerField()
    assignment = serializers.IntegerField(min_value=0, max_value=100)
    test = serializers.IntegerField(min_value=0, max_value=100)
    manual = serializers.IntegerField(min_value=0, max_value=100)

    def validate(self, attrs):
        total = attrs['assignment'] + attrs['test'] + attrs['manual']
        if total != 100:
            raise serializers.ValidationError(
                {'assignment': 'Сумма весов по предмету должна быть 100%.'}
            )
        return attrs


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


class EventSerializer(serializers.ModelSerializer):
    subject_group_display = serializers.SerializerMethodField()
    target_users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)
    target_users_details = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'type', 'start_at', 'end_at', 'is_all_day', 'location',
            'target_audience', 'school', 'subject_group', 'subject_group_display', 'course_section',
            'target_users', 'target_users_details', 'created_by', 'created_at', 'updated_at'
        ]

    def get_subject_group_display(self, obj):
        if obj.subject_group:
            return str(obj.subject_group.classroom)
        return None

    def get_target_users_details(self, obj):
        return [
            {
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name or '',
                'last_name': u.last_name or '',
            }
            for u in obj.target_users.all()
        ]

    def create(self, validated_data):
        target_users = validated_data.pop('target_users', [])
        user = self.context['request'].user
        if not validated_data.get('school') and user.school_id:
            validated_data['school'] = user.school
        event = super().create(validated_data)
        event.target_users.set(target_users)
        return event

    def update(self, instance, validated_data):
        target_users = validated_data.pop('target_users', None)
        result = super().update(instance, validated_data)
        if target_users is not None:
            instance.target_users.set(target_users)
        return result


from datetime import date, datetime, time

from .models import EventType


class RecurringEventCreateSerializer(serializers.Serializer):
	title = serializers.CharField(max_length=255)
	description = serializers.CharField(required=False, allow_blank=True)
	location = serializers.CharField(required=False, allow_blank=True)
	is_all_day = serializers.BooleanField(default=False)
	
	# Target
	subject_group = serializers.IntegerField(required=False)
	course_section = serializers.IntegerField(required=False)
	school = serializers.IntegerField(required=False)
	
	# Recurrence
	start_date = serializers.DateField()
	end_date = serializers.DateField(required=False)
	weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), allow_empty=False)
	start_time = serializers.TimeField()
	end_time = serializers.TimeField()
	
	def validate(self, attrs):
		start_date = attrs['start_date']
		end_date = attrs.get('end_date')
		start_time = attrs['start_time']
		end_time = attrs['end_time']
		if end_time <= start_time:
			raise serializers.ValidationError('end_time must be after start_time')
		if end_date and end_date < start_date:
			raise serializers.ValidationError('end_date must be on or after start_date')
		if not attrs.get('subject_group') and not attrs.get('course_section') and not attrs.get('school'):
			raise serializers.ValidationError('Provide at least one of subject_group, course_section, or school')
		return attrs
