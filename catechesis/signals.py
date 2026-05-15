import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .models import SacramentRequest, CatechesisMember
from notifications.services import NotificationService
from users.models import User

logger = logging.getLogger(__name__)


def get_priest_emails():
    """Get list of priest emails for notifications"""
    priests = User.objects.filter(roles='priest', is_active=True).exclude(email__isnull=True).exclude(email='')
    return [p.email for p in priests]


def notify_priests_new_request(sacrament_request):
    """Send email notification to priests when new sacrament request is created"""
    priest_emails = get_priest_emails()
    if not priest_emails:
        logger.warning("No priest emails found for notification")
        return
    
    member = sacrament_request.member
    sacrament_name = sacrament_request.get_sacrament_display()
    
    subject = f"New Sacrament Request: {sacrament_name} - {member.first_name} {member.last_name}"
    
    message = (
        f"Dear Father,\n\n"
        f"A new sacrament request requires your attention:\n\n"
        f"Sacrament: {sacrament_name}\n"
        f"Member: {member.first_name} {member.last_name}\n"
        f"Phone: {member.phone or 'N/A'}\n"
        f"Email: {member.email or 'N/A'}\n"
        f"Submitted: {sacrament_request.request_date.strftime('%B %d, %Y at %I:%M %p')}\n\n"
        f"Please review and approve/reject this request at your earliest convenience.\n\n"
        f"View request: {settings.SITE_URL}/catechesis/pending-requests/\n\n"
        f"God bless,\nChrist The King Parish System"
    )
    
    try:
        notification_service = NotificationService()
        for email in priest_emails:
            notification_service.send_email(
                to=email,
                subject=subject,
                message=message,
                template='catechesis/priest_notification_email.html',
                context={
                    'member': member,
                    'request': sacrament_request,
                    'sacrament': sacrament_name,
                    'site_url': getattr(settings, 'SITE_URL', ''),
                }
            )
        logger.info(f"Priest notification sent for sacrament request {sacrament_request.id}")
    except Exception as e:
        logger.error(f"Failed to send priest notification: {str(e)}")


@receiver(post_save, sender=SacramentRequest)
def send_sacrament_notification(sender, instance, created, **kwargs):
    """Send SMS/email notification when sacrament request status changes"""
    
    # Only send if explicitly enabled in settings
    if not getattr(settings, 'SEND_SACRAMENT_NOTIFICATIONS', True):
        return
    
    member = instance.member
    sacrament_name = instance.get_sacrament_display()
    
    # Determine message based on status
    if instance.status == 'approved' and instance.scheduled_date:
        message = (
            f"Dear {member.first_name}, your {sacrament_name} request has been APPROVED. "
            f"Scheduled for: {instance.scheduled_date.strftime('%B %d, %Y')}. "
            f"Please arrive 30 minutes early. God bless!"
        )
    elif instance.status == 'rejected':
        message = (
            f"Dear {member.first_name}, your {sacrament_name} request requires additional review. "
            f"Please contact the parish office."
        )
    elif instance.status == 'scheduled':
        message = (
            f"Dear {member.first_name}, your {sacrament_name} is scheduled for "
            f"{instance.scheduled_date.strftime('%B %d, %Y')}. Please arrive 30 minutes early."
        )
    elif instance.status == 'completed':
        message = (
            f"Dear {member.first_name}, congratulations on completing your {sacrament_name}! "
            f"May God continue to bless you on your faith journey."
        )
    elif created and instance.status == 'pending':
        message = (
            f"Dear {member.first_name}, your {sacrament_name} request has been received "
            f"and is pending review. We will notify you once approved."
        )
        # Notify priests about new request
        notify_priests_new_request(instance)
    else:
        return  # Don't send for other status changes
    
    # Send SMS if phone available
    if member.phone:
        try:
            notification_service = NotificationService()
            success = notification_service.send_sms(member.phone, message)
            
            if success:
                instance.sms_sent = True
                instance.sms_sent_at = timezone.now()
                instance.save(update_fields=['sms_sent', 'sms_sent_at'])
                logger.info(f"SMS sent to {member.phone} for sacrament {instance.status}")
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {str(e)}")
    
    # Send email if email available
    if member.email:
        try:
            subject = f"Sacrament Request Update - {sacrament_name}"
            notification_service = NotificationService()
            notification_service.send_email(
                to=member.email,
                subject=subject,
                message=message,
                template='catechesis/sacrament_notification_email.html',
                context={
                    'member': member,
                    'request': instance,
                    'sacrament': instance.get_sacrament_display(),
                    'status': instance.status,
                }
            )
            
            instance.notification_sent = True
            instance.notification_sent_at = timezone.now()
            instance.save(update_fields=['notification_sent', 'notification_sent_at'])
            logger.info(f"Email sent to {member.email} for sacrament {instance.status}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")


@receiver(post_save, sender=CatechesisMember)
def send_welcome_notification(sender, instance, created, **kwargs):
    """Send welcome SMS/email when new member registers"""
    
    if not created:
        return
    
    if not getattr(settings, 'SEND_SACRAMENT_NOTIFICATIONS', True):
        return
    
    message = (
        f"Welcome to Christ The King Parish, {instance.first_name}! "
        f"You are now registered for catechesis. "
        f"We look forward to supporting your faith journey."
    )
    
    # Send SMS
    if instance.phone:
        try:
            notification_service = NotificationService()
            notification_service.send_sms(instance.phone, message)
            logger.info(f"Welcome SMS sent to {instance.phone}")
        except Exception as e:
            logger.error(f"Failed to send welcome SMS: {str(e)}")
    
    # Send Email
    if instance.email:
        try:
            notification_service = NotificationService()
            notification_service.send_email(
                to=instance.email,
                subject="Welcome to Christ The King Parish Catechesis",
                message=message,
                template='catechesis/welcome_email.html',
                context={'member': instance}
            )
            logger.info(f"Welcome email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
