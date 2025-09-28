"""
Microsoft Graph API Service

This module provides a service class for interacting with Microsoft Graph API.
Handles authentication, token management, and API calls.
"""

import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from typing import Dict, List, Optional, Any
from .models import SchoolMicrosoftAccount, MicrosoftGraphConfig

logger = logging.getLogger(__name__)


class MicrosoftGraphService:
    """Service class for Microsoft Graph API interactions"""
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTH_URL = "https://login.microsoftonline.com"
    
    def __init__(self, tenant_id: str = None):
        """
        Initialize the Microsoft Graph service
        
        Args:
            tenant_id: Azure AD tenant ID. If not provided, uses 'common' for multi-tenant.
        """
        self.tenant_id = tenant_id or self._get_default_tenant_id()
        self.config = self._get_config()
    
    def _get_default_tenant_id(self) -> str:
        """Get default tenant ID from settings or use 'common' for multi-tenant"""
        return getattr(settings, 'MICROSOFT_GRAPH_TENANT_ID', 'common')
    
    def _get_config(self) -> MicrosoftGraphConfig:
        """Get Microsoft Graph configuration"""
        try:
            # For multi-tenant apps, we can use any active config
            if self.tenant_id == 'common':
                return MicrosoftGraphConfig.objects.filter(is_active=True).first()
            else:
                return MicrosoftGraphConfig.objects.get(tenant_id=self.tenant_id, is_active=True)
        except MicrosoftGraphConfig.DoesNotExist:
            raise ValueError(f"No active Microsoft Graph configuration found")
    
    def get_auth_url(self, redirect_uri: str, scopes: List[str]) -> str:
        """
        Generate Microsoft Graph authorization URL
        
        Args:
            redirect_uri: Redirect URI after authorization
            scopes: List of requested scopes
            
        Returns:
            Authorization URL
        """
        scope_string = " ".join(scopes)
        params = {
            'client_id': self.config.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': scope_string,
            'response_mode': 'query',
            'state': 'microsoft_graph_auth'
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_URL}/{self.tenant_id}/oauth2/v2.0/authorize?{query_string}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from Microsoft
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Token response data
        """
        token_url = f"{self.AUTH_URL}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response data
        """
        token_url = f"{self.AUTH_URL}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get user profile from Microsoft Graph
        
        Args:
            access_token: Microsoft Graph access token
            
        Returns:
            User profile data
        """
        url = f"{self.BASE_URL}/me"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get user's calendars from Microsoft Graph
        
        Args:
            access_token: Microsoft Graph access token
            
        Returns:
            List of calendar data
        """
        url = f"{self.BASE_URL}/me/calendars"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json().get('value', [])
    
    def get_calendar_events(self, access_token: str, calendar_id: str, 
                          start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Get calendar events from Microsoft Graph
        
        Args:
            access_token: Microsoft Graph access token
            calendar_id: Calendar ID
            start_time: Start time for events (default: now)
            end_time: End time for events (default: 30 days from now)
            
        Returns:
            List of calendar events
        """
        if not start_time:
            start_time = timezone.now()
        if not end_time:
            end_time = start_time + timedelta(days=30)
        
        url = f"{self.BASE_URL}/me/calendars/{calendar_id}/events"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        params = {
            'startDateTime': start_time.isoformat(),
            'endDateTime': end_time.isoformat(),
            '$orderby': 'start/dateTime'
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json().get('value', [])
    
    def create_calendar_event(self, access_token: str, calendar_id: str, 
                            event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a calendar event in Microsoft Graph
        
        Args:
            access_token: Microsoft Graph access token
            calendar_id: Calendar ID
            event_data: Event data
            
        Returns:
            Created event data
        """
        url = f"{self.BASE_URL}/me/calendars/{calendar_id}/events"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=event_data)
        response.raise_for_status()
        
        return response.json()
    
    def get_teams_user(self, access_token: str) -> Dict[str, Any]:
        """
        Get Teams user information
        
        Args:
            access_token: Microsoft Graph access token
            
        Returns:
            Teams user data
        """
        url = f"{self.BASE_URL}/me"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_onedrive_files(self, access_token: str, folder_path: str = "/") -> List[Dict[str, Any]]:
        """
        Get OneDrive files
        
        Args:
            access_token: Microsoft Graph access token
            folder_path: Folder path to list files from
            
        Returns:
            List of file data
        """
        url = f"{self.BASE_URL}/me/drive/root:{folder_path}/children"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json().get('value', [])
    
    def download_onedrive_file(self, access_token: str, file_id: str) -> Dict[str, Any]:
        """
        Get download URL for OneDrive file
        
        Args:
            access_token: Microsoft Graph access token
            file_id: File ID
            
        Returns:
            File download data
        """
        url = f"{self.BASE_URL}/me/drive/items/{file_id}/content"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, allow_redirects=False)
        
        if response.status_code == 302:
            return {
                'download_url': response.headers.get('Location'),
                'file_id': file_id
            }
        
        response.raise_for_status()
        return response.json()
    
    def get_valid_school_token(self, school_account) -> Optional[str]:
        """
        Get valid access token for school account, refreshing if necessary
        
        Args:
            school_account: SchoolMicrosoftAccount instance
            
        Returns:
            Valid access token or None
        """
        if school_account.is_expired and school_account.refresh_token:
            # Refresh the token
            try:
                new_token_data = self.refresh_access_token(school_account.refresh_token)
                
                # Update the school account with new tokens
                school_account.access_token = new_token_data['access_token']
                school_account.refresh_token = new_token_data.get('refresh_token', school_account.refresh_token)
                school_account.expires_at = timezone.now() + timedelta(seconds=new_token_data.get('expires_in', 3600))
                school_account.save()
                
            except Exception as e:
                logger.error(f"Failed to refresh token for school {school_account.school.name}: {e}")
                return None
        
        return school_account.access_token
    
    def create_or_get_online_meeting(self, access_token: str, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or get an existing online meeting in Microsoft Graph using externalId
        
        Args:
            access_token: Microsoft Graph access token
            meeting_data: Meeting data with externalId
            
        Returns:
            Meeting data (created or existing)
        """
        url = f"{self.BASE_URL}/me/onlineMeetings/createOrGet"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=meeting_data)
        response.raise_for_status()
        
        return response.json()
    
    def create_online_meeting(self, access_token: str, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an online meeting in Microsoft Graph (legacy method)
        
        Args:
            access_token: Microsoft Graph access token
            meeting_data: Meeting data
            
        Returns:
            Created meeting data
        """
        return self.create_or_get_online_meeting(access_token, meeting_data)
