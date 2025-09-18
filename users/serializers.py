from rest_framework import serializers
from .models import User, AuthSession, PasswordResetToken


class UserSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'is_active', 'kundelik_id', 'school', 'school_name']
        read_only_fields = ['id', 'username']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'password', 'password_confirm', 'role', 'school', 'kundelik_id']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
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
