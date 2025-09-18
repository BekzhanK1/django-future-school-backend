from django.contrib import admin
from .models import (
    Resource, Assignment, AssignmentAttachment, Submission, 
    SubmissionAttachment, Grade
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
