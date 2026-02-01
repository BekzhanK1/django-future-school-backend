from django.contrib import admin
from .models import Course, SubjectGroup, CourseSection, ScheduleSlot, AcademicYear, Holiday


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'name', 'grade', 'description')
    list_filter = ('grade',)
    search_fields = ('course_code', 'name', 'description')
    ordering = ('grade', 'course_code')

    fieldsets = (
        (None, {'fields': ('course_code', 'name', 'grade')}),
        ('Description', {'fields': ('description',)}),
    )


@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    list_display = ('course', 'classroom', 'teacher')
    list_filter = ('course', 'classroom__school', 'teacher__role')
    search_fields = ('course__name', 'classroom__school__name',
                     'teacher__username')
    autocomplete_fields = ('course', 'classroom', 'teacher')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course', 'classroom__school', 'teacher')


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject_group',
                    'position', 'start_date', 'end_date')
    list_filter = ('subject_group__course', 'subject_group__classroom__school')
    search_fields = ('title', 'subject_group__course__name')
    autocomplete_fields = ('subject_group',)
    ordering = ('subject_group', 'position', 'id')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject_group__course', 'subject_group__classroom__school')


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('subject_group', 'day_of_week',
                    'start_time', 'end_time', 'room')
    list_filter = ('subject_group__course', 'subject_group__classroom__school')
    search_fields = ('subject_group__course__name',
                     'subject_group__classroom__school__name')
    autocomplete_fields = ('subject_group',)
    ordering = ('subject_group', 'day_of_week', 'start_time')


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('name',)
    ordering = ('start_date', 'id')
