from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionViewSet, OptionViewSet, AttemptViewSet, AnswerViewSet

router = DefaultRouter()
# Note: TestViewSet is registered in tests_urls.py to avoid conflicts
router.register(r'questions', QuestionViewSet)
router.register(r'options', OptionViewSet)
router.register(r'attempts', AttemptViewSet)
router.register(r'answers', AnswerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
