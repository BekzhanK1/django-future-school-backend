# """
# Microsoft Graph API Views

# Views for Microsoft Graph API integration:
# - Superadmin authentication for schools
# - Teacher online meeting creation
# """

# from datetime import datetime, timedelta
# import uuid
# from django.utils import timezone
# from rest_framework import status, permissions
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.viewsets import ModelViewSet
# from drf_spectacular.utils import extend_schema
# from drf_spectacular.types import OpenApiTypes

# from schools.permissions import IsSuperAdmin
# from learning.role_permissions import RoleBasedPermission
# from .models import SchoolMicrosoftAccount, OnlineMeeting, MicrosoftGraphConfig
# from courses.models import SubjectGroup

# from .serializers import (
#     MicrosoftGraphConfigSerializer,
#     SchoolMicrosoftAccountSerializer, 
#     OnlineMeetingSerializer,
#     MicrosoftAuthRequestSerializer,
#     MicrosoftAuthResponseSerializer,
#     MicrosoftTokenExchangeSerializer,
#     CreateOnlineMeetingSerializer,
#     CreateOnlineMeetingByExternalIdSerializer
# )
# from .services import MicrosoftGraphService


# class MicrosoftGraphConfigView(APIView):
#     """
#     Get Microsoft Graph configuration for direct authentication
#     Only accessible by superadmin
#     """
#     permission_classes = [IsSuperAdmin]
    
#     @extend_schema(
#         operation_id='get_microsoft_config',
#         summary='Get Microsoft Graph Configuration',
#         description='Get Microsoft Graph configuration for direct authentication',
#         responses={
#             200: MicrosoftGraphConfigSerializer,
#             404: OpenApiTypes.OBJECT,
#         },
#         tags=['Microsoft Graph - Admin']
#     )
#     def get(self, request):
#         """
#         Get Microsoft Graph configuration
        
#         Returns the client_id and other configuration needed for direct Microsoft authentication
#         """
#         try:
#             config = MicrosoftGraphConfig.objects.filter(is_active=True).first()
#             if not config:
#                 return Response({
#                     'error': 'No active Microsoft Graph configuration found'
#                 }, status=status.HTTP_404_NOT_FOUND)
            
#             serializer = MicrosoftGraphConfigSerializer(config)
#             return Response(serializer.data, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# class MicrosoftAuthView(APIView):
#     """
#     Get Microsoft Graph authorization URL for school setup
#     Only accessible by superadmin
#     """
#     permission_classes = [IsSuperAdmin]
    
#     @extend_schema(
#         operation_id='microsoft_auth_url',
#         summary='Get Microsoft Auth URL',
#         description='Get Microsoft Graph authorization URL for school Microsoft account setup',
#         request=MicrosoftAuthRequestSerializer,
#         responses={
#             200: MicrosoftAuthResponseSerializer,
#             400: OpenApiTypes.OBJECT,
#         },
#         tags=['Microsoft Graph - Admin']
#     )
#     def post(self, request):
#         """
#         Generate Microsoft Graph authorization URL for school setup
        
#         Request body:
#         {
#             "redirect_uri": "https://yourapp.com/microsoft/callback",
#             "scopes": ["https://graph.microsoft.com/OnlineMeetings.ReadWrite"]
#         }
#         """
#         serializer = MicrosoftAuthRequestSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
        
#         try:
#             service = MicrosoftGraphService()
#             auth_url = service.get_auth_url(
#                 redirect_uri=serializer.validated_data['redirect_uri'],
#                 scopes=serializer.validated_data['scopes']
#             )
            
#             return Response({
#                 'auth_url': auth_url,
#                 'state': 'microsoft_graph_auth'
#             }, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# class MicrosoftTokenExchangeView(APIView):
#     """
#     Exchange authorization code for tokens and save school Microsoft account
#     Only accessible by superadmin
#     """
#     permission_classes = [IsSuperAdmin]
    
#     @extend_schema(
#         operation_id='microsoft_token_exchange',
#         summary='Exchange Code for Tokens',
#         description='Exchange Microsoft authorization code for tokens and save school account',
#         request=MicrosoftTokenExchangeSerializer,
#         responses={
#             200: SchoolMicrosoftAccountSerializer,
#             400: OpenApiTypes.OBJECT,
#         },
#         tags=['Microsoft Graph - Admin']
#     )
#     def post(self, request):
#         """
#         Exchange authorization code for tokens and save school Microsoft account
        
#         Request body:
#         {
#             "code": "authorization_code_from_microsoft",
#             "redirect_uri": "https://yourapp.com/microsoft/callback",
#             "school_id": 1
#         }
#         """
#         serializer = MicrosoftTokenExchangeSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
        
#         try:
#             service = MicrosoftGraphService()
            
#             # Exchange code for tokens
#             token_data = service.exchange_code_for_token(
#                 code=serializer.validated_data['code'],
#                 redirect_uri=serializer.validated_data['redirect_uri']
#             )
            
