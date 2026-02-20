from rest_framework import serializers
from .models import User, AuthSession, PasswordResetToken, UserRole


class UserSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    children = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'iin', 'first_name', 'last_name', 'phone_number', 'role', 'is_active', 'kundelik_id', 'school', 'school_name', 'children', 'parents', 'avatar']
        read_only_fields = ['id', 'username']

    def get_children(self, obj):
        """Get children (students) for parent users"""
        if obj.role == UserRole.PARENT:
            children = obj.children.filter(role=UserRole.STUDENT).all()
            return [{
                'id': child.id,
                'username': child.username,
                'email': child.email,
                'first_name': child.first_name,
                'last_name': child.last_name,
            } for child in children]
        return []
    
    def get_parents(self, obj):
        """Get parents for student users"""
        if obj.role == UserRole.STUDENT:
            parents = obj.parents.filter(role=UserRole.PARENT).all()
            return [{
                'id': parent.id,
                'username': parent.username,
                'email': parent.email,
                'first_name': parent.first_name,
                'last_name': parent.last_name,
            } for parent in parents]
        return []


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """For authenticated user updating own profile: phone_number, iin, and avatar only."""
    class Meta:
        model = User
        fields = ['phone_number', 'iin', 'avatar']
        extra_kwargs = {
            'phone_number': {'required': False, 'allow_blank': True},
            'iin': {'required': False, 'allow_blank': True},
            'avatar': {'required': False, 'allow_blank': True},
        }
        
    def validate_iin(self, value):
        if value:
            if not value.isdigit() or len(value) != 12:
                raise serializers.ValidationError("IIN must be exactly 12 digits.")
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'iin', 'first_name', 'last_name', 'phone_number', 'password', 'password_confirm', 'role', 'school', 'kundelik_id', 'is_active']
        extra_kwargs = {
            'is_active': {'default': True},
            'iin': {'required': False, 'allow_blank': True}
        }
    
    def validate_iin(self, value):
        if value:
            if not value.isdigit() or len(value) != 12:
                raise serializers.ValidationError("IIN must be exactly 12 digits.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        # Ensure is_active is True by default if not provided
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        user = User.objects.create_user(password=password, **validated_data)
        return user


class AuthSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthSession
        fields = ['id', 'user_agent', 'ip_address', 'is_active', 'created_at', 'expires_at']
        read_only_fields = ['id', 'created_at', 'expires_at']


class PasswordResetTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetToken
        fields = ['id', 'created_at', 'expires_at', 'used']
        read_only_fields = ['id', 'created_at', 'expires_at', 'used']


class ParentChildSerializer(serializers.Serializer):
    """Serializer for managing parent-child relationships"""
    parent_id = serializers.IntegerField()
    child_id = serializers.IntegerField()
    
    def validate_parent_id(self, value):
        try:
            parent = User.objects.get(id=value, role=UserRole.PARENT)
        except User.DoesNotExist:
            raise serializers.ValidationError("Parent user not found or is not a parent")
        return value
    
    def validate_child_id(self, value):
        try:
            child = User.objects.get(id=value, role=UserRole.STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError("Child user not found or is not a student")
        return value
    
    def validate(self, attrs):
        parent_id = attrs['parent_id']
        child_id = attrs['child_id']
        
        if parent_id == child_id:
            raise serializers.ValidationError("Parent and child cannot be the same user")
        
        return attrs


class BulkParentChildSerializer(serializers.Serializer):
    """Serializer for bulk adding/removing parent-child relationships"""
    parent_id = serializers.IntegerField()
    child_ids = serializers.ListField(child=serializers.IntegerField())
    
    def validate_parent_id(self, value):
        try:
            parent = User.objects.get(id=value, role=UserRole.PARENT)
        except User.DoesNotExist:
            raise serializers.ValidationError("Parent user not found or is not a parent")
        return value
    
    def validate_child_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one child ID is required")
        
        children = User.objects.filter(id__in=value, role=UserRole.STUDENT)
        if children.count() != len(value):
            raise serializers.ValidationError("Some child users do not exist or are not students")
        return value
