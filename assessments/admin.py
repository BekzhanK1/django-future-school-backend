from django.contrib import admin
from django.utils.html import format_html
from .models import Test, Question, Option, Attempt, Answer, QuestionType


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    fields = ('text', 'image_url', 'is_correct', 'position')
    ordering = ('position', 'id')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('type', 'text', 'points', 'position')
    ordering = ('position', 'id')
    show_change_link = True


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_section', 'teacher', 'is_published', 'total_points', 'time_limit_minutes', 'scheduled_at')
    list_filter = ('is_published', 'course_section__subject_group__course', 'teacher__role', 'scheduled_at', 'allow_multiple_attempts')
    search_fields = ('title', 'description', 'course_section__title', 'teacher__username')
    autocomplete_fields = ('course_section', 'teacher')
    date_hierarchy = 'scheduled_at'
    inlines = [QuestionInline]
    
    fieldsets = (
        (None, {'fields': ('title', 'course_section', 'teacher', 'description')}),
        ('Publishing', {'fields': ('is_published', 'scheduled_at', 'reveal_results_at')}),
        ('Time Management', {'fields': ('time_limit_minutes', 'allow_multiple_attempts', 'max_attempts')}),
        ('Result Visibility', {'fields': ('show_correct_answers', 'show_feedback', 'show_score_immediately')}),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'course_section__subject_group__course',
            'course_section__subject_group__classroom__school',
            'teacher'
        )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'type', 'text_preview', 'points', 'position', 'options_count')
    list_filter = ('type', 'test__course_section__subject_group__course', 'test__teacher__role')
    search_fields = ('text', 'test__title')
    autocomplete_fields = ('test',)
    ordering = ('test', 'position', 'id')
    inlines = [OptionInline]
    
    fieldsets = (
        (None, {'fields': ('test', 'type', 'text', 'points', 'position')}),
        ('Open Question Settings', {'fields': ('correct_answer_text', 'sample_answer')}),
        ('Matching Question Settings', {'fields': ('matching_pairs_json',)}),
    )
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'
    
    def options_count(self, obj):
        count = obj.options.count()
        if obj.type in [QuestionType.MULTIPLE_CHOICE, QuestionType.CHOOSE_ALL]:
            return f"{count} options"
        return "-"
    options_count.short_description = 'Options'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'test__course_section__subject_group__course',
            'test__teacher'
        )


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'text_preview', 'image_preview', 'is_correct', 'position')
    list_filter = ('is_correct', 'question__type', 'question__test__course_section__subject_group__course')
    search_fields = ('text', 'question__text')
    autocomplete_fields = ('question',)
    ordering = ('question', 'position', 'id')
    
    def text_preview(self, obj):
        if obj.text:
            return obj.text[:30] + '...' if len(obj.text) > 30 else obj.text
        return "-"
    text_preview.short_description = 'Text'
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" width="50" height="50" />', obj.image_url)
        return "-"
    image_preview.short_description = 'Image'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'question__test__course_section__subject_group__course'
        )


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'attempt_number', 'started_at', 'submitted_at', 'is_completed', 'score_display', 'percentage_display', 'time_spent_display')
    list_filter = ('test__course_section__subject_group__course', 'student__role', 'is_completed', 'is_graded', 'submitted_at')
    search_fields = ('test__title', 'student__username', 'student__email')
    autocomplete_fields = ('test', 'student')
    date_hierarchy = 'submitted_at'
    readonly_fields = ('started_at', 'submitted_at', 'graded_at', 'attempt_number')
    
    fieldsets = (
        (None, {'fields': ('test', 'student', 'attempt_number')}),
        ('Timing', {'fields': ('started_at', 'submitted_at', 'graded_at')}),
        ('Scores', {'fields': ('score', 'max_score', 'percentage')}),
        ('Status', {'fields': ('is_completed', 'is_graded', 'results_viewed_at')}),
    )
    
    def score_display(self, obj):
        if obj.score is not None and obj.max_score is not None:
            return f"{obj.score}/{obj.max_score}"
        return "-"
    score_display.short_description = 'Score'
    
    def percentage_display(self, obj):
        if obj.percentage is not None:
            return f"{obj.percentage:.1f}%"
        return "-"
    percentage_display.short_description = 'Percentage'
    
    def time_spent_display(self, obj):
        if obj.time_spent_minutes is not None:
            return f"{obj.time_spent_minutes:.1f} min"
        return "-"
    time_spent_display.short_description = 'Time Spent'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'test__course_section__subject_group__course',
            'student'
        )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'attempt', 'question', 'question_type', 'score_display', 'is_correct', 'has_feedback')
    list_filter = ('question__type', 'attempt__test__course_section__subject_group__course', 'attempt__student__role', 'is_correct')
    search_fields = ('attempt__student__username', 'question__text', 'text_answer')
    autocomplete_fields = ('attempt', 'question')
    filter_horizontal = ('selected_options',)
    
    fieldsets = (
        (None, {'fields': ('attempt', 'question')}),
        ('Answer Content', {'fields': ('selected_options', 'text_answer', 'matching_answers_json')}),
        ('Scoring', {'fields': ('score', 'max_score', 'is_correct')}),
        ('Feedback', {'fields': ('teacher_feedback', 'auto_feedback')}),
    )
    
    def question_type(self, obj):
        return obj.question.get_type_display()
    question_type.short_description = 'Type'
    
    def score_display(self, obj):
        if obj.score is not None and obj.max_score is not None:
            return f"{obj.score}/{obj.max_score}"
        return "-"
    score_display.short_description = 'Score'
    
    def has_feedback(self, obj):
        return bool(obj.teacher_feedback or obj.auto_feedback)
    has_feedback.boolean = True
    has_feedback.short_description = 'Has Feedback'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attempt__test__course_section__subject_group__course',
            'attempt__student',
            'question'
        ).prefetch_related('selected_options')
