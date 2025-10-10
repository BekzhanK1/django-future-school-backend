from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from difflib import SequenceMatcher


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
    reveal_results_at = models.DateTimeField(null=True, blank=True)
    
    # Time management
    start_date = models.DateTimeField(null=True, blank=True, help_text="Test start date and time")
    end_date = models.DateTimeField(null=True, blank=True, help_text="Test end date and time")
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
    key_words = models.TextField(null=True, blank=True, help_text="Comma-separated keywords for automatic grading of open questions")
    
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
            # Check if key_words are provided for automatic grading
            if self.question.key_words and self.text_answer:
                # Split keywords by comma and strip whitespace
                keywords = [kw.strip().lower() for kw in self.question.key_words.split(',') if kw.strip()]
                answer_text = self.text_answer.lower()
                
                # Check if at least one keyword is present in the answer
                if any(keyword in answer_text for keyword in keywords):
                    return self.question.points
                else:
                    return 0
            
            # If no key_words provided, try exact/fuzzy matching with correct_answer_text
            if self.question.correct_answer_text:
                # If student didn't provide an answer, it's incorrect
                if not self.text_answer:
                    return 0
                # Normalize: lowercase, strip, collapse internal whitespace
                expected = " ".join(self.question.correct_answer_text.strip().lower().split())
                given = " ".join(self.text_answer.strip().lower().split())
                # Exact match
                if expected == given:
                    return self.question.points
                # Fuzzy match using similarity ratio
                similarity = SequenceMatcher(None, expected, given).ratio()
                # Threshold for "almost correct" answers
                if similarity >= 0.85:
                    return self.question.points
                return 0
            
            # If neither keywords nor correct_answer_text are provided, requires manual grading
            return None
            
        elif self.question.type == QuestionType.MATCHING:
            if not self.matching_answers_json:
                return 0
                
            correct_pairs = self.question.matching_pairs_json or []
            if not correct_pairs:
                return 0
            
            # Create a normalized set of correct pairs for comparison (case-insensitive)
            correct_pairs_set = set()
            for pair in correct_pairs:
                if isinstance(pair, dict) and 'left' in pair and 'right' in pair:
                    # Normalize by stripping whitespace and converting to lowercase
                    left = str(pair['left']).strip().lower()
                    right = str(pair['right']).strip().lower()
                    correct_pairs_set.add((left, right))
            
            # Process student answers
            student_pairs_set = set()
            valid_answers = []
            
            for answer_pair in self.matching_answers_json:
                if isinstance(answer_pair, dict) and 'left' in answer_pair and 'right' in answer_pair:
                    # Normalize student answer (case-insensitive)
                    left = str(answer_pair['left']).strip().lower()
                    right = str(answer_pair['right']).strip().lower()
                    
                    # Skip duplicates
                    if (left, right) not in student_pairs_set:
                        student_pairs_set.add((left, right))
                        valid_answers.append((left, right))
            
            # Count correct matches
            correct_count = 0
            for student_pair in valid_answers:
                if student_pair in correct_pairs_set:
                    correct_count += 1
            
            # Check if student provided incorrect pairs (penalty)
            incorrect_count = len(valid_answers) - correct_count
            
            # Calculate score with penalty for incorrect pairs
            if len(correct_pairs_set) > 0:
                # Full credit only if all correct pairs are matched and no incorrect pairs
                if correct_count == len(correct_pairs_set) and incorrect_count == 0:
                    return self.question.points
                # Partial credit: proportion of correct pairs minus penalty for incorrect
                else:
                    score_ratio = (correct_count / len(correct_pairs_set)) - (incorrect_count * 0.25 / len(correct_pairs_set))
                    # Ensure score doesn't go below 0
                    score_ratio = max(0, score_ratio)
                    return score_ratio * self.question.points
            return 0
        
        return 0

