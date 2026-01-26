from django.utils import timezone
from datetime import timedelta


class UpdateLastActiveMiddleware:
    """
    Updates user's last_active timestamp, but only once every 5 minutes
    to avoid excessive database writes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            last_active = request.user.last_active

            # Update if last_active is None (first time) or older than 5 minutes
            if last_active is None or (now - last_active) > timedelta(minutes=5):
                request.user.last_active = now
                request.user.save(update_fields=['last_active'])

        response = self.get_response(request)
        return response
