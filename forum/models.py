from django.conf import settings
from django.db import models

from courses.models import SubjectGroup


class ForumThreadType(models.TextChoices):
    QUESTION = "question", "Question"
    ANNOUNCEMENT = "announcement", "Announcement"


class ForumThread(models.Model):
    """
    Q/A + announcements per SubjectGroup (Piazza-style).
    """

    subject_group = models.ForeignKey(
        SubjectGroup, on_delete=models.CASCADE, related_name="forum_threads"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_threads",
    )
    title = models.CharField(max_length=255)
    type = models.CharField(
        max_length=32,
        choices=ForumThreadType.choices,
        default=ForumThreadType.QUESTION,
    )
    # If False → private: visible only to author student + subject_group teacher + admins
    is_public = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.subject_group} / {self.title}"


class ForumPost(models.Model):
    """
    Posts inside a thread (question text, answers, follow-ups).
    """

    thread = models.ForeignKey(
        ForumThread, on_delete=models.CASCADE, related_name="posts"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_posts",
    )
    content = models.TextField()
    # For marking an official teacher answer (can be used in UI)
    is_answer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Post in thread {self.thread_id} by {self.author_id}"


