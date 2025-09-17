from django.contrib import admin
from .models import Resource, Assignment, AssignmentAttachment, Submission, Grade

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'course_section', 'parent_resource', 'position')
    list_filter = ('type', 'course_section')
    search_fields = ('title', 'description')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course_section', 'teacher', 'due_at')
    list_filter = ('course_section', 'teacher')
    search_fields = ('title', 'description')

@admin.register(AssignmentAttachment)
class AssignmentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'assignment', 'position')
    list_filter = ('type', 'assignment')
    search_fields = ('title',)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'submitted_at')
    list_filter = ('assignment', 'student')
    search_fields = ('text',)

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'graded_by', 'grade_value', 'graded_at')
    list_filter = ('graded_by', 'grade_value')
    search_fields = ('feedback',)
