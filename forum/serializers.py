import os
from rest_framework import serializers
from django.db.models import Count

from users.models import UserRole

from .models import (
    ForumThread,
    ForumPost,
    ForumThreadType,
    PostReaction,
    ForumPostAttachment,
    FORUM_ATTACHMENT_MAX_FILES,
    FORUM_ATTACHMENT_MAX_SIZE_BYTES,
    FORUM_ATTACHMENT_ALLOWED_EXTENSIONS,
)


def validate_forum_files(files, field_name="files"):
    """Validate list of uploaded files: max count, size, allowed types (no video)."""
    if not files:
        return
    if len(files) > FORUM_ATTACHMENT_MAX_FILES:
        raise serializers.ValidationError(
            {field_name: f"Maximum {FORUM_ATTACHMENT_MAX_FILES} files allowed."}
        )
    for i, f in enumerate(files):
        if f.size > FORUM_ATTACHMENT_MAX_SIZE_BYTES:
            raise serializers.ValidationError(
                {field_name: f"File '{getattr(f, 'name', str(i))}' exceeds 10 MB."}
            )
        ext = os.path.splitext(getattr(f, "name", ""))[1].lstrip(".").lower()
        if ext not in FORUM_ATTACHMENT_ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                {
                    field_name: (
                        f"File type '.{ext}' not allowed. "
                        "Use images (jpg, png, gif, webp, etc.) or documents (pdf, doc, docx, etc.)."
                    )
                }
            )


class ForumPostAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumPostAttachment
        fields = ["id", "file", "position", "created_at"]
        read_only_fields = ["id", "created_at"]


class ForumPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(
        source="author.username", read_only=True)
    author_first_name = serializers.CharField(
        source="author.first_name", read_only=True)
    author_last_name = serializers.CharField(
        source="author.last_name", read_only=True)
    # Nested replies
    replies = serializers.SerializerMethodField()
    # Reactions
    reactions = serializers.SerializerMethodField()
    user_reactions = serializers.SerializerMethodField()
    # Attachments: new multi-file + legacy single file merged for display
    attachments = serializers.SerializerMethodField()
    # Write-only: multiple files when creating a post (multipart: send as "files" multiple times)
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, use_url=False),
        write_only=True,
        required=False,
    )

    class Meta:
        model = ForumPost
        fields = [
            "id",
            "thread",
            "author",
            "author_username",
            "author_first_name",
            "author_last_name",
            "content",
            "is_answer",
            "parent_post",
            "file",
            "files",
            "attachments",
            "created_at",
            "updated_at",
            "replies",
            "reactions",
            "user_reactions",
        ]
        read_only_fields = ["id", "author", "created_at",
                            "updated_at", "replies", "reactions", "user_reactions", "attachments"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST" and request.FILES:
            files = request.FILES.getlist("files") or []
            validate_forum_files(files, field_name="files")
        return attrs

    def create(self, validated_data):
        validated_data.pop("files", None)
        request = self.context.get("request")
        post = ForumPost.objects.create(**validated_data)
        files = []
        if request and request.FILES:
            files = list(request.FILES.getlist("files") or [])
        for idx, f in enumerate(files):
            ForumPostAttachment.objects.create(post=post, file=f, position=idx)
        return post

    def get_attachments(self, obj):
        """All file attachments: legacy single file (if any) + new attachments list."""
        out = []
        if obj.file:
            out.append({
                "id": None,
                "file": obj.file.url if obj.file else None,
                "position": 0,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
                "legacy": True,
            })
        for a in obj.attachments.all().order_by("position", "id"):
            out.append({
                "id": a.id,
                "file": a.file.url if a.file else None,
                "position": a.position,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "legacy": False,
            })
        return out

    def get_replies(self, obj):
        """Get nested replies to this post"""
        replies = obj.replies.all()
        return ForumPostSerializer(replies, many=True, context=self.context).data

    def get_reactions(self, obj):
        """Get reaction counts by type"""
        reactions_qs = obj.reactions.values('reaction_type').annotate(
            count=Count('id')
        )
        return {item['reaction_type']: item['count'] for item in reactions_qs}

    def get_user_reactions(self, obj):
        """Get reactions from current user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        user_reactions = obj.reactions.filter(user=request.user).values_list(
            'reaction_type', flat=True
        )
        return list(user_reactions)


class ForumThreadSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    created_by_first_name = serializers.CharField(
        source="created_by.first_name", read_only=True
    )
    created_by_last_name = serializers.CharField(
        source="created_by.last_name", read_only=True
    )
    subject_group_course_name = serializers.CharField(
        source="subject_group.course.name", read_only=True
    )
    subject_group_classroom_display = serializers.CharField(
        source="subject_group.classroom.__str__", read_only=True
    )
    posts = serializers.SerializerMethodField()

    class Meta:
        model = ForumThread
        fields = [
            "id",
            "subject_group",
            "subject_group_course_name",
            "subject_group_classroom_display",
            "created_by",
            "created_by_username",
            "created_by_first_name",
            "created_by_last_name",
            "participants",
            "title",
            "type",
            "is_public",
            "is_resolved",
            "allow_replies",
            "archived",
            "created_at",
            "updated_at",
            "posts",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_posts(self, obj):
        # Only return top-level posts (no parent) to prevent replies from showing twice
        root_posts = obj.posts.filter(parent_post__isnull=True)
        return ForumPostSerializer(root_posts, many=True, context=self.context).data


class ForumThreadCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a thread together with the initial post content and optional files.
    """

    initial_content = serializers.CharField(write_only=True)
    initial_file = serializers.FileField(write_only=True, required=False)
    # Multiple files for the initial post (question); max 10, images + documents
    initial_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, use_url=False),
        write_only=True,
        required=False,
    )

    class Meta:
        model = ForumThread
        fields = [
            "subject_group", "title", "type",
            "is_public", "allow_replies",
            "initial_content", "initial_file", "initial_files",
            "participants",
        ]
        extra_kwargs = {
            "subject_group": {"required": False, "allow_null": True},
            "participants": {"required": False},
        }

    def validate_initial_files(self, value):
        validate_forum_files(value, field_name="initial_files")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return attrs

        user = request.user
        thread_type = attrs.get("type", ForumThreadType.QUESTION)
        subject_group = attrs.get("subject_group")
        participants = attrs.get("participants") or []

        if user.role == UserRole.PARENT:
            if thread_type == ForumThreadType.DIRECT_MESSAGE:
                if not participants:
                    raise serializers.ValidationError(
                        {"participants": "Для личного сообщения укажите учителя (участника)."}
                    )
                attrs["subject_group"] = None
                return attrs
            if not subject_group:
                raise serializers.ValidationError(
                    {"subject_group": "Укажите предмет/класс для вопроса."}
                )
            child_classroom_ids = user.children.values_list(
                "classroom_users__classroom_id", flat=True
            ).distinct()
            if subject_group.classroom_id not in child_classroom_ids:
                raise serializers.ValidationError(
                    {"subject_group": "Можно создавать вопросы только по предметам класса вашего ребёнка."}
                )
            if thread_type not in (ForumThreadType.QUESTION,):
                raise serializers.ValidationError(
                    {"type": "Родитель может создавать только вопрос (публичный или приватный)."}
                )
            return attrs

        if user.role == UserRole.TEACHER:
            if thread_type == ForumThreadType.DIRECT_MESSAGE:
                if not participants:
                    raise serializers.ValidationError(
                        {"participants": "Для личного сообщения укажите получателя (родителя)."}
                    )
                return attrs
            if thread_type == ForumThreadType.ANNOUNCEMENT_TO_PARENTS:
                if not subject_group:
                    raise serializers.ValidationError(
                        {"subject_group": "Укажите класс/предмет для объявления родителям."}
                    )
                if subject_group.teacher_id != user.id:
                    raise serializers.ValidationError(
                        {"subject_group": "Можно писать родителям только своего класса."}
                    )
                attrs["is_public"] = True
                return attrs
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        initial_content = validated_data.pop("initial_content")
        initial_file = validated_data.pop("initial_file", None)
        initial_files = validated_data.pop("initial_files", [])
        participants = validated_data.pop("participants", [])

        # Multipart: files may come via request.FILES.getlist("initial_files")
        if not initial_files and request.FILES:
            initial_files = request.FILES.getlist("initial_files") or []
        validate_forum_files(initial_files, field_name="initial_files")

        thread = ForumThread.objects.create(
            created_by=request.user, **validated_data)

        if participants:
            thread.participants.set(participants)

        if thread.type == ForumThreadType.DIRECT_MESSAGE and request.user not in thread.participants.all():
            thread.participants.add(request.user)

        first_post = ForumPost.objects.create(
            thread=thread,
            author=request.user,
            content=initial_content,
            file=initial_file,
            is_answer=False,
        )

        for idx, f in enumerate(initial_files):
            ForumPostAttachment.objects.create(
                post=first_post, file=f, position=idx
            )

        if thread.type == ForumThreadType.DIRECT_MESSAGE:
            participants = list(thread.participants.all())
            if participants:
                from users.notifications_helper import notify_direct_message_new_thread
                notify_direct_message_new_thread(thread, participants, request.user)

        return thread


class PostReactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(
        source="user.username", read_only=True)

    class Meta:
        model = PostReaction
        fields = ["id", "post", "user", "user_username",
                  "reaction_type", "created_at"]
        read_only_fields = ["id", "user", "created_at"]
