from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from catechesis.models import SacramentRequest
from member.models import Member, Community, Committee, Ministry, Zone
from tithe.models import TithePayment
from events.models import Event

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
    
    # Basic counts
    member_count = Member.objects.count()
    ministry_count = Ministry.objects.count()
    community_count = Community.objects.count()
    committee_count = Committee.objects.count()
    zone_count = Zone.objects.count()
    
    # Member statistics breakdown
    active_members = Member.objects.filter(active=True).count()
    inactive_members = member_count - active_members
    
    # Members by category
    elders_count = Member.objects.filter(membership_category='elder', active=True).count()
    youth_count = Member.objects.filter(membership_category='youth', active=True).count()
    children_count = Member.objects.filter(membership_category='child', active=True).count()
    
    # Financial overview - This month's collections
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month_tithe = TithePayment.objects.filter(
        date__gte=current_month_start
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    this_month_payments = TithePayment.objects.filter(
        date__gte=current_month_start
    ).count()
    
    # Today's collections
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_tithe = TithePayment.objects.filter(
        date__gte=today_start
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Pending sacrament requests
    pending_sacraments = SacramentRequest.objects.filter(
        status='pending'
    ).count()
    
    # Recent activities (enhanced to include different types)
    recent_members = Member.objects.order_by('-id')[:3]
    recent_payments = TithePayment.objects.order_by('-date')[:3]
    recent_sacraments = SacramentRequest.objects.order_by('-created_at')[:3]
    
    # Combine recent activities
    recent_activities = []
    for member in recent_members:
        recent_activities.append({
            'type': 'member',
            'icon': 'fa-user-plus',
            'color': '#667eea',
            'text': f'{member.name} was added to the database',
            'time': timedelta(0),  # Most recent
            'time_display': 'Just now',
            'badge': 'New'
        })
    
    for payment in recent_payments:
        time_diff = timezone.now() - payment.date if payment.date else timedelta(days=1000)
        recent_activities.append({
            'type': 'payment',
            'icon': 'fa-hand-holding-dollar',
            'color': '#10b981',
            'text': f'Tithe payment of {payment.amount} recorded',
            'time': time_diff,
            'time_display': f'{time_diff.days} days ago' if time_diff.days > 0 else 'Just now',
            'badge': 'Payment'
        })
    
    for sacrament in recent_sacraments:
        time_diff = timezone.now() - sacrament.created_at if sacrament.created_at else timedelta(days=1000)
        recent_activities.append({
            'type': 'sacrament',
            'icon': 'fa-cross',
            'color': '#f59e0b',
            'text': f'{sacrament.get_sacrament_display()} request by {sacrament.member if sacrament.member else "Unknown"}',
            'time': time_diff,
            'time_display': f'{time_diff.days} days ago' if time_diff.days > 0 else 'Just now',
            'badge': 'Request'
        })
    
    # Sort by time and take top 5
    recent_activities.sort(key=lambda x: x['time'] or timedelta(days=1000))
    recent_activities = recent_activities[:5]
    
    # Upcoming events (next 5)
    upcoming_events = Event.objects.filter(
        start_date__gte=now.date(),
        status='PUBLISHED'
    ).order_by('start_date')[:5]
    
    # Today's events
    today_events = Event.objects.filter(
        start_date=now.date(),
        status='PUBLISHED'
    )
    
    # Zone performance (top 3 by member count)
    top_zones = []
    for zone in Zone.objects.all()[:3]:
        zone_members = zone.get_total_members()
        zone_communities = zone.get_communities_count()
        top_zones.append({
            'name': zone.name,
            'members': zone_members,
            'communities': zone_communities
        })
    
    # Quick alerts
    alerts = []
    if inactive_members > member_count * 0.1:  # More than 10% inactive
        alerts.append({
            'type': 'warning',
            'icon': 'fa-user-slash',
            'message': f'{inactive_members} inactive members ({round(inactive_members/member_count*100)}%)'
        })
    
    if pending_sacraments > 5:
        alerts.append({
            'type': 'info',
            'icon': 'fa-clock',
            'message': f'{pending_sacraments} sacrament requests pending approval'
        })
    
    if this_month_tithe == 0 and now.day > 5:
        alerts.append({
            'type': 'danger',
            'icon': 'fa-exclamation-triangle',
            'message': 'No tithe collections recorded this month'
        })

    context = {
        'member_count': member_count,
        'ministry_count': ministry_count,
        'community_count': community_count,
        'committee_count': committee_count,
        'zone_count': zone_count,
        
        # Member statistics
        'active_members': active_members,
        'inactive_members': inactive_members,
        'elders_count': elders_count,
        'youth_count': youth_count,
        'children_count': children_count,
        
        # Financial overview
        'this_month_tithe': this_month_tithe,
        'this_month_payments': this_month_payments,
        'today_tithe': today_tithe,
        
        # Pending items
        'pending_sacraments': pending_sacraments,
        
        # Activities and events
        'recent_activities': recent_activities,
        'upcoming_events': upcoming_events,
        'today_events': today_events,
        
        # Zone performance
        'top_zones': top_zones,
        
        # Alerts
        'alerts': alerts,
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