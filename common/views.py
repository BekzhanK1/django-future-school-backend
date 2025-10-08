from django.db import connection
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint that verifies the application and database are operational.
    
    Returns:
        - 200 OK: When the application and database are healthy
        - 503 Service Unavailable: When the database connection fails
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Return healthy status
        return Response({
            'status': 'healthy',
            'service': 'future_school_api',
            'database': 'connected'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        # Return unhealthy status
        return Response({
            'status': 'unhealthy',
            'service': 'future_school_api',
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)