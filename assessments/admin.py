from django.contrib import admin
from .models import Test, Question, Attempt, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('type', 'text', 'points', 'position')
    ordering = ('position', 'id')


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'teacher', 'is_published', 'scheduled_at', 'reveal_results_at')
    list_filter = ('is_published', 'course', 'teacher__role', 'scheduled_at')
    search_fields = ('title', 'description', 'course__name', 'teacher__username')
    autocomplete_fields = ('course', 'teacher')
    date_hierarchy = 'scheduled_at'
    inlines = [QuestionInline]
    
    fieldsets = (
        (None, {'fields': ('title', 'course', 'teacher', 'description')}),
        ('Publishing', {'fields': ('is_published', 'scheduled_at', 'reveal_results_at')}),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course', 'teacher')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'type', 'text_preview', 'points', 'position')
    list_filter = ('type', 'test__course', 'test__teacher__role')
    search_fields = ('text', 'test__title')
    autocomplete_fields = ('test',)
    ordering = ('test', 'position', 'id')
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('test__course', 'test__teacher')


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'started_at', 'submitted_at', 'graded_at', 'score', 'max_score')
    list_filter = ('test__course', 'student__role', 'graded_at', 'submitted_at')
    search_fields = ('test__title', 'student__username', 'student__email')
    autocomplete_fields = ('test', 'student')
    date_hierarchy = 'submitted_at'
    readonly_fields = ('started_at', 'submitted_at', 'graded_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('test__course', 'student')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'attempt', 'question', 'score', 'has_text_answer', 'has_selected_json')
    list_filter = ('attempt__test__course', 'attempt__student__role', 'score')
    search_fields = ('attempt__student__username', 'question__text')
    autocomplete_fields = ('attempt', 'question')
    
    def has_text_answer(self, obj):
        return bool(obj.text_answer)
    has_text_answer.boolean = True
    has_text_answer.short_description = 'Has Text Answer'
    
    def has_selected_json(self, obj):
        return bool(obj.selected_json)
    has_selected_json.boolean = True
    has_selected_json.short_description = 'Has Selected JSON'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attempt__test__course',
            'attempt__student',
            'question'
        )
