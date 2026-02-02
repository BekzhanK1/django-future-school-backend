from django.contrib import admin
from .models import (
    Resource, Assignment, AssignmentAttachment, Submission,
    SubmissionAttachment, Grade, ManualGrade, GradeWeight, Attendance, AttendanceRecord,
)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'course_section', 'parent_resource', 'position')
    list_filter = ('type', 'course_section__subject_group__course')
    search_fields = ('title', 'description')
    autocomplete_fields = ('course_section', 'parent_resource')
    ordering = ('course_section', 'position', 'id')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'course_section__subject_group__course',
            'parent_resource'
        )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course_section', 'teacher', 'due_at', 'max_grade')
    list_filter = ('course_section__subject_group__course', 'teacher__role')
    search_fields = ('title', 'description', 'teacher__username')
    autocomplete_fields = ('course_section', 'teacher')
    date_hierarchy = 'due_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'course_section__subject_group__course',
            'teacher'
        )


@admin.register(AssignmentAttachment)
class AssignmentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'assignment', 'position')
    list_filter = ('type', 'assignment__course_section__subject_group__course')
    search_fields = ('title', 'assignment__title')
    autocomplete_fields = ('assignment',)
    ordering = ('assignment', 'position', 'id')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'submitted_at')
    list_filter = ('assignment__course_section__subject_group__course', 'student__role')
    search_fields = ('text', 'student__username', 'assignment__title')
    autocomplete_fields = ('assignment', 'student')
    date_hierarchy = 'submitted_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'assignment__course_section__subject_group__course',
            'student'
        )


@admin.register(SubmissionAttachment)
class SubmissionAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'submission', 'position')
    list_filter = ('type', 'submission__assignment__course_section__subject_group__course')
    search_fields = ('title', 'submission__assignment__title')
    autocomplete_fields = ('submission',)
    ordering = ('submission', 'position', 'id')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'graded_by', 'grade_value', 'graded_at')
    list_filter = ('graded_by__role', 'grade_value', 'graded_at')
    search_fields = ('feedback', 'submission__student__username', 'graded_by__username')
    autocomplete_fields = ('submission', 'graded_by')
    readonly_fields = ('graded_at',)
    date_hierarchy = 'graded_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'submission__assignment__course_section__subject_group__course',
            'submission__student',
            'graded_by'
        )


@admin.register(ManualGrade)
class ManualGradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'subject_group', 'value', 'max_value', 'title', 'grade_type', 'graded_by', 'graded_at')
    list_filter = ('grade_type', 'subject_group__course', 'graded_at')
    search_fields = ('title', 'student__username', 'feedback')
    autocomplete_fields = ('student', 'subject_group', 'course_section', 'graded_by')
    readonly_fields = ('graded_at',)
    date_hierarchy = 'graded_at'


@admin.register(GradeWeight)
class GradeWeightAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject_group', 'source_type', 'weight')
    list_filter = ('source_type', 'subject_group__course')
    search_fields = ('subject_group__course__name',)
    autocomplete_fields = ('subject_group',)


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ('student', 'status', 'notes')
    autocomplete_fields = ('student',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject_group', 'taken_by', 'taken_at', 'total_students', 'present_count', 'excused_count', 'not_present_count', 'attendance_percentage')
    list_filter = ('subject_group__course', 'subject_group__classroom', 'taken_by__role', 'taken_at')
    search_fields = ('subject_group__course__name', 'notes', 'taken_by__username')
    autocomplete_fields = ('subject_group', 'taken_by')
    date_hierarchy = 'taken_at'
    inlines = [AttendanceRecordInline]
    readonly_fields = ('taken_at', 'total_students', 'present_count', 'excused_count', 'not_present_count', 'attendance_percentage')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'subject_group__course',
            'subject_group__classroom',
            'taken_by'
        ).prefetch_related('records__student')
    
    def total_students(self, obj):
        return obj.total_students
    total_students.short_description = 'Total Students'
    
    def present_count(self, obj):
        return obj.present_count
    present_count.short_description = 'Present'
    
    def excused_count(self, obj):
        return obj.excused_count
    excused_count.short_description = 'Excused'
    
    def not_present_count(self, obj):
        return obj.not_present_count
    not_present_count.short_description = 'Not Present'
    
    def attendance_percentage(self, obj):
        return f"{obj.attendance_percentage}%"
    attendance_percentage.short_description = 'Attendance %'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'attendance', 'student', 'status', 'attendance_date', 'attendance_course')
    list_filter = ('status', 'attendance__subject_group__course', 'attendance__taken_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'notes')
    autocomplete_fields = ('attendance', 'student')
    date_hierarchy = 'attendance__taken_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attendance__subject_group__course',
            'attendance__subject_group__classroom',
            'student'
        )
    
    def attendance_date(self, obj):
        return obj.attendance.taken_at.strftime('%Y-%m-%d %H:%M')
    attendance_date.short_description = 'Date'
    attendance_date.admin_order_field = 'attendance__taken_at'
    
    def attendance_course(self, obj):
        return obj.attendance.subject_group.course.name
    attendance_course.short_description = 'Course'
    attendance_course.admin_order_field = 'attendance__subject_group__course__name'


from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'type', 'start_at', 'end_at', 'school', 'subject_group', 'course_section')
	list_filter = ('type', 'school')
	search_fields = ('title', 'description')
	autocomplete_fields = ('school', 'subject_group', 'course_section', 'created_by')
	date_hierarchy = 'start_at'
