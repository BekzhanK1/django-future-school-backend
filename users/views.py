from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import AuthSession, PasswordResetToken, User
from .serializers import UserSerializer, UserCreateSerializer, AuthSessionSerializer, PasswordResetTokenSerializer
from .access_checker import AccessChecker
from .access_serializers import CheckAccessRequestSerializer, CheckAccessResponseSerializer
from schools.permissions import IsSuperAdmin, IsSchoolAdminOrSuperAdmin
from common.tasks import send_email_task


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
            
        return response


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
    email = serializers.EmailField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField()


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def request_password_reset(request):
    serializer = RequestPasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = User.objects.get(email=serializer.validated_data["email"])
    except User.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)
    token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    # Send reset email asynchronously
    reset_link = f"http://localhost:3000/reset-password?token={token.token}"
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
    filterset_fields = ['role', 'school', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['username', 'email', 'first_name', 'last_name', 'role']
    ordering = ['username']
    
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