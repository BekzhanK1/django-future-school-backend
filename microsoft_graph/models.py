"""
Microsoft Graph API Integration

This module handles integration with Microsoft Graph API for:
- School-level Microsoft account authentication (by superadmin)
- Online meeting creation by teachers
- Token management per school
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class MicrosoftGraphConfig(models.Model):
    """Configuration for Microsoft Graph API integration"""
    tenant_id = models.CharField(max_length=255, null=True, blank=True, help_text="Leave empty for multi-tenant (common) apps")
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Microsoft Graph Configuration"
        verbose_name_plural = "Microsoft Graph Configurations"
    
    def __str__(self):
        tenant_display = self.tenant_id or "common (multi-tenant)"
        return f"Microsoft Graph Config - {tenant_display}"


class SchoolMicrosoftAccount(models.Model):
    """Microsoft account tokens for each school (signed in by superadmin)"""
    school = models.OneToOneField(
        "schools.School", 
        on_delete=models.CASCADE, 
        related_name="microsoft_account"
    )
    microsoft_email = models.EmailField(help_text="Microsoft account email used for this school")
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_type = models.CharField(max_length=50, default="Bearer")
    expires_at = models.DateTimeField()
    scope = models.TextField(help_text="Comma-separated list of granted scopes")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "users.User", 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_microsoft_accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "School Microsoft Account"
        verbose_name_plural = "School Microsoft Accounts"
    
    def __str__(self):
        return f"Microsoft Account for {self.school.name} ({self.microsoft_email})"
    
    @property
    def is_expired(self):
        """Check if the token is expired"""
        return timezone.now() >= self.expires_at


class OnlineMeeting(models.Model):
    """Online meetings created by teachers using school's Microsoft account"""
    school_account = models.ForeignKey(
        SchoolMicrosoftAccount, 
        on_delete=models.CASCADE, 
        related_name="online_meetings"
    )
    created_by = models.ForeignKey(
        "users.User", 
        on_delete=models.CASCADE, 
        related_name="created_online_meetings"
    )
    subject_group = models.OneToOneField(
        "courses.SubjectGroup", 
        on_delete=models.CASCADE, 
        related_name="online_meeting"
    )
    
    # Meeting details
    meeting_title = models.CharField(max_length=255)
    meeting_description = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # Microsoft Graph data
    microsoft_meeting_id = models.CharField(max_length=255, unique=True)
    join_url = models.URLField()
    meeting_url = models.URLField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Online Meeting"
        verbose_name_plural = "Online Meetings"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.meeting_title} - {self.subject_group} ({self.start_time})"