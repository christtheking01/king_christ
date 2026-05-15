import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .models import EventRegistration, Event, EventReminder
from notifications.services import NotificationService
from notifications.models import Notification, UserNotification
from users.models import User

logger = logging.getLogger(__name__)


def format_phone_number(phone):
    """Format phone number to international format"""
    if not phone:
        return None
    
    import re
    cleaned = re.sub(r'\D', '', str(phone))
    
    if cleaned.startswith('0'):
        return '+255' + cleaned[1:]
    elif cleaned.startswith('255'):
        return '+' + cleaned
    elif not cleaned.startswith('+') and len(cleaned) in [11, 12, 13]:
        return '+' + cleaned
    return phone


@receiver(post_save, sender=EventRegistration)
def send_event_registration_sms(sender, instance, created, **kwargs):
    """Send SMS confirmation when someone registers for an event"""
    
    # Only send for new registrations and if SMS is enabled
    if not created or not getattr(settings, 'SEND_SMS_ENABLED', False):
        return
    
    # Don't send SMS if already sent
    if instance.sms_sent:
        return
    
    try:
        event = instance.event
        phone_number = format_phone_number(instance.phone)
        
        if not phone_number:
            logger.warning(f"No valid phone number for registration {instance.id}")
            return
        
        # Create SMS message
        event_date = event.start_date.strftime('%d/%m/%Y')
        event_time = event.start_time.strftime('%I:%M %p') if event.start_time else ''
        location = event.location.name if event.location else event.location_details or 'TBD'
        
        message = (
            f"KRISTO MFALME: Karibu {instance.first_name}! Umeshajiliwa kwa matukio "
            f"'{event.title}' tarehe {event_date} {event_time} eneo la {location}. "
            f"Tunakutegemea. Mungu akubariki!"
        )
        
        # Send SMS using notification service
        notification_service = NotificationService()
        result = notification_service.at_service.send_sms([phone_number], message)
        
        # Update registration with SMS status
        if result.get('success'):
            instance.sms_sent = True
            instance.sms_sent_at = timezone.now()
            
            # Extract message ID from response
            response_data = result.get('response', {})
            sms_recipients = response_data.get('SMSMessageData', {}).get('Recipients', [])
            if sms_recipients:
                instance.sms_message_id = sms_recipients[0].get('messageId')
            
            logger.info(f"Registration SMS sent to {phone_number} for event {event.title}")
        else:
            instance.sms_failure_count += 1
            instance.last_sms_error = result.get('error', 'Unknown error')
            logger.error(f"Failed to send registration SMS: {result.get('error')}")
        
        instance.save(update_fields=[
            'sms_sent', 'sms_sent_at', 'sms_message_id', 
            'sms_failure_count', 'last_sms_error'
        ])
        
        # Also create in-app notification if user has account
        if instance.user:
            try:
                notification = Notification.objects.create(
                    title=f"Event Registration Confirmed: {event.title}",
                    message=(
                        f"You have successfully registered for '{event.title}' on "
                        f"{event_date} at {location}."
                    ),
                    recipient_type='MEMBER',
                    target_audience='PORTAL_ONLY',
                    priority='normal',
                    send_sms=False,
                    status='SENT',
                    sent_at=timezone.now()
                )
                
                UserNotification.objects.create(
                    user=instance.user,
                    notification=notification,
                    is_read=False
                )
                
                # Broadcast via WebSocket
                from notifications.utils import broadcast_notification
                broadcast_notification(notification)
                
            except Exception as e:
                logger.error(f"Failed to create in-app notification: {e}")
                
    except Exception as e:
        logger.error(f"Error sending registration SMS for {instance.id}: {str(e)}", exc_info=True)


@receiver(pre_save, sender=Event)
def handle_event_cancellation(sender, instance, **kwargs):
    """Send SMS notifications when event is cancelled"""
    
    # Check if this is an update and status changed to CANCELLED
    if instance.pk:
        try:
            old_instance = Event.objects.get(pk=instance.pk)
            if old_instance.status != 'CANCELLED' and instance.status == 'CANCELLED':
                # Event is being cancelled
                send_event_cancellation_notifications(instance)
        except Event.DoesNotExist:
            pass


def send_event_cancellation_notifications(event):
    """Send SMS to all registered attendees when event is cancelled"""
    
    if not getattr(settings, 'SEND_SMS_ENABLED', False):
        return
    
    try:
        registrations = event.registrations.filter(
            status__in=['PENDING', 'CONFIRMED']
        ).exclude(phone__isnull=True).exclude(phone='')
        
        message = (
            f"KRISTO MFALME: Tukahatashauri! Matukio '{event.title}' yameghairiwa. "
            f"Tutaendelea kukuarifu kwa matukio haya. Samahani kwa usumbufu."
        )
        
        notification_service = NotificationService()
        
        for registration in registrations:
            phone_number = format_phone_number(registration.phone)
            if not phone_number:
                continue
                
            try:
                result = notification_service.at_service.send_sms([phone_number], message)
                
                if result.get('success'):
                    logger.info(f"Cancellation SMS sent to {phone_number} for event {event.title}")
                else:
                    logger.error(f"Failed to send cancellation SMS to {phone_number}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error sending cancellation SMS to {phone_number}: {e}")
        
        # Also create in-app notifications
        for registration in registrations.filter(user__isnull=False):
            try:
                notification = Notification.objects.create(
                    title=f"Event Cancelled: {event.title}",
                    message=f"The event '{event.title}' has been cancelled. We apologize for any inconvenience.",
                    recipient_type='MEMBER',
                    target_audience='PORTAL_ONLY',
                    priority='high',
                    send_sms=False,
                    status='SENT',
                    sent_at=timezone.now()
                )
                
                UserNotification.objects.create(
                    user=registration.user,
                    notification=notification,
                    is_read=False
                )
                
                from notifications.utils import broadcast_notification
                broadcast_notification(notification)
                
            except Exception as e:
                logger.error(f"Failed to create cancellation notification: {e}")
                
    except Exception as e:
        logger.error(f"Error in event cancellation notifications: {str(e)}", exc_info=True)


def send_event_reminder_sms(event, registration):
    """Send reminder SMS for an event"""
    
    if not getattr(settings, 'SEND_SMS_ENABLED', False):
        return False
    
    try:
        phone_number = format_phone_number(registration.phone)
        if not phone_number:
            return False
        
        event_date = event.start_date.strftime('%d/%m/%Y')
        event_time = event.start_time.strftime('%I:%M %p') if event.start_time else ''
        location = event.location.name if event.location else event.location_details or 'TBD'
        
        message = (
            f"KRISTO MFALME: Ukumbusho! Matukio '{event.title}' kesho "
            f"{event_date} {event_time} eneo la {location}. "
            f"Tunakutegemea. Mungu akubariki!"
        )
        
        notification_service = NotificationService()
        result = notification_service.at_service.send_sms([phone_number], message)
        
        if result.get('success'):
            logger.info(f"Reminder SMS sent to {phone_number} for event {event.title}")
            return True
        else:
            logger.error(f"Failed to send reminder SMS: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending reminder SMS: {e}")
        return False


@receiver(post_save, sender=EventReminder)
def handle_event_reminder(sender, instance, created, **kwargs):
    """Process event reminders when created"""
    
    # Only process when reminder is first created and not yet sent
    if not created or instance.sent:
        return
    
    # This will be handled by the management command that runs periodically
    # The command will check for unsent reminders and send them
    pass
