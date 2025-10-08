from rest_framework import permissions
from users.models import UserRole


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.SUPERADMIN


class IsSchoolAdminOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.SUPERADMIN, UserRole.SCHOOLADMIN]
        )


class IsTeacherOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        print(request.user)
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.SUPERADMIN, UserRole.SCHOOLADMIN, UserRole.TEACHER]
        )


class IsStudentOrTeacherOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.SUPERADMIN, UserRole.SCHOOLADMIN, UserRole.TEACHER, UserRole.STUDENT]
        )