from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ForumThreadViewSet, ForumPostViewSet


router = DefaultRouter()
router.register(r'forum/threads', ForumThreadViewSet, basename='forum-threads')
router.register(r'forum/posts', ForumPostViewSet, basename='forum-posts')

urlpatterns = [
    path('', include(router.urls)),
]


