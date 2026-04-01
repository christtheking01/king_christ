from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Notification, NotificationLog,NotificationReadStatus
from .forms import NotificationForm
from .services import NotificationService

@login_required
def notification_list(request):
    """List all notifications"""
    notifications = Notification.objects.all()
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_create(request):
    """Create a new notification"""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.save()
            
            # Send notification if send_sms is True
            if notification.send_sms:
                service = NotificationService()
                result = service.send_notification(notification.id)
                
                if result['success']:
                    messages.success(
                        request,
                        f"Notification sent! {result.get('sent', 0)} successful, "
                        f"{result.get('failed', 0)} failed"
                    )
                else:
                    messages.error(request, f"Error: {result.get('error')}")
            else:
                messages.success(request, 'Notification created successfully')
            
            return redirect('notification_detail', pk=notification.id)
    else:
        form = NotificationForm()
    
    context = {'form': form}
    return render(request, 'notifications/notification_form.html', context)


@login_required
def notification_detail(request, pk):
    """View notification details"""
    notification = get_object_or_404(Notification, pk=pk)
    logs = notification.logs.all()[:50]  # Limit to 50 logs
    
    context = {
        'notification': notification,
        'logs': logs,
        'recipients': notification.get_recipients()[:50]
    }
    return render(request, 'notifications/notification_detail.html', context)


@login_required
def notification_send(request, pk):
    """Manually send/resend a notification"""
    notification = get_object_or_404(Notification, pk=pk)
    
    if request.method == 'POST':
        service = NotificationService()
        result = service.send_notification(notification.id)
        
        if result['success']:
            messages.success(
                request,
                f"Notification sent! {result.get('sent', 0)} successful, "
                f"{result.get('failed', 0)} failed"
            )
        else:
            messages.error(request, f"Error: {result.get('error')}")
    
    return redirect('notification_detail', pk=pk)


@login_required
def notification_preview(request, pk):
    """Preview notification recipients"""
    notification = get_object_or_404(Notification, pk=pk)
    recipients = notification.get_recipients()
    phone_numbers = notification.get_phone_numbers()
    
    data = {
        'total_recipients': recipients.count(),
        'valid_phones': len(phone_numbers),
        'recipients': [
            {
                'name': r.name,
                'phone': str(r.telephone) if r.telephone else 'N/A'
            }
            for r in recipients[:20]  # Limit preview
        ]
    }
    
    return JsonResponse(data)

@login_required
def unread_notifications_api(request):
    """API endpoint for unread notifications"""
    
    # Get IDs of notifications this user has already read
    read_notification_ids = NotificationReadStatus.objects.filter(
        user=request.user
    ).values_list('notification_id', flat=True)
    
    # Get unread notifications (not in read_notification_ids)
    # Adjust based on what users should see - maybe all recent notifications?
    notifications = Notification.objects.filter(
        ~Q(id__in=read_notification_ids),  # Not read by this user
        status='SENT'  # Only show sent notifications
    ).order_by('-created_at')[:10]
    
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
            'type': _get_notification_type(notification),  # Determine type based on recipient_type or other criteria
            'read': False
        })
    
    # Get unread count
    unread_count = Notification.objects.filter(
        ~Q(id__in=read_notification_ids),
        status='SENT'
    ).count()
    
    return JsonResponse(data, safe=False)

def _get_notification_type(self, notification):
    """Helper to determine notification type"""
    # You can customize this based on your needs
    type_map = {
        'ALL': 'info',
        'MEMBER': 'info',
        'MINISTRY': 'success',
        'COMMUNITY': 'warning',
        'Staff': 'primary'
    }
    return type_map.get(notification.recipient_type, 'info')


@login_required
@csrf_exempt
def mark_notification_read(request, notification_id):
    """Mark a notification as read by the current user"""
    if request.method == 'POST':
        try:
            if not notification_id:
                return JsonResponse({'error': 'Notification ID required'}, status=400)
            
            # Create read status
            read_status, created = NotificationReadStatus.objects.get_or_create(
                notification_id=notification_id,
                user=request.user,
                defaults={'is_read': True}
            )
            
            # Get updated unread count
            read_ids = NotificationReadStatus.objects.filter(
                user=request.user
            ).values_list('notification_id', flat=True)
            
            unread_count = Notification.objects.filter(
                ~Q(id__in=read_ids),
                status='SENT'
            ).count()
            
            return JsonResponse({
                'success': True,
                'unread_count': unread_count
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def mark_all_read(request):
    """Mark all notifications as read by the current user"""
    if request.method == 'POST':
        try:
            # Get all sent notifications
            notifications = Notification.objects.filter(status='SENT')
            
            # Create read status for all
            for notification in notifications:
                NotificationReadStatus.objects.get_or_create(
                    notification=notification,
                    user=request.user,
                    defaults={'is_read': True}
                )
            
            return JsonResponse({
                'success': True,
                'unread_count': 0
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)