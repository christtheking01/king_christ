from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from catechesis.models import SacramentRequest
from member.models import Member, Community,Committee,Ministry

# Create your views here.
@login_required
def home(request):
    """Main dashboard - only accessible to staff/admin users"""
    # Check if user is staff or has church_member attribute (portal users should not see this)
    if not request.user.is_staff and not request.user.is_superuser:
        # Portal users or regular members should go to their portal
        if hasattr(request.user, 'church_member'):
            return redirect('portal_dashboard')
        # For other non-staff users (shouldn't happen with @login_required), logout and redirect to staff login
        from django.contrib.auth import logout
        logout(request)
        return redirect('login_user')
    
    # Total members in the system
    member_count = Member.objects.count()
    
    # Total number of unique Ministries, Communities, and Committees
    ministry_count = Ministry.objects.count()
    community_count = Community.objects.count()
    committee_count = Committee.objects.count()

    context = {
        'member_count': member_count,
        'ministry_count': ministry_count,
        'community_count': community_count,
        'committee_count': committee_count,
        'recent_activities':Member.objects.order_by('-id')[:5]

    }
    return render(request, 'index.html', context)


def home_redirect(request):
    """Redirect /home/ to appropriate page based on user type"""
    if request.user.is_authenticated:
        # Check if user is a church member (portal user)
        if hasattr(request.user, 'church_member'):
            return redirect('portal_dashboard')
    # Default to home page for staff or anonymous users
    return redirect('home')