from django.urls import path, include
from rest_framework.routers import DefaultRouter
from assessments.views import TestViewSet

# Create a router for tests with custom prefix
router = DefaultRouter()
router.register(r'tests', TestViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
