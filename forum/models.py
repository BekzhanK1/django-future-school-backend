from django.conf import settings
from django.db import models

from courses.models import SubjectGroup


class ForumThreadType(models.TextChoices):
    QUESTION = "question", "Question"
    ANNOUNCEMENT = "announcement", "Announcement"  # to students
    ANNOUNCEMENT_TO_PARENTS = "announcement_to_parents", "Announcement to parents"
    DIRECT_MESSAGE = "direct_message", "Direct Message"


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
        SubjectGroup, on_delete=models.CASCADE, related_name="forum_threads",
        null=True, blank=True,
    )
    # participants for direct messages
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="direct_threads", blank=True
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
    # When True, announcement is hidden from students (teacher archived old announcement)
    archived = models.BooleanField(
        default=False, help_text="Archived announcements are hidden from students")
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
    # Legacy single file (kept for backward compatibility; new uploads use attachments)
    file = models.FileField(upload_to='forum_posts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Post in thread {self.thread_id} by {self.author_id}"


# Max 10 attachments per post; allowed: images + documents (no video)
FORUM_ATTACHMENT_MAX_FILES = 10
FORUM_ATTACHMENT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file
FORUM_ATTACHMENT_ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'odt', 'ods', 'csv', 'ppt', 'pptx',
}


class ForumPostAttachment(models.Model):
    """File attached to a forum post (image or document; max 10 per post)."""

    post = models.ForeignKey(
        ForumPost, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to='forum_posts/attachments/%Y/%m/')
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"Attachment {self.id} for post {self.post_id}"


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
