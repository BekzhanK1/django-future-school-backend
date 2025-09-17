from django.db import models


class Lesson(models.Model):
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="lessons")
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="lessons")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    topic = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    meeting_link = models.CharField(max_length=1024, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.topic} ({self.starts_at:%Y-%m-%d})"


class Recording(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="recordings")
    storage_provider = models.CharField(max_length=255, null=True, blank=True)
    file_url = models.CharField(max_length=1024)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models

# Create your models here.
