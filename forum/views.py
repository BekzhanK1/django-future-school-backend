from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from learning.role_permissions import RoleBasedPermission
from schools.models import ClassroomUser
from users.models import UserRole

from .models import ForumThread, ForumPost, PostReaction
from .serializers import (
    ForumThreadSerializer,
    ForumThreadCreateSerializer,
    ForumPostSerializer,
    PostReactionSerializer,
)


class ForumThreadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Q/A threads per SubjectGroup.
    """

    queryset = (
        ForumThread.objects.select_related(
            "subject_group__classroom",
            "subject_group__course",
            "subject_group__teacher",
            "created_by",
        )
        .prefetch_related("posts__author")
        .all()
    )
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["subject_group", "type", "is_public", "is_resolved"]
    search_fields = ["title", "posts__content"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return ForumThreadCreateSerializer
        return ForumThreadSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Superadmin / schooladmin: full access (object-level filtered by RoleBasedPermission if needed)
        if user.role in [UserRole.SUPERADMIN, UserRole.SCHOOLADMIN]:
            return qs

        # Teacher: threads in their subject groups
        if user.role == UserRole.TEACHER:
            return qs.filter(subject_group__teacher=user)

        # Student: threads in their classrooms; private only if they created them
        if user.role == UserRole.STUDENT:
            classroom_ids = ClassroomUser.objects.filter(user=user).values_list(
                "classroom_id", flat=True
            )
            return qs.filter(
                subject_group__classroom_id__in=classroom_ids
            ).filter(
                models.Q(is_public=True) | models.Q(created_by=user)
            )

        # Parent (spectator): only public threads in subject groups where their children study
        if user.role == UserRole.PARENT:
            child_classrooms = user.children.values_list(
                "classroom_users__classroom_id", flat=True
            )
            return qs.filter(
                subject_group__classroom_id__in=child_classrooms,
                is_public=True,
            )

        # Other roles: no access
        return qs.none()

    def perform_create(self, serializer):
        serializer.save()  # created_by is set in serializer.create

    @extend_schema(
        operation_id="forum_threads_mark_resolved",
        summary="Mark thread as resolved",
        request=None,
        responses={200: ForumThreadSerializer, 403: OpenApiTypes.OBJECT},
        tags=["Forum"],
    )
    @action(detail=True, methods=["post"], url_path="mark-resolved")
    def mark_resolved(self, request, pk=None):
        """Teacher marks question as resolved."""
        thread = self.get_object()
        subject_group = thread.subject_group

        if request.user != subject_group.teacher:
            return Response(
                {"error": "Only the subject group teacher can mark as resolved"},
                status=status.HTTP_403_FORBIDDEN,
            )

        thread.is_resolved = True
        thread.save(update_fields=["is_resolved"])

        serializer = ForumThreadSerializer(thread, context={"request": request})
        return Response(serializer.data)


class ForumPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing posts inside threads (questions, answers, comments).
    """

    queryset = ForumPost.objects.select_related(
        "thread", "author", "thread__subject_group", "thread__subject_group__teacher", "thread__created_by"
    ).all()
    serializer_class = ForumPostSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["thread"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Superadmin / schooladmin: full access
        if user.role in [UserRole.SUPERADMIN, UserRole.SCHOOLADMIN]:
            return qs

        # Teacher: posts in threads from their subject groups
        if user.role == UserRole.TEACHER:
            return qs.filter(thread__subject_group__teacher=user)

        # Student: posts in threads they can access (public or created by them)
        if user.role == UserRole.STUDENT:
            classroom_ids = ClassroomUser.objects.filter(user=user).values_list(
                "classroom_id", flat=True
            )
            return qs.filter(
                thread__subject_group__classroom_id__in=classroom_ids
            ).filter(
                models.Q(thread__is_public=True) | models.Q(thread__created_by=user)
            )

        # Parent: only posts in public threads from their children's classrooms
        if user.role == UserRole.PARENT:
            child_classrooms = user.children.values_list(
                "classroom_users__classroom_id", flat=True
            )
            return qs.filter(
                thread__subject_group__classroom_id__in=child_classrooms,
                thread__is_public=True,
            )

        # Other roles: no access
        return qs.none()

    def perform_create(self, serializer):
        # Check if replies are allowed in this thread
        from rest_framework import serializers as drf_serializers
        thread_id = self.request.data.get('thread')
        if thread_id:
            try:
                thread = ForumThread.objects.get(id=thread_id)
                if not thread.allow_replies:
                    raise drf_serializers.ValidationError("Replies are not allowed on this thread")
            except ForumThread.DoesNotExist:
                pass
        
        serializer.save(author=self.request.user)

    @extend_schema(
        operation_id="forum_posts_add_reaction",
        summary="Add or toggle emoji reaction on a post",
        request=PostReactionSerializer,
        responses={200: PostReactionSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Forum"],
    )
    @action(detail=True, methods=["post"], url_path="react")
    def react(self, request, pk=None):
        """Add or toggle an emoji reaction on a post."""
        post = self.get_object()
        reaction_type = request.data.get("reaction_type")

        if not reaction_type:
            return Response(
                {"error": "reaction_type is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Toggle: if user already reacted with this emoji, remove it; otherwise add it
        reaction, created = PostReaction.objects.get_or_create(
            post=post, user=request.user, reaction_type=reaction_type
        )

        if not created:
            # User already reacted, so remove it (toggle)
            reaction.delete()
            return Response(
                {"message": "Reaction removed"},
                status=status.HTTP_200_OK,
            )

        serializer = PostReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="forum_posts_remove_reaction",
        summary="Remove emoji reaction from a post",
        request=None,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Forum"],
    )
    @action(detail=True, methods=["delete"], url_path=r"react/(?P<reaction_type>[^/]+)")
    def remove_reaction(self, request, pk=None, reaction_type=None):
        """Remove a specific emoji reaction from a post."""
        post = self.get_object()

        try:
            reaction = PostReaction.objects.get(
                post=post, user=request.user, reaction_type=reaction_type
            )
            reaction.delete()
            return Response(
                {"message": "Reaction removed"},
                status=status.HTTP_200_OK,
            )
        except PostReaction.DoesNotExist:
            return Response(
                {"error": "Reaction not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


