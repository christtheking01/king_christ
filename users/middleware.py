from django.shortcuts import redirect
from django.urls import reverse

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Password change enforcement disabled
        response = self.get_response(request)
        return response


class NoCacheMiddleware:
    """Add cache-control headers to prevent back-button issues for logout only.
    Church members can use browser caching for better UX."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only add no-cache headers for login/logout pages, not for authenticated users
        # This prevents back-button issues after logout while allowing normal caching for logged-in users
        if request.path in ['/accounts/login/', '/accounts/_login_/', '/accounts/_logout_/']:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Vary'] = 'Cookie'
        
        return response