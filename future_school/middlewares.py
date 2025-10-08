"""
Custom middleware for the Future School project.
"""

from django.http import HttpResponse


class RemoveXFrameForMedia:
    """
    Middleware to remove X-Frame-Options header for media files
    to allow embedding in iframes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Remove X-Frame-Options header for media files
        if request.path.startswith('/media/'):
            # FileResponse does not implement pop; mutate headers dict instead
            if 'X-Frame-Options' in response.headers:
                del response.headers['X-Frame-Options']
            
        return response



