from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from users.models import ChurchMember


def portal_login_required(view_func):
    """Decorator to check if user is logged in and has ChurchMember profile.
    Staff users without ChurchMember profile are redirected to staff area."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access the member portal.")
            return redirect('portal_login')
        
        # Check if user has a ChurchMember profile
        try:
            request.church_member = request.user.church_member
            if not request.church_member.is_portal_active:
                messages.error(request, "Your portal account is not active. Please verify your account or contact admin.")
                return redirect('portal_login')
        except ChurchMember.DoesNotExist:
            # User is staff (no ChurchMember profile) - redirect to staff area
            messages.info(request, "Redirecting to staff area.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Decorator to restrict views to staff/admin users only.
    Church members are redirected to the member portal."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('login_user')
        
        # Check if user is a church member - redirect them to portal
        if hasattr(request.user, 'church_member') and request.user.church_member.is_portal_active:
            messages.info(request, "Please use the member portal for church member access.")
            return redirect('portal_dashboard')
        
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('portal_dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper
