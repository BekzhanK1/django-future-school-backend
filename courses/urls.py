from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, SubjectGroupViewSet, CourseSectionViewSet,
    ScheduleSlotViewSet, AcademicYearViewSet, HolidayViewSet
)
from .views_ktp import (
    AcademicPlanViewSet,
    PlanSubjectGroupViewSet,
    PlanQuarterDetailViewSet,
    SectionViewSet,
    LearningObjectiveViewSet,
    LessonViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'subject-groups', SubjectGroupViewSet)
router.register(r'course-sections', CourseSectionViewSet)
router.register(r'schedule-slots', ScheduleSlotViewSet)
router.register(r'academic-years', AcademicYearViewSet)
router.register(r'holidays', HolidayViewSet)

router.register(r'academic-plans', AcademicPlanViewSet)
router.register(r'plan-subject-groups', PlanSubjectGroupViewSet)
router.register(r'plan-quarter-details', PlanQuarterDetailViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'learning-objectives', LearningObjectiveViewSet)
router.register(r'lessons', LessonViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
