from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import json
from .models import Notification, NotificationLog, NotificationReadStatus, UserNotification,DeliveryReport,IncomingSMS
from .forms import NotificationForm, TitheReminderForm, PledgeReminderForm
from .services import NotificationService
from .utils import get_user_notification_count
from member.models import Member
from tithe.models import TithePayment
from finance.models import EventPledge, PledgePayment
import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
@login_required
def notification_list(request):
    """List all notifications"""
    notifications = Notification.objects.all().distinct().order_by('-created_at')
    
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
            
            # Send notification via SMS if enabled, otherwise mark as SENT for in-app
            # First, calculate total recipients
            recipients = notification.get_recipients()
            if hasattr(recipients, 'count') and hasattr(recipients, 'model'):
                # Django QuerySet
                notification.total_recipients = recipients.count()
            else:
                # Python list
                notification.total_recipients = len(recipients) if recipients else 0
            
            # Save the total_recipients count
            notification.save(update_fields=['total_recipients'])
            
            # Create user notifications for in-app display (regardless of SMS setting)
            notification.create_user_notifications()
            
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
                # Mark as SENT for in-app notification (no SMS)
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()
                messages.success(request, 'Notification created and sent to users (in-app only)')
            
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
    read_status = notification.read_status.select_related('user').all()[:50]  # Who read it
    
    context = {
        'notification': notification,
        'logs': logs,
        'recipients': notification.get_recipients()[:50],
        'read_status': read_status,
        'read_count': notification.read_status.count()
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
    """API endpoint for unread notifications - uses UserNotification model"""
    
    # Get unread UserNotifications for the current user
    user_notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).select_related('notification').order_by('-sent_at')[:10]
    
    data = []
    for un in user_notifications:
        data.append({
            'id': un.id,
            'notification_id': un.notification.id,
            'title': un.notification.title,
            'message': un.notification.message,
            'created_at': un.sent_at.isoformat() if un.sent_at else un.notification.created_at.isoformat(),
            'type': _get_notification_type(un.notification),
            'read': un.is_read,
            'priority': un.notification.priority
        })
    
    # Get unread count
    unread_count = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count
    }, safe=False)

def _get_notification_type(notification):
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


@login_required
def notification_delete(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk)
    
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notification deleted successfully.')
        return redirect('notification_list')
    
    # GET request - show confirmation page
    context = {
        'notification': notification,
    }
    return render(request, 'notifications/notification_confirm_delete.html', context)


# =============================================================================
# USER NOTIFICATION VIEWS (for individual users)
# =============================================================================

