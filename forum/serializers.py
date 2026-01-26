from rest_framework import serializers
from django.db.models import Count

from .models import ForumThread, ForumPost, ForumThreadType, PostReaction


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
            "reactions",
            "user_reactions",
        ]
        read_only_fields = ["id", "author", "created_at",
                            "updated_at", "replies", "reactions", "user_reactions"]

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
    posts = ForumPostSerializer(many=True, read_only=True)

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
        fields = ["subject_group", "title", "type",
                  "is_public", "allow_replies", "initial_content"]

    def create(self, validated_data):
        request = self.context["request"]
        initial_content = validated_data.pop("initial_content")

        thread = ForumThread.objects.create(
            created_by=request.user, **validated_data)

        ForumPost.objects.create(
            thread=thread,
            author=request.user,
            content=initial_content,
            is_answer=False,
        )

        return thread


class PostReactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(
        source="user.username", read_only=True)

    class Meta:
        model = PostReaction
        fields = ["id", "post", "user", "user_username",
                  "reaction_type", "created_at"]
        read_only_fields = ["id", "user", "created_at"]
