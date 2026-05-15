from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from users.models import UserProfile
from users.decorators import staff_required
from member.models import Member, Community, Committee, Ministry
from events.models import Event


def permission_denied_view(request, exception=None):
    """
    Custom 403 handler that shows a friendly permission denied page.
    This is shown when an authenticated user tries to access a page
    they don't have permission for - instead of redirecting to login.
    """
    context = {
        'user': request.user,
        'home_active': True,
    }
    return render(request, '403.html', context, status=403)


@staff_required
@login_required
def index(request):
    """Main dashboard with statistics. Church members are redirected to the portal."""
    # Check if user is a church member - redirect them to portal
    if hasattr(request.user, 'church_member') and request.user.church_member.is_portal_active:
        return redirect('portal_dashboard')
    
    try:
        profile = UserProfile.objects.get_or_create(user=request.user)
    except:
        profile = None

    # Get counts for dashboard
    context = {
        "home_active": "active",
        "profile": profile,
        "member_count": Member.objects.count(),
        "ministry_count": Ministry.objects.count(),
        "community_count": Community.objects.count(),
        "committee_count": Committee.objects.count(),
        "recent_activities": Member.objects.order_by('-id')[:5],
        "upcoming_events": Event.objects.filter(status='upcoming').order_by('start_date')[:5]
    }
    return render(request, "index.html", context)