from rest_framework import serializers

from .models import ForumThread, ForumPost, ForumThreadType


class ForumPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ForumPost
        fields = [
            "id",
            "thread",
            "author",
            "author_username",
            "content",
            "is_answer",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]


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
        fields = ["subject_group", "title", "type", "is_public", "initial_content"]

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


