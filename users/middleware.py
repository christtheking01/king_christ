from django.shortcuts import redirect
from django.urls import reverse

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # URLs that should be accessible even when password change is required
            allowed_urls = [
                reverse('change_password'),
                reverse('logout'),
            ]
            
            # Check if user must change password and is not on allowed pages
            if request.user.must_change_password and request.path not in allowed_urls:
                return redirect('change_password')
        
        response = self.get_response(request)
        return response