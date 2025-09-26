from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceViewSet, AssignmentViewSet, AssignmentAttachmentViewSet, SubmissionViewSet, SubmissionAttachmentViewSet, GradeViewSet, AttendanceViewSet, EventViewSet
from .calendar_views import calendar_events, upcoming_events

router = DefaultRouter()
router.register(r'resources', ResourceViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'assignment-attachments', AssignmentAttachmentViewSet)
router.register(r'submissions', SubmissionViewSet)
router.register(r'submission-attachments', SubmissionAttachmentViewSet)
router.register(r'grades', GradeViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'events', EventViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('calendar/events/', calendar_events, name='calendar_events'),
    path('calendar/upcoming/', upcoming_events, name='upcoming_events'),
]
