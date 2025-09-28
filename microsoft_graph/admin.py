from django.contrib import admin
from .models import MicrosoftGraphConfig, SchoolMicrosoftAccount, OnlineMeeting


@admin.register(MicrosoftGraphConfig)
class MicrosoftGraphConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant_id', 'client_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['tenant_id', 'client_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SchoolMicrosoftAccount)
class SchoolMicrosoftAccountAdmin(admin.ModelAdmin):
    list_display = ['school', 'microsoft_email', 'is_active', 'is_expired', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at', 'school']
    search_fields = ['school__name', 'microsoft_email']
    readonly_fields = ['created_at', 'updated_at', 'is_expired']
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Token Expired'


@admin.register(OnlineMeeting)
class OnlineMeetingAdmin(admin.ModelAdmin):
    list_display = ['meeting_title', 'subject_group', 'created_by', 'start_time', 'is_active']
    list_filter = ['is_active', 'start_time', 'created_at', 'school_account__school']
    search_fields = ['meeting_title', 'meeting_description', 'created_by__username']
    readonly_fields = ['microsoft_meeting_id', 'join_url', 'meeting_url', 'created_at', 'updated_at']
    date_hierarchy = 'start_time'