#             # Get user profile to get email
#             user_profile = service.get_user_profile(token_data['access_token'])
#             microsoft_email = user_profile.get('mail') or user_profile.get('userPrincipalName')
            
#             # Save school Microsoft account
#             from schools.models import School
#             school = School.objects.get(id=serializer.validated_data['school_id'])
            
#             school_account, created = SchoolMicrosoftAccount.objects.update_or_create(
#                 school=school,
#                 defaults={
#                     'microsoft_email': microsoft_email,
#                     'access_token': token_data['access_token'],
#                     'refresh_token': token_data.get('refresh_token'),
#                     'token_type': token_data.get('token_type', 'Bearer'),
#                     'expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
#                     'scope': token_data.get('scope', ''),
#                     'created_by': request.user,
#                     'is_active': True
#                 }
#             )
            
#             response_serializer = SchoolMicrosoftAccountSerializer(school_account)
#             return Response(response_serializer.data, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# class SchoolMicrosoftAccountViewSet(ModelViewSet):
#     """
#     Manage school Microsoft accounts
#     Only accessible by superadmin
#     """
#     queryset = SchoolMicrosoftAccount.objects.select_related('school', 'created_by').all()
#     serializer_class = SchoolMicrosoftAccountSerializer
#     permission_classes = [IsSuperAdmin]
#     filterset_fields = ['school', 'is_active']
#     search_fields = ['school__name', 'microsoft_email']
#     ordering_fields = ['created_at', 'updated_at']
#     ordering = ['-created_at']


# class CreateOnlineMeetingByExternalIdView(APIView):
#     """
#     Create or get existing online meeting using SubjectGroup external_id
#     Accessible by teachers and school admins
#     Returns existing meeting if one already exists for the subject group
#     """
#     permission_classes = [RoleBasedPermission]
    
#     @extend_schema(
#         operation_id='create_or_get_online_meeting_by_external_id',
#         summary='Create or Get Online Meeting by External ID',
#         description='Create a new online meeting or get existing one using SubjectGroup external_id',
#         request=CreateOnlineMeetingByExternalIdSerializer,
#         responses={
#             200: OnlineMeetingSerializer,
#             201: OnlineMeetingSerializer,
#             400: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT,
#             404: OpenApiTypes.OBJECT,
#         },
#         tags=['Microsoft Graph - Teachers']
#     )
#     def post(self, request):
#         """
#         Create or get existing online meeting using SubjectGroup external_id
        
#         Returns existing meeting if one already exists for the subject group,
#         otherwise creates a new meeting.
#         """
#         serializer = CreateOnlineMeetingByExternalIdSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         update = serializer.validated_data.get('update', False)
#         print(update)
        
#         try:
#             try:
#                 subject_group = SubjectGroup.objects.get(
#                     id=serializer.validated_data['subject_group']
#                 )
#             except SubjectGroup.DoesNotExist:
#                 return Response({
#                     'error': 'SubjectGroup with this id not found'
#                 }, status=status.HTTP_404_NOT_FOUND)
            
#             if request.user.role == 'teacher' and subject_group.teacher != request.user:
#                 return Response({
#                     'error': 'You do not have permission to create meetings for this subject group'
#                 }, status=status.HTTP_403_FORBIDDEN)
            
#             if request.user.role == 'schooladmin' and subject_group.classroom.school != request.user.school:
#                 return Response({
#                     'error': 'You do not have permission to create meetings for this subject group'
#                 }, status=status.HTTP_403_FORBIDDEN)
            
#             if not update:
#                 try:
#                     existing_meeting = OnlineMeeting.objects.get(subject_group=subject_group)
#                     return Response(OnlineMeetingSerializer(existing_meeting).data, status=status.HTTP_200_OK)
#                 except OnlineMeeting.DoesNotExist:
#                     pass
            
#             try:
#                 school_account = SchoolMicrosoftAccount.objects.get(
#                     school=subject_group.classroom.school,
#                     is_active=True
#                 )
#             except SchoolMicrosoftAccount.DoesNotExist:
#                 return Response({
#                     'error': 'No Microsoft account configured for this school'
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             service = MicrosoftGraphService()
#             access_token = service.get_valid_school_token(school_account)
            
#             if not access_token:
#                 return Response({
#                     'error': 'Microsoft account token is expired and cannot be refreshed'
#                 }, status=status.HTTP_400_BAD_REQUEST)
            

#             if not subject_group.external_id:
#                 new_external_id = str(uuid.uuid4())
#                 subject_group.external_id = new_external_id
#                 subject_group.save()


#             if not update:
#                 try:
#                     existing_meeting = OnlineMeeting.objects.get(subject_group=subject_group)
#                     # Return existing meeting
#                     response_serializer = OnlineMeetingSerializer(existing_meeting)
#                     return Response(response_serializer.data, status=status.HTTP_200_OK)
#                 except OnlineMeeting.DoesNotExist:
#                     print("No existing meeting found")

#             print("Updating meeting")

