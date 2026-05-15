from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .models import EventPledge, PledgePayment, Payroll
from notifications.models import Notification, UserNotification
from notifications.services import NotificationService
from users.models import User
import logging

logger = logging.getLogger(__name__)


def get_priest_emails():
    """Get list of priest emails for notifications"""
    priests = User.objects.filter(roles='priest', is_active=True).exclude(email__isnull=True).exclude(email='')
    return [p.email for p in priests]


def notify_priests_payroll_submitted(payroll):
    """Send email notification to priests when payroll is submitted for verification"""
    priest_emails = get_priest_emails()
    if not priest_emails:
        logger.warning("No priest emails found for payroll notification")
        return
    
    employee = payroll.employee
    submitted_by = payroll.submitted_by
    
    subject = f"Payroll Verification Required: {employee.name} - {payroll.pay_period_start.strftime('%B %Y')}"
    
    message = (
        f"Dear Father,\n\n"
        f"A payroll has been submitted for your verification:\n\n"
        f"Employee: {employee.name}\n"
        f"Position: {employee.position}\n"
        f"Pay Period: {payroll.pay_period_start.strftime('%B %d, %Y')} - {payroll.pay_period_end.strftime('%B %d, %Y')}\n"
        f"Basic Salary: TZS {payroll.basic_salary:,.2f}\n"
        f"Gross Salary: TZS {payroll.gross_salary:,.2f}\n"
        f"Net Salary: TZS {payroll.net_salary:,.2f}\n"
        f"Submitted By: {submitted_by.get_full_name() or submitted_by.username}\n"
        f"Submitted At: {payroll.submitted_for_verification_at.strftime('%B %d, %Y at %I:%M %p')}\n\n"
        f"Please review and verify this payroll at your earliest convenience.\n\n"
        f"View payroll: {getattr(settings, 'SITE_URL', '')}/finance/payrolls/?status=PENDING_VERIFICATION\n\n"
        f"God bless,\nChrist The King Parish System"
    )
    
    try:
        notification_service = NotificationService()
        for email in priest_emails:
            notification_service.send_email(
                to=email,
                subject=subject,
                message=message,
                template='finance/priest_payroll_notification_email.html',
                context={
                    'payroll': payroll,
                    'employee': employee,
                    'submitted_by': submitted_by,
                    'site_url': getattr(settings, 'SITE_URL', ''),
                }
            )
        logger.info(f"Priest notification sent for payroll {payroll.id}")
    except Exception as e:
        logger.error(f"Failed to send priest payroll notification: {str(e)}")


@receiver(post_save, sender=Payroll)
def notify_payroll_submitted_for_verification(sender, instance, created, **kwargs):
    """Send notification to priests when payroll is submitted for verification"""
    # Only notify when status changes to PENDING_VERIFICATION
    if instance.status == 'PENDING_VERIFICATION' and instance.submitted_for_verification:
        notify_priests_payroll_submitted(instance)


@receiver(post_save, sender=EventPledge)
def send_pledge_assignment_notification(sender, instance, created, **kwargs):
    """
    Send notification when a user is assigned to a pledge.
    This includes:
    - SMS notification
    - Email notification
    - Live in-app notification
    """
    if not created:
        return  # Only notify on new pledge creation
    
    try:
        # Get the user's contact information
        pledge = instance
        member = pledge.member
        
        if not member:
            logger.info(f"External pledger {pledge.external_name} - no user notification needed")
            return
        
        # Try to find the user associated with this member
        user = None
        try:
            # Check if member has a user account
            user = User.objects.filter(
                church_member__member=member,
                church_member__is_portal_active=True
            ).first()
        except Exception as e:
            logger.warning(f"Could not find user for member {member}: {e}")
        
        # Create the notification message
        event_title = pledge.event.title if pledge.event else "Church Event"
        promised_amount = pledge.promised_amount
        due_date = pledge.due_date.strftime('%d %B %Y') if pledge.due_date else "soon"
        
        title = f"Upangaji wa Ahadi Mpya: {event_title}"
        message = (
                f"Ndugu {pledge.pledger_name}, umepangiwa ahadi ya TZS {promised_amount:,.2f} " \
                f"kwa ajili ya {event_title}. Tafadhali kamilisha ifikapo {due_date}. " \
                f"Asante kwa mchango wako!"

        )
        
        # 1. Send SMS notification
        try:
            from tithe.sms_api.africastalking import SMS
            phone = pledge.pledger_phone
            if phone:
                sms_message = (
                    f"Ndugu {pledge.pledger_name}, umepangiwa ahadi ya TZS {promised_amount:,.2f} " \
                    f"kwa ajili ya {event_title}. Tafadhali kamilisha ifikapo {due_date}. " \
                    f"Asante kwa mchango wako!"

                )
                SMS.send_sms(phone, sms_message)
                logger.info(f"SMS sent to {phone} for pledge {pledge.id}")
        except Exception as e:
            logger.error(f"Failed to send SMS for pledge {pledge.id}: {e}")
        
        # 2. Create in-app notification for live delivery
        if user:
            try:
                # Create a notification record
                notification = Notification.objects.create(
                    title=title,
                    message=message,
                    recipient_type='MEMBER',
                    member=member,
                    target_audience='PORTAL_ONLY',
                    priority='normal',
                    send_sms=False,  # Already sent above
                    status='SENT',
                    sent_at=timezone.now()
                )
                
                # Create user notification for this specific user
                UserNotification.objects.create(
                    user=user,
                    notification=notification,
                    is_read=False
                )
                
                # Broadcast via WebSocket
                from notifications.utils import broadcast_notification
                broadcast_notification(notification)
                
                logger.info(f"Live notification created for user {user.username} - pledge {pledge.id}")
            except Exception as e:
                logger.error(f"Failed to create live notification: {e}")
        
        # 3. Send Email notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            if user and user.email:
                email_subject = f"New Pledge Assignment - {event_title}"
                email_body = f"""
Dear {pledge.pledger_name},

You have been assigned a new pledge for {event_title}.

Pledge Details:
- Amount: {promised_amount:,.2f} TZS
- Event: {event_title}
- Due Date: {due_date}
- Status: {pledge.get_status_display()}

Please log in to your portal to view and manage your pledge:
https://christtheking.space/portal/pledges/

Thank you for your generous support!

Blessings,
Kristo Mfalme Parish Team
"""
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
                logger.info(f"Email sent to {user.email} for pledge {pledge.id}")
        except Exception as e:
            logger.error(f"Failed to send email for pledge {pledge.id}: {e}")
            
    except Exception as e:
        logger.error(f"Error in pledge assignment notification: {e}")


