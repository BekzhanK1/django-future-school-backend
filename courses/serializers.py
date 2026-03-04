from rest_framework import serializers
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from .models import Course, SubjectGroup, CourseSection
from .models_schedule import ScheduleSlot, DayOfWeek
from .models_academic_year import AcademicYear, Holiday, Quarter
from microsoft_graph.serializers import ShortOnlineMeetingSerializer


class TimeFieldHHMM(serializers.TimeField):
    """Accept time as HH:MM or HH:MM:SS."""
    input_formats = ['%H:%M', '%H:%M:%S', '%H:%M:%S.%f']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'course_code', 'name',
                  'description', 'grade', 'language']


class HolidaySerializer(serializers.ModelSerializer):
    """Serializer for holidays"""
    class Meta:
        model = Holiday
        fields = [
            'id',
            'academic_year',
            'name',
            'start_date',
            'end_date',
            'is_recurring',
        ]


class QuarterSerializer(serializers.ModelSerializer):
    """Serializer for quarter"""
    class Meta:
        model = Quarter
        fields = [
            'id',
            'quarter_index',
            'start_date',
            'end_date',
        ]
        read_only_fields = ['id', 'quarter_index']


class AcademicYearSerializer(serializers.ModelSerializer):
    """Serializer for academic year"""
    additional_holidays = HolidaySerializer(many=True, read_only=True)
    quarters = QuarterSerializer(many=True, required=False)
    
    quarter1_weeks = serializers.IntegerField(write_only=True, required=False, default=8)
    quarter2_weeks = serializers.IntegerField(write_only=True, required=False, default=8)
    quarter3_weeks = serializers.IntegerField(write_only=True, required=False, default=10)
    quarter4_weeks = serializers.IntegerField(write_only=True, required=False, default=8)
    
    class Meta:
        model = AcademicYear
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'quarters',
            'quarter1_weeks',
            'quarter2_weeks',
            'quarter3_weeks',
            'quarter4_weeks',
            'autumn_holiday_start',
            'autumn_holiday_end',
            'winter_holiday_start',
            'winter_holiday_end',
            'spring_holiday_start',
            'spring_holiday_end',
            'is_active',
            'additional_holidays',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @transaction.atomic
    def create(self, validated_data):
        # Extract week counts
        weeks = [
            validated_data.pop('quarter1_weeks', 8),
            validated_data.pop('quarter2_weeks', 8),
            validated_data.pop('quarter3_weeks', 10),
            validated_data.pop('quarter4_weeks', 8),
        ]
        quarters_data = validated_data.pop('quarters', None)
        
        academic_year = super().create(validated_data)
        
        # Calculate quarters from weeks
        current_date = academic_year.start_date
        for q in range(1, 5):
            quarter_weeks = weeks[q - 1]
            days_to_add = quarter_weeks * 7
            quarter_end = current_date + timedelta(days=days_to_add - 1)
            
            # Adjust for holidays in Q1
            if q == 1 and academic_year.autumn_holiday_start and academic_year.autumn_holiday_end:
                if academic_year.autumn_holiday_start <= quarter_end:
                    days_to_add += (academic_year.autumn_holiday_end - academic_year.autumn_holiday_start).days + 1
            
            quarter_end = current_date + timedelta(days=days_to_add - 1)
            
            Quarter.objects.create(
                academic_year=academic_year,
                quarter_index=q,
                start_date=current_date,
                end_date=quarter_end
            )
            
            current_date = quarter_end + timedelta(days=1)
            
        return academic_year

    @transaction.atomic
    def update(self, instance, validated_data):
        quarters_data = validated_data.pop('quarters', None)
        
        # Pop write-only week fields in case frontend still sends them on update
        validated_data.pop('quarter1_weeks', None)
        validated_data.pop('quarter2_weeks', None)
        validated_data.pop('quarter3_weeks', None)
        validated_data.pop('quarter4_weeks', None)

        instance = super().update(instance, validated_data)

        if quarters_data is not None:
            # Map existing quarters by index
            existing_quarters = {q.quarter_index: q for q in instance.quarters.all()}
            for i, q_data in enumerate(quarters_data):
                # The frontend might just pass the list of 4 quarters in order.
                # Assuming quarters_data has the same indices 1 to 4 or based on order.
                q_idx = q_data.get('quarter_index', i + 1)
                quarter = existing_quarters.get(q_idx)
                if quarter:
                    quarter.start_date = q_data.get('start_date', quarter.start_date)
                    quarter.end_date = q_data.get('end_date', quarter.end_date)
                    quarter.save()
                    
        return instance


