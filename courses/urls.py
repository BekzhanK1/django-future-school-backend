from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, SubjectGroupViewSet, CourseSectionViewSet,
    ScheduleSlotViewSet, AcademicYearViewSet, HolidayViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'subject-groups', SubjectGroupViewSet)
router.register(r'course-sections', CourseSectionViewSet)
router.register(r'schedule-slots', ScheduleSlotViewSet)
router.register(r'academic-years', AcademicYearViewSet)
router.register(r'holidays', HolidayViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
