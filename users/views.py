from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import AuthSession, PasswordResetToken, User
from .serializers import UserSerializer, UserCreateSerializer, AuthSessionSerializer, PasswordResetTokenSerializer
from .access_checker import AccessChecker
from .access_serializers import CheckAccessRequestSerializer, CheckAccessResponseSerializer
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin
from common.tasks import send_email_task
from future_school.settings import FRONTEND_URL


class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get the user from the validated credentials
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.user
            
            # Serialize user data
            user_serializer = UserSerializer(user)
            user_data = user_serializer.data
            
            # Add user data to the response
            response.data['user'] = user_data
            
            # Add role-specific data
            if user.role == 'student':
                student_data = self.get_student_data(user)
                response.data['user']['student_data'] = student_data
            
        return response
    
    def get_student_data(self, user):
        """Get comprehensive student data including courses, assignments, and grades"""
        from django.utils import timezone
        from datetime import timedelta
        from learning.models import Assignment, Submission, Grade
        from courses.models import Course, SubjectGroup, CourseSection
        from schools.models import Classroom
        
        # Get student's classrooms
        classrooms = user.classroom_users.select_related('classroom__school').all()
        classroom_data = []
        for cu in classrooms:
            classroom_data.append({
                'id': cu.classroom.id,
                'grade': cu.classroom.grade,
                'letter': cu.classroom.letter,
                'language': cu.classroom.language,
                'school_name': cu.classroom.school.name,
                'school_id': cu.classroom.school.id
            })
        
        # Get student's courses through subject groups
        subject_groups = SubjectGroup.objects.filter(
            classroom__classroom_users__user=user
        ).select_related('course', 'teacher', 'classroom').all()
        
        courses_data = []
        for sg in subject_groups:
            # Get course sections
            sections = CourseSection.objects.filter(subject_group=sg).all()
            sections_data = []
            for section in sections:
                sections_data.append({
                    'id': section.id,
                    'title': section.title,
                    'position': section.position
                })
            
            courses_data.append({
                'id': sg.course.id,
                'course_code': sg.course.course_code,
                'name': sg.course.name,
                'description': sg.course.description,
                'grade': sg.course.grade,
                'teacher': {
                    'id': sg.teacher.id if sg.teacher else None,
                    'username': sg.teacher.username if sg.teacher else None,
                    'first_name': sg.teacher.first_name if sg.teacher else None,
                    'last_name': sg.teacher.last_name if sg.teacher else None,
                    'email': sg.teacher.email if sg.teacher else None
                },
                'classroom': {
                    'id': sg.classroom.id,
                    'grade': sg.classroom.grade,
                    'letter': sg.classroom.letter,
                    'language': sg.classroom.language
                },
                'sections': sections_data
            })
        
        # Get upcoming assignments (next 7 days)
        now = timezone.now()
        next_week = now + timedelta(days=7)
        
        upcoming_assignments = Assignment.objects.filter(
            course_section__subject_group__classroom__classroom_users__user=user,
            due_at__range=[now, next_week]
        ).select_related('course_section__subject_group__course', 'teacher').all()
        
        upcoming_assignments_data = []
        for assignment in upcoming_assignments:
            upcoming_assignments_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'due_at': assignment.due_at.isoformat(),
                'max_grade': assignment.max_grade,
                'course_name': assignment.course_section.subject_group.course.name,
                'course_code': assignment.course_section.subject_group.course.course_code,
                'teacher': assignment.teacher.username if assignment.teacher else None,
                'section_title': assignment.course_section.title
            })
        
        # Get recent submissions and grades
        recent_submissions = Submission.objects.filter(
            student=user
        ).select_related('assignment__course_section__subject_group__course', 'grade').order_by('-submitted_at')[:10]
        
        submissions_data = []
        for submission in recent_submissions:
            grade_info = None
            if hasattr(submission, 'grade'):
                grade_info = {
                    'grade_value': submission.grade.grade_value,
                    'max_grade': submission.assignment.max_grade,
                    'feedback': submission.grade.feedback,
                    'graded_at': submission.grade.graded_at.isoformat(),
                    'graded_by': submission.grade.graded_by.username
                }
            
            submissions_data.append({
                'id': submission.id,
                'assignment_title': submission.assignment.title,
                'assignment_id': submission.assignment.id,
                'course_name': submission.assignment.course_section.subject_group.course.name,
                'course_code': submission.assignment.course_section.subject_group.course.course_code,
                'submitted_at': submission.submitted_at.isoformat(),
                'grade': grade_info
            })
        
        # Get overall statistics
        total_assignments = Assignment.objects.filter(
            course_section__subject_group__classroom__classroom_users__user=user
        ).count()
        
        submitted_assignments = Submission.objects.filter(student=user).count()
        
        graded_assignments = Grade.objects.filter(
            submission__student=user
        ).count()
        
        # Calculate average grade if there are grades
        grades = Grade.objects.filter(submission__student=user).values_list('grade_value', flat=True)
        average_grade = sum(grades) / len(grades) if grades else None
        
        return {
            'classrooms': classroom_data,
            'courses': courses_data,
            'upcoming_assignments': upcoming_assignments_data,
            'recent_submissions': submissions_data,
            'statistics': {
                'total_assignments': total_assignments,
                'submitted_assignments': submitted_assignments,
                'graded_assignments': graded_assignments,
                'average_grade': average_grade
            }
        }


