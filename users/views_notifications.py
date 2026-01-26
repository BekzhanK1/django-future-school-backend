from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone

from .models_notifications import Notification
from .serializers_notifications import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Only return notifications for the current user"""
        return Notification.objects.filter(
            user=self.request.user
        ).select_related(
            'triggered_by',
            'related_forum_thread__subject_group__course',
            'related_forum_thread__subject_group__classroom',
            'related_assignment__course_section__subject_group__course',
            'related_assignment__course_section__subject_group__classroom',
            'related_test__course_section__subject_group__course',
            'related_test__course_section__subject_group__classroom',
        )

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get all unread notifications"""
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).select_related(
            'triggered_by',
            'related_forum_thread__subject_group__course',
            'related_forum_thread__subject_group__classroom',
            'related_assignment__course_section__subject_group__course',
            'related_assignment__course_section__subject_group__classroom',
            'related_test__course_section__subject_group__course',
            'related_test__course_section__subject_group__classroom',
        ).order_by('-created_at')
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'All notifications marked as read'})

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Delete all notifications for the user"""
        Notification.objects.filter(user=request.user).delete()
        return Response({'status': 'All notifications deleted'})
