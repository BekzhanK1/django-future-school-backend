from rest_framework import serializers
from .models_notifications import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    triggered_by_username = serializers.CharField(
        source="triggered_by.username", read_only=True)
    triggered_by_first_name = serializers.CharField(
        source="triggered_by.first_name", read_only=True)
    triggered_by_last_name = serializers.CharField(
        source="triggered_by.last_name", read_only=True)
    related_forum_thread_subject_group = serializers.SerializerMethodField()
    related_forum_thread_subject_name = serializers.SerializerMethodField()
    related_forum_thread_classroom_name = serializers.SerializerMethodField()
    related_assignment_subject_name = serializers.SerializerMethodField()
    related_assignment_classroom_name = serializers.SerializerMethodField()
    related_test_subject_name = serializers.SerializerMethodField()
    related_test_classroom_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'title',
            'message',
            'is_read',
            'read_at',
            'created_at',
            'triggered_by',
            'triggered_by_username',
            'triggered_by_first_name',
            'triggered_by_last_name',
            'related_assignment',
            'related_assignment_subject_name',
            'related_assignment_classroom_name',
            'related_test',
            'related_test_subject_name',
            'related_test_classroom_name',
            'related_forum_thread',
            'related_forum_thread_subject_group',
            'related_forum_thread_subject_name',
            'related_forum_thread_classroom_name',
            'related_forum_post',
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

    def get_related_forum_thread_subject_group(self, obj):
        """Get subject_group ID from forum thread"""
        if obj.related_forum_thread:
            return obj.related_forum_thread.subject_group_id
        return None

    def get_related_forum_thread_subject_name(self, obj):
        """Get subject name from forum thread"""
        if obj.related_forum_thread and obj.related_forum_thread.subject_group:
            return obj.related_forum_thread.subject_group.course.name
        return None

    def get_related_forum_thread_classroom_name(self, obj):
        """Get classroom name from forum thread"""
        if obj.related_forum_thread and obj.related_forum_thread.subject_group:
            return str(obj.related_forum_thread.subject_group.classroom)
        return None

    def get_related_assignment_subject_name(self, obj):
        """Get subject name from assignment"""
        if obj.related_assignment and obj.related_assignment.course_section:
            subject_group = obj.related_assignment.course_section.subject_group
            if subject_group:
                return subject_group.course.name
        return None

    def get_related_assignment_classroom_name(self, obj):
        """Get classroom name from assignment"""
        if obj.related_assignment and obj.related_assignment.course_section:
            subject_group = obj.related_assignment.course_section.subject_group
            if subject_group:
                return str(subject_group.classroom)
        return None

    def get_related_test_subject_name(self, obj):
        """Get subject name from test"""
        if obj.related_test and obj.related_test.course_section:
            subject_group = obj.related_test.course_section.subject_group
            if subject_group:
                return subject_group.course.name
        return None

    def get_related_test_classroom_name(self, obj):
        """Get classroom name from test"""
        if obj.related_test and obj.related_test.course_section:
            subject_group = obj.related_test.course_section.subject_group
            if subject_group:
                return str(subject_group.classroom)
        return None
