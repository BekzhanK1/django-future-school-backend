from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    """Types of notifications in the system"""
    # Assignments
    NEW_ASSIGNMENT = "new_assignment", "New Assignment"
    ASSIGNMENT_GRADED = "assignment_graded", "Assignment Graded"

    # Tests
    NEW_TEST = "new_test", "New Test"
    TEST_AVAILABLE = "test_available", "Test Available"
    TEST_GRADED = "test_graded", "Test Graded"

    # Forum
    FORUM_QUESTION = "forum_question", "Forum Question"
    FORUM_REPLY = "forum_reply", "Forum Reply"
    FORUM_MENTION = "forum_mention", "Forum Mention"
    FORUM_RESOLVED = "forum_resolved", "Forum Resolved"

    # Other
    OTHER = "other", "Other"


class Notification(models.Model):
    """
    Notification for users about events in the system.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.OTHER
    )

    # The title to display
    title = models.CharField(max_length=255)

    # The description/message
    message = models.TextField(blank=True)

    # Link to related object (assignment, test, forum post, etc)
    # Store as JSON or just keep model references below
    related_assignment = models.ForeignKey(
        'learning.Assignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )

    related_test = models.ForeignKey(
        'assessments.Test',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )

    related_forum_thread = models.ForeignKey(
        'forum.ForumThread',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )

    related_forum_post = models.ForeignKey(
        'forum.ForumPost',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )

    # Who triggered the notification
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_triggered"
    )

    # Mark as read
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.type} - {self.title}"

    def mark_as_read(self) -> None:
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
