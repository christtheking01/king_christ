from django.db.models import Q

def notification_context(request):
    """
    Context processor to add notification-related variables
    """
    context = {
        'unread_count': 0,
    }
    
    # Get unread notifications count for authenticated users
    if request.user.is_authenticated:
        try:
            from .models import Notification, NotificationReadStatus
            
            # Get IDs of notifications this user has already read
            read_notification_ids = NotificationReadStatus.objects.filter(
                user=request.user
            ).values_list('notification_id', flat=True)
            
            # Get unread notifications count
            unread_count = Notification.objects.filter(
                ~Q(id__in=read_notification_ids),
                status='SENT'
            ).count()
            
            context['unread_count'] = unread_count
            
        except Exception:
            # If there's any error, default to 0
            context['unread_count'] = 0
    
    return context
