from django.contrib import admin
from .models import Lesson, Recording


class RecordingInline(admin.TabularInline):
    model = Recording
    extra = 0
    fields = ('storage_provider', 'file_url', 'duration_seconds', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('topic', 'course', 'teacher', 'starts_at', 'ends_at', 'has_meeting_link')
    list_filter = ('course', 'teacher__role', 'starts_at')
    search_fields = ('topic', 'description', 'course__name', 'teacher__username')
    autocomplete_fields = ('course', 'teacher')
    date_hierarchy = 'starts_at'
    inlines = [RecordingInline]
    
    fieldsets = (
        (None, {'fields': ('topic', 'course', 'teacher', 'description')}),
        ('Schedule', {'fields': ('starts_at', 'ends_at')}),
        ('Meeting', {'fields': ('meeting_link',)}),
    )
    
    def has_meeting_link(self, obj):
        return bool(obj.meeting_link)
    has_meeting_link.boolean = True
    has_meeting_link.short_description = 'Has Meeting Link'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course', 'teacher')


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'lesson', 'storage_provider', 'duration_seconds', 'created_at')
    list_filter = ('storage_provider', 'created_at', 'lesson__course')
    search_fields = ('lesson__topic', 'file_url')
    autocomplete_fields = ('lesson',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lesson__course', 'lesson__teacher')
