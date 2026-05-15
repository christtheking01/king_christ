from django.db.models import Q

def notification_context(request):
    """
    Context processor to add notification-related variables
    """
    context = {
        'unread_count': 0,
        'notifications': [],
    }
    
    # Get unread notifications count for authenticated users
    if request.user.is_authenticated:
        try:
            from .models import UserNotification
            
            # Get unread count from UserNotification model
            unread_count = UserNotification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
            
            context['unread_count'] = unread_count
            
            # Get recent unread notifications for dropdown
            recent_notifications = UserNotification.objects.filter(
                user=request.user,
                is_read=False
            ).select_related('notification').order_by('-sent_at')[:5]
            
            context['notifications'] = recent_notifications
            
        except Exception:
            # If there's any error, default to 0
            context['unread_count'] = 0
            context['notifications'] = []
    
    return context
