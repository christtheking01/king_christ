from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Notification, NotificationLog
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