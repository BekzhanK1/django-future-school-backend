from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, SubjectGroupViewSet, CourseSectionViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'subject-groups', SubjectGroupViewSet)
router.register(r'course-sections', CourseSectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
