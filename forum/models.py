from django.conf import settings
from django.db import models

from courses.models import SubjectGroup


class ForumThreadType(models.TextChoices):
    QUESTION = "question", "Question"
    ANNOUNCEMENT = "announcement", "Announcement"


class ReactionType(models.TextChoices):
    THUMBS_UP = "👍", "Thumbs Up"
    HEART = "❤️", "Heart"
    LAUGHING = "😂", "Laughing"
    SURPRISED = "😮", "Surprised"
    SAD = "😢", "Sad"
    FIRE = "🔥", "Fire"


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
    # For announcements: whether replies are allowed
    allow_replies = models.BooleanField(
        default=True, help_text="Whether students can reply to this thread")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.subject_group} / {self.title}"


class ForumPost(models.Model):
    """
    Posts inside a thread (questions, answers, comments).
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
    # For nested replies (reply-to functionality)
    parent_post = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        help_text="Parent post if this is a reply"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Post in thread {self.thread_id} by {self.author_id}"


class PostReaction(models.Model):
    """
    Emoji reactions on forum posts (👍 ❤️ 😂 😮 😢 🔥).
    """
    post = models.ForeignKey(
        ForumPost, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_post_reactions",
    )
    reaction_type = models.CharField(
        max_length=2,  # emoji is typically 2 chars
        choices=ReactionType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("post", "user", "reaction_type")

    def __str__(self) -> str:
        return f"{self.user.username} reacted {self.reaction_type} on post {self.post_id}"