class RefreshView(TokenRefreshView):
    pass


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Incorrect password"})
        validate_password(attrs["new_password"], user)
        return attrs


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestPasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField()


@extend_schema(
    operation_id='request_password_reset',
    summary='Request password reset',
    request=RequestPasswordResetSerializer,
    responses={201: PasswordResetTokenSerializer, 204: None},
    tags=['auth']
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def request_password_reset(request):
    serializer = RequestPasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = User.objects.get(username=serializer.validated_data["username"])
    except User.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)
    token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    # Send reset email asynchronously
    reset_link = f"{FRONTEND_URL}/reset-password?token={token.token}"
    subject = "Password Reset Instructions"
    text_body = (
        "We received a request to reset your password.\n\n"
        f"Use this token: {token.token}\n"
        f"Or click the link: {reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html_body = (
        f"<p>We received a request to reset your password.</p>"
        f"<p><strong>Token:</strong> {token.token}</p>"
        f"<p><a href=\"{reset_link}\">Reset your password</a></p>"
        f"<p>If you did not request this, you can ignore this email.</p>"
    )
    send_email_task.delay(subject, text_body, [user.email], html_body)
    return Response({"token": token.token}, status=status.HTTP_201_CREATED)


@extend_schema(
    operation_id='confirm_password_reset',
    summary='Confirm password reset',
    request=ConfirmPasswordResetSerializer,
    responses={204: None, 400: OpenApiTypes.OBJECT},
    tags=['auth']
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def confirm_password_reset(request):
    serializer = ConfirmPasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        prt = PasswordResetToken.objects.get(token=serializer.validated_data["token"], used=False)
    except PasswordResetToken.DoesNotExist:
        return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
    if prt.expires_at < timezone.now():
        return Response({"detail": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)
    user = prt.user
    validate_password(serializer.validated_data["new_password"], user)
    user.set_password(serializer.validated_data["new_password"])
    user.save()
    prt.used = True
    prt.save(update_fields=["used"])
    return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(ModelViewSet):
    queryset = User.objects.select_related('school').all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'school', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['username', 'email', 'first_name', 'last_name', 'role']
    ordering = ['username']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter for students without classrooms
        no_classroom = self.request.query_params.get('no_classroom')
        if no_classroom and no_classroom.lower() in ['true', '1', 'yes']:
            # Get users who don't have any ClassroomUser entries
            queryset = queryset.filter(classroom_users__isnull=True)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer


class AuthSessionViewSet(ModelViewSet):
    queryset = AuthSession.objects.select_related('user').all()
    serializer_class = AuthSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own sessions
        if self.request.user.role in ['superadmin', 'schooladmin']:
            return self.queryset
        return self.queryset.filter(user=self.request.user)


class PasswordResetTokenViewSet(ModelViewSet):
    queryset = PasswordResetToken.objects.select_related('user').all()
    serializer_class = PasswordResetTokenSerializer
    permission_classes = [IsSuperAdmin]


class CheckAccessView(APIView):
    """
    Check if the authenticated user has access to a specific object.
    
    This endpoint allows frontend applications to verify user permissions
    before attempting to access or display specific resources.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        operation_id='check_access',
        summary='Check User Access to Object',
        description='Verify if the authenticated user has permission to access a specific object in the system.',
        request=CheckAccessRequestSerializer,
        responses={
            200: CheckAccessResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        tags=['Access Control']
    )
    def post(self, request):
        """
        Check access to an object
        
        Request body:
        {
            "type": "test|subjectgroup|attendance|assignment|resource|coursesection|event|submission|school|classroom",
            "id": 123
        }
        
        Response:
        {
            "has_access": true/false,
            "reason": "Explanation of access decision"
        }
        """
        # Validate request data
        serializer = CheckAccessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        object_type = serializer.validated_data['type']
        object_id = serializer.validated_data['id']
        
        # Check access using AccessChecker
        result = AccessChecker.check_access(request.user, object_type, object_id)
        
        # Return response
        response_serializer = CheckAccessResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)