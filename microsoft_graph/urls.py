# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import (
#     MicrosoftGraphConfigView,
#     MicrosoftAuthView,
#     MicrosoftTokenExchangeView,
#     SchoolMicrosoftAccountViewSet,
#     CreateOnlineMeetingByExternalIdView,
#     GetOnlineMeetingByExternalIdView,
#     OnlineMeetingViewSet
# )

# router = DefaultRouter()
# router.register(r'school-accounts', SchoolMicrosoftAccountViewSet)
# router.register(r'online-meetings', OnlineMeetingViewSet)

# urlpatterns = [
#     # Admin endpoints (Superadmin only)
#     path('config/', MicrosoftGraphConfigView.as_view(), name='microsoft_config'),
#     path('auth/url/', MicrosoftAuthView.as_view(), name='microsoft_auth_url'),
#     path('auth/token-exchange/', MicrosoftTokenExchangeView.as_view(), name='microsoft_token_exchange'),
    
#     # Teacher endpoints
#     path('meetings/create-by-external-id/', CreateOnlineMeetingByExternalIdView.as_view(), name='create_online_meeting_by_external_id'),
#     path('meetings/get-by-external-id/<str:external_id>/', GetOnlineMeetingByExternalIdView.as_view(), name='get_online_meeting_by_external_id'),
    
#     # Include router URLs
#     path('', include(router.urls)),
# ]
