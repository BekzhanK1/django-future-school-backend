from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    RefreshView,
    ChangePasswordView,
    request_password_reset,
    confirm_password_reset,
    UserViewSet,
    AuthSessionViewSet,
    PasswordResetTokenViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'auth-sessions', AuthSessionViewSet)
router.register(r'password-reset-tokens', PasswordResetTokenViewSet)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("auth/request-password-reset/", request_password_reset, name="request_password_reset"),
    path("auth/confirm-password-reset/", confirm_password_reset, name="confirm_password_reset"),
    path("", include(router.urls)),
]