@login_required
def my_notifications(request):
    """View for users to see their own notifications"""
    # Filter by read status
    filter_type = request.GET.get('filter', 'all')
    
    user_notifications = UserNotification.objects.filter(
        user=request.user
    ).select_related('notification').order_by('-sent_at')
    
    if filter_type == 'unread':
        user_notifications = user_notifications.filter(is_read=False)
    elif filter_type == 'read':
        user_notifications = user_notifications.filter(is_read=True)
    
    # Pagination
    paginator = Paginator(user_notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count
    unread_count = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    # Check if user is a church member (portal user) or staff
    is_church_member = hasattr(request.user, 'church_member')
    
    # Set base template based on user type
    base_template = 'portal/base_portal.html' if is_church_member else 'base.html'
    
    context = {
        'page_obj': page_obj,
        'user_notifications': page_obj,
        'unread_count': unread_count,
        'filter_type': filter_type,
        'is_church_member': is_church_member,
        'base_template': base_template,
    }
    
    return render(request, 'notifications/my_notifications.html', context)


@login_required
def user_notification_detail(request, pk):
    """View a specific notification for a user and mark it as read"""
    user_notification = get_object_or_404(
        UserNotification,
        pk=pk,
        user=request.user
    )
    
    # Mark as read
    if not user_notification.is_read:
        user_notification.mark_as_read()
    
    # Check if user is a church member (portal user) or staff
    is_church_member = hasattr(request.user, 'church_member')
    base_template = 'portal/base_portal.html' if is_church_member else 'base.html'
    
    context = {
        'user_notification': user_notification,
        'notification': user_notification.notification,
        'is_church_member': is_church_member,
        'base_template': base_template,
    }
    return render(request, 'notifications/user_notification_detail.html', context)


@login_required
def user_notification_mark_read(request, pk):
    """Mark a specific user notification as read via API"""
    if request.method == 'POST':
        try:
            user_notification = get_object_or_404(
                UserNotification,
                pk=pk,
                user=request.user
            )
            user_notification.mark_as_read()
            
            # Get updated unread count
            unread_count = UserNotification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
            
            return JsonResponse({
                'success': True,
                'unread_count': unread_count
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def user_notification_mark_all_read(request):
    """Mark all user notifications as read via API"""
    if request.method == 'POST':
        try:
            UserNotification.objects.filter(
                user=request.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            return JsonResponse({
                'success': True,
                'unread_count': 0
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def user_notifications_api(request):
    """API endpoint for user's notifications with filtering"""
    limit = int(request.GET.get('limit', 10))
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
    
    user_notifications = UserNotification.objects.filter(
        user=request.user
    ).select_related('notification')
    
    if unread_only:
        user_notifications = user_notifications.filter(is_read=False)
    
    user_notifications = user_notifications.order_by('-sent_at')[:limit]
    
    data = []
    for un in user_notifications:
        data.append({
            'id': un.id,
            'notification_id': un.notification.id,
            'title': un.notification.title,
            'message': un.notification.message,
            'priority': un.notification.priority if hasattr(un.notification, 'priority') else 'normal',
            'is_read': un.is_read,
            'created_at': un.notification.created_at.isoformat(),
            'sent_at': un.sent_at.isoformat(),
            'type': _get_notification_type(un.notification),
        })
    
    # Get unread count
    unread_count = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count
    })


@login_required
def send_tithe_reminder(request):
    """Send tithe reminders to members who haven't paid this month"""
    # Get stats for preview
    current_month = timezone.now().strftime('%Y-%m')
    
    # Get all members who pay tithe
    tithe_payers = Member.objects.filter(pays_tithe=True, active=True)
    total_tithe_payers = tithe_payers.count()
    
    # Get those who have paid this month
    year, month = current_month.split('-')
    paid_this_month = TithePayment.objects.filter(
        date__year=year,
        date__month=month,
        name__in=tithe_payers
    ).values('name').distinct().count()
    
    pending_reminders = total_tithe_payers - paid_this_month
    
    if request.method == 'POST':
        form = TitheReminderForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.recipient_type = 'TITHE_PAYERS'
            
            # Get delivery method
            delivery_method = form.cleaned_data.get('delivery_method', 'both')
            
            # Set SMS flag based on delivery method
            notification.send_sms = delivery_method in ['both', 'sms_only']
            notification.save()
            
            # Get members who haven't paid for the selected month
            selected_month = form.cleaned_data.get('month', current_month)
            year, month = selected_month.split('-')
            
            paid_members = TithePayment.objects.filter(
                date__year=year,
                date__month=month,
                name__in=tithe_payers
            ).values_list('name_id', flat=True)
            
            target_members = tithe_payers.exclude(id__in=paid_members)
            notification.total_recipients = target_members.count()
            notification.save(update_fields=['total_recipients'])
            
            # Handle different delivery methods
            if delivery_method == 'portal_only':
                # Portal only - create user notifications but no SMS
                notification.create_user_notifications()
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()
                messages.success(request, f"Tithe reminders sent to {notification.total_recipients} members (portal only)")
                
            elif delivery_method == 'sms_only':
                # SMS only - send SMS but don't create portal notifications
                service = NotificationService()
                result = service.send_notification(notification.id)
                
                if result['success']:
                    messages.success(
                        request,
                        f"Tithe reminders sent via SMS! {result.get('sent', 0)} successful, "
                        f"{result.get('failed', 0)} failed"
                    )
                else:
                    messages.error(request, f"Error: {result.get('error')}")
                    
            else:  # both
                # Both SMS and portal
                notification.create_user_notifications()
                
                service = NotificationService()
                result = service.send_notification(notification.id)
                
                if result['success']:
                    messages.success(
                        request,
                        f"Tithe reminders sent! {result.get('sent', 0)} SMS successful, "
                        f"{result.get('failed', 0)} SMS failed, {notification.total_recipients} portal notifications"
                    )
                else:
                    messages.error(request, f"Error: {result.get('error')}")
            
            return redirect('notification_detail', pk=notification.id)
    else:
        # Pre-populate with default message
        current_month_name = timezone.now().strftime('%B %Y')
        initial_data = {
            'title': f'Tithe Reminder - {current_month_name}',
            'message': f'Dear {{member_name}}, this is a friendly reminder to submit your tithe for {current_month_name}. Thank you for your faithfulness!',
            'priority': 'normal',
            'delivery_method': 'both',
            'month': current_month
        }
        form = TitheReminderForm(initial=initial_data)
    
    context = {
        'form': form,
        'total_tithe_payers': total_tithe_payers,
        'paid_this_month': paid_this_month,
        'pending_reminders': pending_reminders,
    }
    return render(request, 'notifications/send_tithe_reminder.html', context)


@login_required
def send_pledge_reminder(request):
    """Send pledge reminders to members with active pledges"""
    # Get stats for preview
    total_pledgers = EventPledge.objects.filter(
        status__in=['PENDING', 'PARTIAL']
    ).values('member').distinct().count()
    
    pending_pledges = EventPledge.objects.filter(status='PENDING').count()
    partial_pledges = EventPledge.objects.filter(status='PARTIAL').count()
    
    if request.method == 'POST':
        form = PledgeReminderForm(request.POST)
        include_pending = request.POST.get('include_pending') == 'true'
        include_partial = request.POST.get('include_partial') == 'true'
        
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.recipient_type = 'PLEDGERS'
            notification.send_sms = form.cleaned_data.get('send_sms', True)
            notification.save()
            
            # Get pledges based on filters
            status_filter = []
            if include_pending:
                status_filter.append('PENDING')
            if include_partial:
                status_filter.append('PARTIAL')
            
            target_pledges = EventPledge.objects.filter(status__in=status_filter)
            target_members = Member.objects.filter(
                id__in=target_pledges.values_list('member', flat=True).distinct()
            )
            
            notification.total_recipients = target_members.count()
            notification.save(update_fields=['total_recipients'])
            
            # Create user notifications
            notification.create_user_notifications()
            
            # Send SMS if enabled
            if notification.send_sms:
                service = NotificationService()
                result = service.send_notification(notification.id)
                
                if result['success']:
                    messages.success(
                        request,
                        f"Pledge reminders sent! {result.get('sent', 0)} successful, "
                        f"{result.get('failed', 0)} failed"
                    )
                else:
                    messages.error(request, f"Error: {result.get('error')}")
            else:
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()
                messages.success(request, f"Pledge reminders sent to {notification.total_recipients} members (in-app only)")
            
            return redirect('notification_detail', pk=notification.id)
    else:
        # Pre-populate with default message
        initial_data = {
            'title': 'Pledge Payment Reminder',
            'message': 'Dear {member_name}, this is a reminder about your pledge of {pledge_amount}. Amount paid so far: {amount_paid}. Balance remaining: {balance}. Thank you for your commitment!',
            'priority': 'normal',
            'send_sms': True,
            'include_pending': True,
            'include_partial': True
        }
        form = PledgeReminderForm(initial=initial_data)
    
    context = {
        'form': form,
        'total_pledgers': total_pledgers,
        'pending_pledges': pending_pledges,
        'partial_pledges': partial_pledges,
    }
    return render(request, 'notifications/send_pledge_reminder.html', context)


@login_required
def send_to_member(request):
    """Send notification to individual member - uses separate template"""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.recipient_type = 'MEMBER'
            
            # Ensure member is properly set
            if not notification.member and form.cleaned_data.get('member'):
                notification.member = form.cleaned_data['member']
            
            notification.save()
            
            # Calculate recipients
            recipients = notification.get_recipients()
            if hasattr(recipients, 'count') and hasattr(recipients, 'model'):
                notification.total_recipients = recipients.count()
            else:
                notification.total_recipients = len(recipients) if recipients else 0
            notification.save(update_fields=['total_recipients'])
            
            # Create user notifications
            notification.create_user_notifications()
            
            if notification.send_sms:
                service = NotificationService()
                result = service.send_notification(notification.id)
                
                if result['success']:
                    messages.success(
                        request,
                        f"Notification sent to {notification.member.name}! "
                        f"{result.get('sent', 0)} successful, {result.get('failed', 0)} failed"
                    )
                else:
                    messages.error(request, f"Error: {result.get('error')}")
            else:
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()
                messages.success(
                    request, 
                    f"Notification sent to {notification.member.name} (in-app only)"
                )
            
            return redirect('notification_detail', pk=notification.id)
    else:
        form = NotificationForm()
    
    context = {'form': form}
    return render(request, 'notifications/send_to_member.html', context)


@login_required
def send_to_custom(request):
    """Send notification to custom phone numbers - uses separate template"""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.recipient_type = 'CUSTOM_PHONES'
            notification.send_sms = True  # Always send SMS for custom numbers
            notification.save()
            
            # Calculate recipients from phone numbers
            phone_numbers = notification.get_phone_numbers()
            notification.total_recipients = len(phone_numbers) if phone_numbers else 0
            notification.save(update_fields=['total_recipients'])
            
            # Send via SMS only (no in-app for custom numbers)
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
            
            return redirect('notification_detail', pk=notification.id)
    else:
        form = NotificationForm()
    
    context = {'form': form}
    return render(request, 'notifications/send_to_custom.html', context)

import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def sms_incoming(request):
    """Handle incoming SMS from Africa's Talking"""
    try:
        # Validate required fields
        required_fields = ['from', 'to', 'text', 'date', 'id']
        for field in required_fields:
            if not request.POST.get(field):
                logger.warning(f"Missing required field: {field}")
                return HttpResponse(f"Missing {field}", status=400)
        
        from_number = request.POST.get('from', '')
        to_number   = request.POST.get('to', '')
        text        = request.POST.get('text', '')
        date        = request.POST.get('date', '')
        message_id  = request.POST.get('id', '')
        link_id     = request.POST.get('linkId', '')  # For SMS-linked USSD

        logger.info(f"Incoming SMS from {from_number}: {text}")

        # Check for duplicate messages
        if IncomingSMS.objects.filter(message_id=message_id).exists():
            logger.info(f"Duplicate message ignored: {message_id}")
            return HttpResponse("OK", status=200)

        # Save to database (recommended by Africa's Talking)
        incoming_sms = IncomingSMS.objects.create(
            from_number=from_number,
            to_number=to_number,
            text=text,
            date=date,
            message_id=message_id,
            link_id=link_id,
        )

        # TODO: Add business logic for processing incoming SMS
        # - Auto-replies
        # - Command processing
        # - Member lookup and response
        
        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"SMS incoming error: {e}")
        return HttpResponse("Error", status=500)


@csrf_exempt
@require_POST
def sms_delivery_report(request):
    """Handle SMS delivery reports from Africa's Talking"""
    try:
        # Validate required fields
        required_fields = ['phoneNumber', 'id', 'status']
        for field in required_fields:
            if not request.POST.get(field):
                logger.warning(f"Missing required field: {field}")
                return HttpResponse(f"Missing {field}", status=400)
        
        phone_number = request.POST.get('phoneNumber', '')
        message_id   = request.POST.get('id', '')
        status       = request.POST.get('status', '')  # e.g. Success, Failed
        network_code = request.POST.get('networkCode', '')
        failure_reason = request.POST.get('failureReason', '')  # if failed

        logger.info(f"Delivery report for {phone_number}: {status}")

        # Try to find the related notification log
        notification_log = None
        try:
            notification_log = NotificationLog.objects.filter(
                at_message_id=message_id,
                phone_number=phone_number
            ).first()
        except Exception as e:
            logger.warning(f"Could not find notification log for {message_id}: {e}")

        # Update or save delivery status
        delivery_report = DeliveryReport.objects.create(
            phone_number=phone_number,
            message_id=message_id,
            status=status,
            network_code=network_code,
            failure_reason=failure_reason,
            notification_log=notification_log
        )

        # Update the original notification log if found
        if notification_log:
            notification_log.status = status.upper()
            if failure_reason:
                notification_log.error_message = failure_reason
            notification_log.save(update_fields=['status', 'error_message'])
            
            # Update parent notification statistics
            notification = notification_log.notification
            if status.upper() == 'SUCCESS':
                notification.sms_sent_count += 1
            elif status.upper() == 'FAILED':
                notification.sms_failed_count += 1
            notification.save(update_fields=['sms_sent_count', 'sms_failed_count'])

        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"Delivery report error: {e}")
        return HttpResponse("Error", status=500)