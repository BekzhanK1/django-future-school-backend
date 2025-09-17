from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SchoolViewSet, ClassroomViewSet, ClassroomUserViewSet

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'classrooms', ClassroomViewSet)
router.register(r'classroom-users', ClassroomUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
