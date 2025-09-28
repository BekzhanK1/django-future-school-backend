from rest_framework import serializers


class CheckAccessRequestSerializer(serializers.Serializer):
    """
    Request serializer for checking user access to objects.
    
    This serializer validates the input for the check-access endpoint,
    ensuring the object type is valid and the ID is a positive integer.
    """
    type = serializers.ChoiceField(
        choices=[
            'test', 'subjectgroup', 'attendance', 'assignment', 
            'resource', 'coursesection', 'event', 'submission',
            'school', 'classroom'
        ],
        help_text="Type of object to check access for. Valid values: test, subjectgroup, attendance, assignment, resource, coursesection, event, submission, school, classroom"
    )
    id = serializers.IntegerField(
        min_value=1,
        help_text="ID of the object to check access for. Must be a positive integer."
    )


class CheckAccessResponseSerializer(serializers.Serializer):
    """
    Response serializer for access check results.
    
    This serializer formats the response from the check-access endpoint,
    providing both the access decision and a human-readable explanation.
    """
    has_access = serializers.BooleanField(
        help_text="Whether the user has access to the object. true if access is granted, false otherwise."
    )
    reason = serializers.CharField(
        help_text="Human-readable explanation of why access is granted or denied. Examples: 'Teacher has access to their assigned objects', 'Student does not have access to this object'"
    )
