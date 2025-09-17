from rest_framework import permissions
from users.models import UserRole


class StudentPermission(permissions.BasePermission):
    """Permission for students - can only access their own data"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.STUDENT
    
    def has_object_permission(self, request, view, obj):
        # Students can only access their own submissions, attempts, etc.
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class TeacherPermission(permissions.BasePermission):
    """Permission for teachers - can access their assigned subject groups"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.TEACHER
    
    def has_object_permission(self, request, view, obj):
        # Teachers can access content from their subject groups
        if hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        if hasattr(obj, 'course_section'):
            return obj.course_section.subject_group.teacher == request.user
        if hasattr(obj, 'assignment'):
            return obj.assignment.teacher == request.user
        if hasattr(obj, 'test'):
            return obj.test.teacher == request.user
        return False


class SchoolAdminPermission(permissions.BasePermission):
    """Permission for school admins - can see everything in their school"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.SCHOOLADMIN
    
    def has_object_permission(self, request, view, obj):
        # School admins can see everything in their school
        if hasattr(obj, 'school'):
            return obj.school == request.user.school
        if hasattr(obj, 'student'):
            return obj.student.school == request.user.school
        if hasattr(obj, 'teacher'):
            return obj.teacher.school == request.user.school
        return False


class RoleBasedPermission(permissions.BasePermission):
    """Combined permission that checks role-based access"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can do everything
        if request.user.role == UserRole.SUPERADMIN:
            return True
        
        # School admin can do everything in their school
        if request.user.role == UserRole.SCHOOLADMIN:
            return True
        
        # Teacher can access their assigned content
        if request.user.role == UserRole.TEACHER:
            return True
        
        # Student can access their own data
        if request.user.role == UserRole.STUDENT:
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Superadmin can access everything
        if user.role == UserRole.SUPERADMIN:
            return True
        
        # School admin can access everything in their school
        if user.role == UserRole.SCHOOLADMIN:
            if hasattr(obj, 'school'):
                return obj.school == user.school
            if hasattr(obj, 'student'):
                return obj.student.school == user.school
            if hasattr(obj, 'teacher'):
                return obj.teacher.school == user.school
            return True
        
        # Teacher can access their assigned content
        if user.role == UserRole.TEACHER:
            if hasattr(obj, 'teacher'):
                return obj.teacher == user
            if hasattr(obj, 'course_section'):
                return obj.course_section.subject_group.teacher == user
            if hasattr(obj, 'assignment'):
                return obj.assignment.teacher == user
            if hasattr(obj, 'test'):
                return obj.test.teacher == user
            return False
        
        # Student can access their own data
        if user.role == UserRole.STUDENT:
            if hasattr(obj, 'student'):
                return obj.student == user
            if hasattr(obj, 'user'):
                return obj.user == user
            return False
        
        return False
