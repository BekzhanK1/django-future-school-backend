from rest_framework import serializers

from .models import ForumThread, ForumPost, ForumThreadType


class ForumPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_first_name = serializers.CharField(source="author.first_name", read_only=True)
    author_last_name = serializers.CharField(source="author.last_name", read_only=True)
    # Nested replies
    replies = serializers.SerializerMethodField()

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
            "created_at",
            "updated_at",
            "replies",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at", "replies"]

    def get_replies(self, obj):
        """Get nested replies to this post"""
        replies = obj.replies.all()
        return ForumPostSerializer(replies, many=True).data


class ForumThreadSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    posts = ForumPostSerializer(many=True, read_only=True)

    class Meta:
        model = ForumThread
        fields = [
            "id",
            "subject_group",
            "created_by",
            "created_by_username",
            "title",
            "type",
            "is_public",
            "is_resolved",
            "allow_replies",
            "created_at",
            "updated_at",
            "posts",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ForumThreadCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a thread together with the initial post content.
    """

    initial_content = serializers.CharField(write_only=True)

    class Meta:
        model = ForumThread
        fields = ["subject_group", "title", "type", "is_public", "allow_replies", "initial_content"]

    def create(self, validated_data):
        request = self.context["request"]
        initial_content = validated_data.pop("initial_content")

        thread = ForumThread.objects.create(created_by=request.user, **validated_data)

        ForumPost.objects.create(
            thread=thread,
            author=request.user,
            content=initial_content,
            is_answer=False,
        )

        return thread


