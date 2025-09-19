from django.db import models


class ResourceType(models.TextChoices):
    FILE = "file", "File"
    LINK = "link", "Link"
    DIRECTORY = "directory", "Directory"
    TEXT = "text", "Text"


class Resource(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="resources")
    parent_resource = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    type = models.CharField(max_length=32, choices=ResourceType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    url = models.CharField(max_length=1024, null=True, blank=True)
    file = models.FileField(upload_to='resources/', null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.title


class Assignment(models.Model):
    course_section = models.ForeignKey("courses.CourseSection", on_delete=models.CASCADE, related_name="assignments")
    teacher = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    due_at = models.DateTimeField()
    max_grade = models.PositiveIntegerField(default=100, help_text="Maximum possible grade for this assignment")

    def __str__(self) -> str:
        return self.title


class AssignmentAttachmentType(models.TextChoices):
    TEXT = "text", "Text"
    FILE = "file", "File"
    LINK = "link", "Link"


class AssignmentAttachment(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="attachments")
    type = models.CharField(max_length=32, choices=AssignmentAttachmentType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)  # For text content or file URLs
    file_url = models.URLField(null=True, blank=True)  # For file URLs
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self) -> str:
        return f"{self.assignment.title} - {self.title}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField(null=True, blank=True)  # Keep for backward compatibility
    file_url = models.CharField(max_length=1024, null=True, blank=True)  # Keep for backward compatibility

    def __str__(self) -> str:
        return f"Submission {self.id}"


class SubmissionAttachmentType(models.TextChoices):
    TEXT = "text", "Text"
    FILE = "file", "File"
    LINK = "link", "Link"


class SubmissionAttachment(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="attachments")
    type = models.CharField(max_length=32, choices=SubmissionAttachmentType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)  # For text content or file URLs
    file_url = models.URLField(null=True, blank=True)  # For file URLs
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self) -> str:
        return f"{self.submission} - {self.title}"


class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="grade")
    graded_by = models.ForeignKey("users.User", on_delete=models.CASCADE)
    grade_value = models.PositiveIntegerField()
    feedback = models.TextField(null=True, blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

from django.db import models

# Create your models here.
