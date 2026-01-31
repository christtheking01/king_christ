from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.conf import settings

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 1. Always let unauthenticated users through
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 2. Skip middleware for static/media files to prevent 500 errors
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        # 3. Only run logic if the flag is actually True
        if getattr(request.user, 'must_change_password', False):
            try:
                change_password_url = reverse('change_password')
                logout_url = reverse('logout')
                
                # PREVENT INFINITE LOOP: If they are already on the allowed pages, let them through
                if request.path == change_password_url or request.path == logout_url:
                    return self.get_response(request)
                
                # Otherwise, force them to the password change page
                return redirect(change_password_url)
                
            except NoReverseMatch:
                # If 'change_password' isn't in your urls.py, this avoids a 500 crash
                return self.get_response(request)
        
        # 4. If flag is False, proceed normally
        return self.get_response(request)