class ScheduleSlotSerializer(serializers.ModelSerializer):
    """Serializer for schedule slots"""
    start_time = TimeFieldHHMM()
    end_time = TimeFieldHHMM()
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    subject_group_course_name = serializers.CharField(
        source='subject_group.course.name', read_only=True
    )
    subject_group_classroom_display = serializers.CharField(
        source='subject_group.classroom.__str__', read_only=True
    )
    subject_group_teacher_fullname = serializers.CharField(
        source='subject_group.teacher.get_full_name', read_only=True
    )
    subject_group_teacher_username = serializers.CharField(
        source='subject_group.teacher.username', read_only=True
    )
    subject_group_color = serializers.CharField(
        source='subject_group.color', read_only=True
    )
    
    class Meta:
        model = ScheduleSlot
        fields = [
            'id',
            'subject_group',
            'subject_group_course_name',
            'subject_group_classroom_display',
            'subject_group_teacher_fullname',
            'subject_group_teacher_username',
            'subject_group_color',
            'day_of_week',
            'day_of_week_display',
            'start_time',
            'end_time',
            'room',
            'start_date',
            'end_date',
            'quarter',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubjectGroupSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(
        source='course.course_code', read_only=True)
    classroom_display = serializers.CharField(
        source='classroom.__str__', read_only=True)
    teacher_username = serializers.CharField(
        source='teacher.username', read_only=True)
    teacher_fullname = serializers.CharField(
        source='teacher.get_full_name', read_only=True)
    teacher_email = serializers.CharField(
        source='teacher.email', read_only=True)
    external_id = serializers.CharField(read_only=True)
    online_meeting = serializers.SerializerMethodField()
    schedule_slots = ScheduleSlotSerializer(many=True, read_only=True)

    def get_online_meeting(self, obj):
        online_meeting = getattr(obj, 'online_meeting', None)
        if online_meeting is not None:
            return ShortOnlineMeetingSerializer(online_meeting, context=self.context).data
        return None

    class Meta:
        model = SubjectGroup
        fields = ['id', 'course', 'classroom', 'teacher', 'course_name', 'course_code',
                  'classroom_display', 'teacher_username', 'teacher_fullname', 'teacher_email', 'external_id', 'online_meeting', 'schedule_slots', 'color']


class CourseSectionSerializer(serializers.ModelSerializer):
    resources = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    tests = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = CourseSection
        fields = [
            'id',
            'course',
            'subject_group',
            'template_section',
            'title',
            'position',
            'is_current',
            'is_general',
            'start_date',
            'end_date',
            'quarter',
            # Template-relative scheduling fields (meaningful for template sections)
            'template_week_index',
            'template_start_offset_days',
            'template_duration_days',
            'resources',
            'assignments',
            'tests',
        ]

    def get_resources(self, obj):
        from learning.serializers import ResourceTreeSerializer
        from users.models import UserRole

        # IMPORTANT: Students should NOT see template sections (where subject_group is null)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            if user.role == UserRole.STUDENT:
                # If this is a template section (subject_group is null), return empty list
                if obj.subject_group is None:
                    return []
                # Verify student is enrolled in the classroom of this section
                student_classrooms = user.classroom_users.values_list(
                    'classroom', flat=True)
                if obj.subject_group.classroom_id not in student_classrooms:
                    return []

        # Get root resources (no parent) for this section
        root_resources = obj.resources.filter(
            parent_resource__isnull=True).order_by('position', 'id')
        # Students and parents must not see resources hidden from students (backend enforcement)
        if request and request.user.is_authenticated and request.user.role in (UserRole.STUDENT, UserRole.PARENT):
            root_resources = root_resources.filter(is_visible_to_students=True)

        return ResourceTreeSerializer(root_resources, many=True, context=self.context).data

    def get_is_current(self, obj):
        # A section is current if today is within its date range and it's not general
        if obj.is_general:
            return False
        if not obj.start_date or not obj.end_date:
            return False
        today = timezone.now().date()
        return obj.start_date <= today <= obj.end_date

    def get_assignments(self, obj):
        from learning.serializers import AssignmentSerializer
        from users.models import UserRole

        # IMPORTANT: Students should NOT see template sections (where subject_group is null)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            if user.role == UserRole.STUDENT:
                # If this is a template section (subject_group is null), return empty list
                if obj.subject_group is None:
                    return []
                # Verify student is enrolled in the classroom of this section
                student_classrooms = user.classroom_users.values_list(
                    'classroom', flat=True)
                if obj.subject_group.classroom_id not in student_classrooms:
                    return []

        assignments = obj.assignments.all().order_by('due_at')

        return AssignmentSerializer(assignments, many=True, context=self.context).data

    def get_tests(self, obj):
        from assessments.serializers import TestSerializer
        from users.models import UserRole

        # IMPORTANT: Students should NOT see template sections (where subject_group is null)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            if user.role == UserRole.STUDENT:
                # If this is a template section (subject_group is null), return empty list
                if obj.subject_group is None:
                    return []
                # Verify student is enrolled in the classroom of this section
                student_classrooms = user.classroom_users.values_list(
                    'classroom', flat=True)
                if obj.subject_group.classroom_id not in student_classrooms:
                    return []

        tests = obj.tests.all().order_by('start_date', 'id')
        return TestSerializer(tests, many=True, context=self.context).data


class CourseFullSerializer(serializers.ModelSerializer):
    subject_groups = SubjectGroupSerializer(many=True, read_only=True)
    subject_groups_count = serializers.SerializerMethodField()
    template_sections_count = serializers.SerializerMethodField()

    def get_subject_groups_count(self, obj):
        """Count of subject groups using this course"""
        return obj.subject_groups.count()

    def get_template_sections_count(self, obj):
        """Count of template sections (where subject_group is null) for this course"""
        return CourseSection.objects.filter(course=obj, subject_group__isnull=True).count()

    class Meta:
        model = Course
        fields = ['id', 'course_code', 'name', 'description', 'grade', 'language', 'subject_groups',
                  'subject_groups_count', 'template_sections_count']


class AutoCreateWeekSectionsSerializer(serializers.Serializer):
    subject_group_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    section_title_template = serializers.CharField(
        default="Week of {start_date} - {end_date}")

    def validate_subject_group_id(self, value):
        try:
            SubjectGroup.objects.get(id=value)
        except SubjectGroup.DoesNotExist:
            raise serializers.ValidationError("Subject group does not exist")
        return value

    def validate(self, attrs):
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError(
                "End date must be after start date")
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
