from django.db import models


class Test(models.Model):
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="tests")
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="tests")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    reveal_results_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.title


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=64)
    text = models.TextField()
    options_json = models.TextField(null=True, blank=True)
    correct_json = models.TextField(null=True, blank=True)
    points = models.PositiveIntegerField(default=1)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]


class Attempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="test_attempts")
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    max_score = models.IntegerField(null=True, blank=True)


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_json = models.TextField(null=True, blank=True)
    text_answer = models.TextField(null=True, blank=True)
    match_json = models.TextField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)

from django.db import models

# Create your models here.