#             meeting_data = {
#                 'externalId': subject_group.external_id,
#                 'subject': str(subject_group),
#                 'body': {
#                     'contentType': 'text',
#                     'content': serializer.validated_data.get('meeting_description', '')
#                 },
#                 'isOnlineMeeting': True,
#                 'onlineMeetingProvider': 'teamsForBusiness'
#             }
   
#             microsoft_meeting = service.create_or_get_online_meeting(access_token, meeting_data)
           
#             online_meeting = OnlineMeeting.objects.update_or_create(
#                 school_account=school_account,
#                 created_by=request.user,
#                 subject_group=subject_group,
#                 meeting_title=str(subject_group),
#                 meeting_description=serializer.validated_data.get('meeting_description', ''),
#                 microsoft_meeting_id=microsoft_meeting['id'],
#                 join_url=microsoft_meeting['joinWebUrl'],
#                 meeting_url=microsoft_meeting.get('webUrl'),
#                 start_time=microsoft_meeting['startDateTime'],
#                 end_time=microsoft_meeting['endDateTime']
#             )[0]
            
#             response_serializer = OnlineMeetingSerializer(online_meeting)
#             return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
#         except Exception as e:
#             return Response({
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# class GetOnlineMeetingByExternalIdView(APIView):
#     """
#     Get existing online meeting by SubjectGroup external_id
#     Accessible by teachers, school admins, and students
#     """
#     permission_classes = [RoleBasedPermission]
    
#     @extend_schema(
#         operation_id='get_online_meeting_by_external_id',
#         summary='Get Online Meeting by External ID',
#         description='Get existing online meeting using SubjectGroup external_id',
#         responses={
#             200: OnlineMeetingSerializer,
#             404: OpenApiTypes.OBJECT,
#             403: OpenApiTypes.OBJECT,
#         },
#         tags=['Microsoft Graph - Teachers']
#     )
#     def get(self, request, external_id):
#         """
#         Get existing online meeting by SubjectGroup external_id
        
#         Args:
#             external_id: The external_id of the SubjectGroup
#         """
#         try:
#             try:
#                 subject_group = SubjectGroup.objects.get(external_id=external_id)
#             except SubjectGroup.DoesNotExist:
#                 return Response({
#                     'error': 'SubjectGroup with this external_id not found'
#                 }, status=status.HTTP_404_NOT_FOUND)
            
#             # Check permissions
#             if request.user.role == 'teacher' and subject_group.teacher != request.user:
#                 return Response({
#                     'error': 'You do not have permission to access this meeting'
#                 }, status=status.HTTP_403_FORBIDDEN)
            
#             if request.user.role == 'schooladmin' and subject_group.classroom.school != request.user.school:
#                 return Response({
#                     'error': 'You do not have permission to access this meeting'
#                 }, status=status.HTTP_403_FORBIDDEN)
            
#             if request.user.role == 'student':
#                 # Students can access meetings for their enrolled subject groups
#                 student_classrooms = request.user.classroom_users.values_list('classroom', flat=True)
#                 if subject_group.classroom.id not in student_classrooms:
#                     return Response({
#                         'error': 'You do not have permission to access this meeting'
#                     }, status=status.HTTP_403_FORBIDDEN)
            
#             try:
#                 online_meeting = OnlineMeeting.objects.get(subject_group=subject_group)
#                 response_serializer = OnlineMeetingSerializer(online_meeting)
#                 return Response(response_serializer.data, status=status.HTTP_200_OK)
#             except OnlineMeeting.DoesNotExist:
#                 return Response({
#                     'error': 'No meeting found for this subject group'
#                 }, status=status.HTTP_404_NOT_FOUND)
            
#         except Exception as e:
#             return Response({
#                 'error': str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# class OnlineMeetingViewSet(ModelViewSet):
#     """
#     Manage online meetings
#     Teachers can see their meetings, school admins can see all meetings in their school
#     """
#     queryset = OnlineMeeting.objects.select_related(
#         'school_account__school', 
#         'created_by', 
#         'subject_group__course',
#         'subject_group__classroom'
#     ).all()
#     serializer_class = OnlineMeetingSerializer
#     permission_classes = [RoleBasedPermission]
#     filterset_fields = ['subject_group', 'is_active', 'school_account__school']
#     search_fields = ['meeting_title', 'meeting_description']
#     ordering_fields = ['start_time', 'created_at']
#     ordering = ['-start_time']
    
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         user = self.request.user
        
#         if user.role == 'teacher':
#             # Teachers can only see meetings for their subject groups
#             queryset = queryset.filter(subject_group__teacher=user)
#         elif user.role == 'schooladmin':
#             # School admins can see all meetings in their school
#             queryset = queryset.filter(school_account__school=user.school)
#         elif user.role == 'student':
#             # Students can see meetings for their enrolled subject groups
#             student_classrooms = user.classroom_users.values_list('classroom', flat=True)
#             queryset = queryset.filter(subject_group__classroom__id__in=student_classrooms)
        
#         return queryset