@receiver(post_save, sender=PledgePayment)
def send_payment_confirmation_notification(sender, instance, created, **kwargs):
    """
    Send notification when a payment is made on a pledge.
    """
    if not created:
        return
    
    try:
        pledge = instance.pledge
        payment_amount = instance.amount
        member = pledge.member
        
        if not member:
            return
        
        # Calculate remaining
        total_paid = pledge.paid_amount
        remaining = pledge.remaining_amount
        
        # Get user
        user = User.objects.filter(
            church_member__member=member,
            church_member__is_portal_active=True
        ).first()
        
        event_title = pledge.event.title if pledge.event else "Church Event"
        
        # 1. Send SMS
        try:
            from tithe.sms_api.africastalking import SMS
            phone = pledge.pledger_phone
            if phone:
                sms_message = (
                    f"KRISTO MFALME: Asante! Malipo ya TZS {payment_amount:,.0f} yamepokelewa. " \
                    f"Jumla iliyolipwa: TZS {total_paid:,.0f}. " \
                    f"Baki: TZS {remaining:,.0f}. " \
                    f"Mungu akubariki!"
                )
                SMS.send_sms(phone, sms_message)
        except Exception as e:
            logger.error(f"SMS payment notification failed: {e}")
        
        # 2. Live notification
        if user and remaining > 0:
            try:
                title = "Pledge Payment Received"
                message = (
                    f"Asante kwa malipo yako ya TZS {payment_amount:,.2f}. " \
                    f"Umelipa jumla ya TZS {total_paid:,.2f} kati ya TZS {pledge.promised_amount:,.2f}. " \
                    f"Salio lililobaki: TZS {remaining:,.2f}."

                )
                
                notification = Notification.objects.create(
                    title=title,
                    message=message,
                    recipient_type='MEMBER',
                    member=member,
                    target_audience='PORTAL_ONLY',
                    priority='normal',
                    send_sms=False,
                    status='SENT',
                    sent_at=timezone.now()
                )
                
                UserNotification.objects.create(
                    user=user,
                    notification=notification,
                    is_read=False
                )
                
                from notifications.utils import broadcast_notification
                broadcast_notification(notification)
            except Exception as e:
                logger.error(f"Live payment notification failed: {e}")
        
        # 3. Email notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            if user and user.email:
                email_subject = "Pledge Payment Confirmation"
                email_body = f"""
Dear {pledge.pledger_name},

Thank you for your contribution!

Payment Details:
- Amount Paid: {payment_amount:,.2f} TZS
- Event: {event_title}
- Total Paid: {total_paid:,.2f} TZS
- Total Pledged: {pledge.promised_amount:,.2f} TZS
- Remaining Balance: {remaining:,.2f} TZS

{"Your pledge is now COMPLETE! Thank you for your generosity." if remaining <= 0 else f"Please complete your remaining balance of {remaining:,.2f} TZS by the due date."}

God bless you!

Kristo Mfalme Parish Team
"""
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
        except Exception as e:
            logger.error(f"Email payment notification failed: {e}")
            
    except Exception as e:
        logger.error(f"Error in payment notification: {e}")
