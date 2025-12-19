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

        # Parent: spectator mode, read-only
        if request.user.role == UserRole.PARENT:
            return request.method in permissions.SAFE_METHODS
        
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
            if hasattr(obj, 'submission'):
                # For Grade objects, check if the submission's assignment belongs to the teacher
                return obj.submission.assignment.teacher == user
            if hasattr(obj, 'graded_by'):
                # For Grade objects, check if the teacher is the one who graded it OR if the assignment belongs to the teacher
                if obj.graded_by == user:
                    return True
                if hasattr(obj, 'submission'):
                    return obj.submission.assignment.teacher == user
            return False
        
        # Student can access their own data and resources from their enrolled courses
        if user.role == UserRole.STUDENT:
            # Direct student assignment
            if hasattr(obj, 'student'):
                return obj.student == user
            if hasattr(obj, 'user'):
                return obj.user == user
            
            # Check if student is enrolled in the classroom/subject group
            if hasattr(obj, 'subject_group'):
                student_classrooms = user.classroom_users.values_list('classroom', flat=True)
                return obj.subject_group.classroom.id in student_classrooms
            
            if hasattr(obj, 'course_section'):
                student_classrooms = user.classroom_users.values_list('classroom', flat=True)
                return obj.course_section.subject_group.classroom.id in student_classrooms
            
            # Check through classroom enrollment
            if hasattr(obj, 'classroom'):
                student_classrooms = user.classroom_users.values_list('classroom', flat=True)
                return obj.classroom.id in student_classrooms
            
            return False
        
        # Parent: spectator mode, can view data related to their children (students) only
        if user.role == UserRole.PARENT:
            # Direct student link
            children_qs = user.children.all()
            if hasattr(obj, 'student'):
                return obj.student in children_qs
            if hasattr(obj, 'user'):
                return obj.user in children_qs

            # Objects linked via subject_group / course_section / classroom are allowed
            # if any of the parent's children is in that classroom.
            from django.contrib.auth import get_user_model
            User = get_user_model()

            def child_classroom_ids():
                return User.objects.filter(
                    id__in=children_qs.values_list('id', flat=True)
                ).values_list('classroom_users__classroom', flat=True)

            classrooms = set(child_classroom_ids())

            if hasattr(obj, 'subject_group') and hasattr(obj.subject_group, 'classroom'):
                return obj.subject_group.classroom.id in classrooms

            if hasattr(obj, 'course_section') and hasattr(obj.course_section, 'subject_group'):
                sg = obj.course_section.subject_group
                if hasattr(sg, 'classroom'):
                    return sg.classroom.id in classrooms

            if hasattr(obj, 'classroom'):
                return obj.classroom.id in classrooms

            return False
        
        return False
