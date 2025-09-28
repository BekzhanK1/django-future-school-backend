"""
Microsoft Graph API Serializers

Serializers for Microsoft Graph API integration endpoints.
"""

from django.utils import timezone
from rest_framework import serializers
from .models import SchoolMicrosoftAccount, OnlineMeeting, MicrosoftGraphConfig


class MicrosoftGraphConfigSerializer(serializers.ModelSerializer):
    """Serializer for Microsoft Graph configuration"""
    tenant_display = serializers.CharField(source='__str__', read_only=True)
    
    class Meta:
        model = MicrosoftGraphConfig
        fields = ['id', 'tenant_id', 'client_id', 'is_active', 'tenant_display', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SchoolMicrosoftAccountSerializer(serializers.ModelSerializer):
    """Serializer for school Microsoft accounts"""
    school = serializers.StringRelatedField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SchoolMicrosoftAccount
        fields = [
            'id', 'school', 'microsoft_email', 'token_type', 'expires_at', 
            'scope', 'is_active', 'is_expired', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'school', 'created_by', 'created_at', 'updated_at']


class OnlineMeetingSerializer(serializers.ModelSerializer):
    """Serializer for online meetings"""
    created_by = serializers.StringRelatedField(read_only=True)
    subject_group = serializers.StringRelatedField(read_only=True)
    school_account = serializers.StringRelatedField(read_only=True)
    subject_group_external_id = serializers.CharField(source='subject_group.external_id', read_only=True)
    
    class Meta:
        model = OnlineMeeting
        fields = [
            'id', 'school_account', 'created_by', 'subject_group', 'subject_group_external_id',
            'meeting_title', 'meeting_description', 'start_time', 'end_time', 'microsoft_meeting_id',
            'join_url', 'meeting_url', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'school_account', 'created_by', 'microsoft_meeting_id', 'created_at', 'updated_at']

class ShortOnlineMeetingSerializer(serializers.ModelSerializer):
    """Short serializer for online meetings: id, subject_group, join_url"""
    subject_group = serializers.StringRelatedField(read_only=True)
    url = serializers.URLField(source='join_url', read_only=True)

    class Meta:
        model = OnlineMeeting
        fields = ['id', 'subject_group', 'url']
        read_only_fields = ['id', 'subject_group', 'url']


# Request/Response serializers for API endpoints

class MicrosoftAuthRequestSerializer(serializers.Serializer):
    """Serializer for Microsoft authentication request"""
    redirect_uri = serializers.URLField(
        help_text="Redirect URI after Microsoft authentication"
    )
    scopes = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of requested Microsoft Graph scopes"
    )


class MicrosoftAuthResponseSerializer(serializers.Serializer):
    """Serializer for Microsoft authentication response"""
    auth_url = serializers.URLField(
        help_text="Microsoft Graph authorization URL"
    )
    state = serializers.CharField(
        help_text="State parameter for CSRF protection"
    )


class MicrosoftTokenExchangeSerializer(serializers.Serializer):
    """Serializer for token exchange request"""
    code = serializers.CharField(
        help_text="Authorization code from Microsoft"
    )
    redirect_uri = serializers.URLField(
        help_text="Redirect URI used in authorization"
    )
    school_id = serializers.IntegerField(
        help_text="ID of the school to associate with this Microsoft account"
    )


class CreateOnlineMeetingByExternalIdSerializer(serializers.Serializer):
    """Serializer for creating online meetings using external_id"""
    subject_group = serializers.IntegerField(
        help_text="ID of the subject group for the meeting"
    )
    meeting_description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description of the meeting"
    )
    update = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to update the meeting if it already exists"
    )
    

class CreateOnlineMeetingSerializer(serializers.Serializer):
    """Serializer for creating online meetings"""
    subject_group_id = serializers.IntegerField(
        help_text="ID of the subject group for the meeting"
    )
    meeting_title = serializers.CharField(
        max_length=255,
        help_text="Title of the meeting"
    )
    meeting_description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description of the meeting"
    )
    start_time = serializers.DateTimeField(
        help_text="Start time of the meeting"
    )
    end_time = serializers.DateTimeField(
        help_text="End time of the meeting"
    )
    
    def validate(self, data):
        """Validate meeting times"""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        
        if data['start_time'] <= timezone.now():
            raise serializers.ValidationError("Start time must be in the future")
        
        return data
