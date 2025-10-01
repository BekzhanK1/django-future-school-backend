from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class QuestionType(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    CHOOSE_ALL = "choose_all", "Choose All That Apply"
    OPEN_QUESTION = "open_question", "Open Question"
    MATCHING = "matching", "Matching Items"


class Test(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="tests")
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="tests")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    reveal_results_at = models.DateTimeField(null=True, blank=True)
    
    # Time management
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Time limit in minutes (optional)")
    allow_multiple_attempts = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum number of attempts (if multiple attempts allowed)")
    
    # Result visibility
    show_correct_answers = models.BooleanField(default=True)
    show_feedback = models.BooleanField(default=True)
    show_score_immediately = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
    
    @property
    def total_points(self):
        return sum(question.points for question in self.questions.all())


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=32, choices=QuestionType.choices)
    text = models.TextField()
    points = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    position = models.PositiveIntegerField(default=0)
    
    # For open questions
    correct_answer_text = models.TextField(null=True, blank=True, help_text="Expected answer for open questions")
    sample_answer = models.TextField(null=True, blank=True, help_text="Sample answer for reference")
    
    # For matching questions
    matching_pairs_json = models.JSONField(null=True, blank=True, help_text="JSON array of matching pairs")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.test.title} - Q{self.position}: {self.text[:50]}..."


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        content = self.text or f"Image: {self.image_url}"
        return f"{content} {'✓' if self.is_correct else ''}"


class Attempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="test_attempts")
    attempt_number = models.PositiveIntegerField(default=1)
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # Scores
    score = models.IntegerField(null=True, blank=True)
    max_score = models.IntegerField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Result viewing
    results_viewed_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_completed = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['test', 'student', 'attempt_number']

    def __str__(self) -> str:
        return f"{self.student.username} - {self.test.title} (Attempt {self.attempt_number})"
    
    @property
    def can_view_results(self):
        if not self.is_completed:
            return False
        if not self.test.reveal_results_at:
            return True
        from django.utils import timezone
        return timezone.now() >= self.test.reveal_results_at
    
    @property
    def time_spent_minutes(self):
        if not self.submitted_at:
            return None
        delta = self.submitted_at - self.started_at
        return delta.total_seconds() / 60


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For multiple choice and choose all
    selected_options = models.ManyToManyField(Option, blank=True, related_name="selected_in_answers")
    
    # For open questions
    text_answer = models.TextField(null=True, blank=True)
    
    # For matching questions
    matching_answers_json = models.JSONField(null=True, blank=True, help_text="JSON array of matching answers")
    
    # Scoring
    score = models.FloatField(null=True, blank=True)
    max_score = models.FloatField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    
    # Feedback
    teacher_feedback = models.TextField(null=True, blank=True)
    auto_feedback = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Answer for {self.question} by {self.attempt.student.username}"
    
    def calculate_score(self):
        """Calculate the score for this answer based on question type"""
        if self.question.type == QuestionType.MULTIPLE_CHOICE:
            correct_options = self.question.options.filter(is_correct=True)
            selected_correct = self.selected_options.filter(is_correct=True).count()
            if selected_correct == correct_options.count() and self.selected_options.count() == 1:
                return self.question.points
            return 0
            
        elif self.question.type == QuestionType.CHOOSE_ALL:
            correct_options = self.question.options.filter(is_correct=True)
            selected_correct = self.selected_options.filter(is_correct=True).count()
            selected_incorrect = self.selected_options.filter(is_correct=False).count()
            
            if selected_incorrect > 0:
                return 0  # Any incorrect selection = 0 points
            
            # Partial credit for partially correct answers
            if selected_correct > 0:
                return (selected_correct / correct_options.count()) * self.question.points
            return 0
            
        elif self.question.type == QuestionType.OPEN_QUESTION:
            # This would need manual grading or AI-based grading
            return None  # Requires manual review
            
        elif self.question.type == QuestionType.MATCHING:
            if not self.matching_answers_json:
                return 0
                
            correct_pairs = self.question.matching_pairs_json or []
            correct_count = 0
            
            for answer_pair in self.matching_answers_json:
                if answer_pair in correct_pairs:
                    correct_count += 1
            
            if correct_pairs:
                return (correct_count / len(correct_pairs)) * self.question.points
            return 0
        
        return 0

