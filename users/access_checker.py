from django.core.exceptions import ObjectDoesNotExist
from users.models import UserRole
from assessments.models import Test, Attempt
from courses.models import SubjectGroup, CourseSection
from learning.models import Attendance, Assignment, Resource, Event, Submission
from schools.models import School, Classroom


class AccessChecker:
    """Centralized access checker for role-based permissions"""
    
    # Mapping of object types to their models
    MODEL_MAPPING = {
        'test': Test,
        'subjectgroup': SubjectGroup,
        'attendance': Attendance,
        'assignment': Assignment,
        'resource': Resource,
        'coursesection': CourseSection,
        'event': Event,
        'submission': Submission,
        'school': School,
        'classroom': Classroom,
    }
    
    @classmethod
    def check_access(cls, user, object_type, object_id):
        """
        Check if user has access to the specified object
        
        Args:
            user: User instance
            object_type: String type of object (test, subjectgroup, etc.)
            object_id: ID of the object
            
        Returns:
            dict: {'has_access': bool, 'reason': str}
        """
        try:
            # Get the model class
            model_class = cls.MODEL_MAPPING.get(object_type.lower())
            if not model_class:
                return {
                    'has_access': False,
                    'reason': f'Unknown object type: {object_type}'
                }
            
            # Get the object
            obj = model_class.objects.get(id=object_id)
            
            # Check access based on user role
            return cls._check_role_access(user, obj, object_type)
            
        except ObjectDoesNotExist:
            return {
                'has_access': False,
                'reason': f'{object_type.title()} with id {object_id} not found'
            }
        except Exception as e:
            return {
                'has_access': False,
                'reason': f'Error checking access: {str(e)}'
            }
    
    @classmethod
    def _check_role_access(cls, user, obj, object_type):
        """Check access based on user role"""
        
        # Superadmin can access everything
        if user.role == UserRole.SUPERADMIN:
            return {
                'has_access': True,
                'reason': 'Superadmin has access to all objects'
            }
        
        # School admin can access everything in their school
        if user.role == UserRole.SCHOOLADMIN:
            return cls._check_school_admin_access(user, obj, object_type)
        
        # Teacher can access their assigned content
        if user.role == UserRole.TEACHER:
            return cls._check_teacher_access(user, obj, object_type)
        
        # Student can access their own data and enrolled courses
        if user.role == UserRole.STUDENT:
            return cls._check_student_access(user, obj, object_type)
        
        return {
            'has_access': False,
            'reason': 'Unknown user role'
        }
    
    @classmethod
    def _check_school_admin_access(cls, user, obj, object_type):
        """Check access for school admin"""
        if not user.school:
            return {
                'has_access': False,
                'reason': 'School admin not assigned to any school'
            }
        
        # Check if object belongs to the school
        if hasattr(obj, 'school'):
            if obj.school == user.school:
                return {
                    'has_access': True,
                    'reason': 'School admin has access to objects in their school'
                }
        
        # Check through related objects
        if hasattr(obj, 'student') and obj.student.school == user.school:
            return {
                'has_access': True,
                'reason': 'School admin has access to student objects in their school'
            }
        
        if hasattr(obj, 'teacher') and obj.teacher.school == user.school:
            return {
                'has_access': True,
                'reason': 'School admin has access to teacher objects in their school'
            }
        
        # Check through subject groups
        if hasattr(obj, 'subject_group'):
            if obj.subject_group.classroom.school == user.school:
                return {
                    'has_access': True,
                    'reason': 'School admin has access to subject group objects in their school'
                }
        
        if hasattr(obj, 'course_section'):
            if obj.course_section.subject_group.classroom.school == user.school:
                return {
                    'has_access': True,
                    'reason': 'School admin has access to course section objects in their school'
                }
        
        return {
            'has_access': False,
            'reason': 'Object does not belong to school admin\'s school'
        }
    
    @classmethod
    def _check_teacher_access(cls, user, obj, object_type):
        """Check access for teacher"""
        
        # Direct teacher assignment
        if hasattr(obj, 'teacher') and obj.teacher == user:
            return {
                'has_access': True,
                'reason': 'Teacher has access to their assigned objects'
            }
        
        # Through course sections
        if hasattr(obj, 'course_section'):
            if obj.course_section.subject_group.teacher == user:
                return {
                    'has_access': True,
                    'reason': 'Teacher has access to objects in their course sections'
                }
        
        # Through assignments
        if hasattr(obj, 'assignment') and obj.assignment.teacher == user:
            return {
                'has_access': True,
                'reason': 'Teacher has access to their assignment objects'
            }
        
        # Through tests
        if hasattr(obj, 'test') and obj.test.teacher == user:
            return {
                'has_access': True,
                'reason': 'Teacher has access to their test objects'
            }
        
        # Through subject groups
        if hasattr(obj, 'subject_group') and obj.subject_group.teacher == user:
            return {
                'has_access': True,
                'reason': 'Teacher has access to their subject group objects'
            }
        
        return {
            'has_access': False,
            'reason': 'Teacher does not have access to this object'
        }
    
    @classmethod
    def _check_student_access(cls, user, obj, object_type):
        """Check access for student"""
        
        # Direct student assignment
        if hasattr(obj, 'student') and obj.student == user:
            return {
                'has_access': True,
                'reason': 'Student has access to their own objects'
            }
        
        if hasattr(obj, 'user') and obj.user == user:
            return {
                'has_access': True,
                'reason': 'Student has access to their own objects'
            }
        
        # Check if student is enrolled in the classroom/subject group
        if hasattr(obj, 'subject_group'):
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            if obj.subject_group.classroom.id in student_classrooms:
                return {
                    'has_access': True,
                    'reason': 'Student has access to objects in their enrolled subject groups'
                }
        
        if hasattr(obj, 'course_section'):
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            if obj.course_section.subject_group.classroom.id in student_classrooms:
                return {
                    'has_access': True,
                    'reason': 'Student has access to objects in their enrolled course sections'
                }
        
        # Check through classroom enrollment
        if hasattr(obj, 'classroom'):
            student_classrooms = user.classroom_users.values_list('classroom', flat=True)
            if obj.classroom.id in student_classrooms:
                return {
                    'has_access': True,
                    'reason': 'Student has access to objects in their enrolled classrooms'
                }
        
        return {
            'has_access': False,
            'reason': 'Student does not have access to this object'
        }
