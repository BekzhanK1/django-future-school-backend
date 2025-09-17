from rest_framework import serializers
from .models import School, Classroom, ClassroomUser
from users.models import User


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'city', 'country', 'logo_url', 'contact_email', 'contact_phone', 'kundelik_id']


class ClassroomSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Classroom
        fields = ['id', 'grade', 'letter', 'language', 'kundelik_id', 'school', 'school_name']


class ClassroomUserSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = ClassroomUser
        fields = ['id', 'classroom', 'user', 'user_username', 'user_email', 'user_role']


class BulkClassroomUserSerializer(serializers.Serializer):
    classroom_id = serializers.IntegerField()
    user_ids = serializers.ListField(child=serializers.IntegerField())
    
    def validate_classroom_id(self, value):
        try:
            Classroom.objects.get(id=value)
        except Classroom.DoesNotExist:
            raise serializers.ValidationError("Classroom does not exist")
        return value
    
    def validate_user_ids(self, value):
        existing_users = User.objects.filter(id__in=value)
        if len(existing_users) != len(value):
            raise serializers.ValidationError("Some users do not exist")
        return value
    
    def create(self, validated_data):
        classroom_id = validated_data['classroom_id']
        user_ids = validated_data['user_ids']
        
        # Remove existing classroom users for this classroom
        ClassroomUser.objects.filter(classroom_id=classroom_id).delete()
        
        # Create new classroom users
        classroom_users = []
        for user_id in user_ids:
            classroom_users.append(ClassroomUser(classroom_id=classroom_id, user_id=user_id))
        
        return ClassroomUser.objects.bulk_create(classroom_users)
