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
        .prefetch_related("posts__author", "posts__attachments")
        .all()
    )
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["subject_group", "type", "is_public", "is_resolved", "archived"]
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

        # Teacher: threads in their subject groups + direct messages
        if user.role == UserRole.TEACHER:
            return qs.filter(
                models.Q(subject_group__teacher=user) | models.Q(participants=user)
            ).distinct()

        # Student: threads in their classrooms; private only if they created them + direct messages; hide archived announcements; never show "to parents"
        if user.role == UserRole.STUDENT:
            classroom_ids = ClassroomUser.objects.filter(user=user).values_list(
                "classroom_id", flat=True
            )
            return qs.filter(
                (models.Q(subject_group__classroom_id__in=classroom_ids) & 
                 (models.Q(is_public=True) | models.Q(created_by=user))) |
                models.Q(participants=user)
            ).exclude(type="announcement", archived=True).exclude(
                type="announcement_to_parents"
            ).distinct()

        # Parent: public threads + own (private) threads + teacher's "to parents" announcements in child's classes + direct messages; hide student announcements
        if user.role == UserRole.PARENT:
            child_classrooms = user.children.values_list(
                "classroom_users__classroom_id", flat=True
            )
            return qs.filter(
                (
                    models.Q(subject_group__classroom_id__in=child_classrooms)
                    & (
                        models.Q(is_public=True)
                        | models.Q(created_by=user)
                        | models.Q(type="announcement_to_parents")
                    )
                )
                | models.Q(participants=user)
            ).exclude(type="announcement", archived=True).exclude(
                type="announcement_to_parents", archived=True
            ).distinct()

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

    @extend_schema(
        operation_id="forum_threads_archive",
        summary="Archive announcement (hide from students)",
        request=None,
        responses={200: ForumThreadSerializer, 403: OpenApiTypes.OBJECT},
        tags=["Forum"],
    )
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        """Teacher archives an announcement so students no longer see it."""
        thread = self.get_object()
        if not thread.subject_group or thread.subject_group.teacher_id != request.user.id:
            return Response(
                {"error": "Only the subject group teacher can archive this thread"},
                status=status.HTTP_403_FORBIDDEN,
            )
        thread.archived = True
        thread.save(update_fields=["archived"])
        serializer = ForumThreadSerializer(thread, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        operation_id="forum_threads_unarchive",
        summary="Unarchive announcement",
        request=None,
        responses={200: ForumThreadSerializer, 403: OpenApiTypes.OBJECT},
        tags=["Forum"],
    )
    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, pk=None):
        """Teacher makes archived announcement visible to students again."""
        thread = self.get_object()
        if not thread.subject_group or thread.subject_group.teacher_id != request.user.id:
            return Response(
                {"error": "Only the subject group teacher can unarchive this thread"},
                status=status.HTTP_403_FORBIDDEN,
            )
        thread.archived = False
        thread.save(update_fields=["archived"])
        serializer = ForumThreadSerializer(thread, context={"request": request})
        return Response(serializer.data)


class ForumPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing posts inside threads (questions, answers, comments).
    """

    queryset = ForumPost.objects.select_related(
        "thread", "author", "thread__subject_group", "thread__subject_group__teacher", "thread__created_by"
    ).prefetch_related("attachments").all()
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

        # Teacher: posts in threads from their subject groups + direct messages
        if user.role == UserRole.TEACHER:
            return qs.filter(
                models.Q(thread__subject_group__teacher=user) | models.Q(thread__participants=user)
            ).distinct()

        # Student: hide archived announcements and "to parents" threads
        if user.role == UserRole.STUDENT:
            classroom_ids = ClassroomUser.objects.filter(user=user).values_list(
                "classroom_id", flat=True
            )
            return qs.filter(
                (models.Q(thread__subject_group__classroom_id__in=classroom_ids) & 
                 (models.Q(thread__is_public=True) | models.Q(thread__created_by=user))) |
                models.Q(thread__participants=user)
            ).exclude(thread__type="announcement", thread__archived=True).exclude(
                thread__type="announcement_to_parents"
            ).distinct()

        # Parent: include "to parents" announcements in their children's classes
        if user.role == UserRole.PARENT:
            child_classrooms = user.children.values_list(
                "classroom_users__classroom_id", flat=True
            )
            return qs.filter(
                (
                    models.Q(thread__subject_group__classroom_id__in=child_classrooms)
                    & (
                        models.Q(thread__is_public=True)
                        | models.Q(thread__created_by=user)
                        | models.Q(thread__type="announcement_to_parents")
                    )
                )
                | models.Q(thread__participants=user)
            ).exclude(thread__type="announcement", thread__archived=True).exclude(
                thread__type="announcement_to_parents", thread__archived=True
            ).distinct()

        # Other roles: no access
        return qs.none()

    def perform_create(self, serializer):
        from rest_framework import serializers as drf_serializers

        thread_id = self.request.data.get('thread')
        if thread_id:
            try:
                thread_obj = ForumThread.objects.get(id=thread_id)
                if not thread_obj.allow_replies:
                    raise drf_serializers.ValidationError("Replies are not allowed on this thread")
            except ForumThread.DoesNotExist:
                pass
        post = serializer.save(author=self.request.user)
        # Notifications for replies are sent via users.signals_notifications.forum_post_created

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


