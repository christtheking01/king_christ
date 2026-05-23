"""
Management command to send pledge reminder notifications.

This command should be run periodically (e.g., daily) via cron or scheduled task.
Example cron entry:
0 9 * * * cd /path/to/project && python manage.py send_pledge_reminders

Usage:
    python manage.py send_pledge_reminders
    python manage.py send_pledge_reminders --dry-run
    python manage.py send_pledge_reminders --days-before-due 3
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from finance.models import EventPledge
from notifications.models import Notification, UserNotification
from users.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send reminder notifications for pending pledges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--days-before-due',
            type=int,
            default=7,
            help='Number of days before due date to send reminder (default: 7)',
        )
        parser.add_argument(
            '--overdue-only',
            action='store_true',
            help='Only send reminders for overdue pledges',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_before_due = options['days_before_due']
        overdue_only = options['overdue_only']
        
        today = timezone.now().date()
        reminder_date = today + timedelta(days=days_before_due)
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f"Checking for pledges due around {reminder_date}..."
            )
        )
        
        # Get pledges that need reminders
        if overdue_only:
            pledges = EventPledge.objects.filter(
                status__in=['PENDING', 'PARTIAL'],
                due_date__lt=today
            ).exclude(
                last_reminder_date=today  # Don't remind more than once per day
            )
        else:
            # Pledges due in X days or overdue
            pledges = EventPledge.objects.filter(
                status__in=['PENDING', 'PARTIAL'],
                due_date__lte=reminder_date
            ).exclude(
                last_reminder_date=today  # Don't remind more than once per day
            )
        
        total_sent = 0
        total_errors = 0
        
        for pledge in pledges:
            try:
                result = self.send_reminder(pledge, dry_run)
                if result:
                    total_sent += 1
            except Exception as e:
                total_errors += 1
                logger.error(f"Failed to send reminder for pledge {pledge.id}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"Failed pledge {pledge.id}: {e}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would send {total_sent} reminders"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sent {total_sent} reminders, {total_errors} errors"
                )
            )

    def send_reminder(self, pledge, dry_run=False):
        """Send a reminder for a specific pledge"""
        member = pledge.member
        if not member:
            return False
        
        # Calculate days until due
        today = timezone.now().date()
        days_until_due = (pledge.due_date - today).days if pledge.due_date else None
        
        # Determine urgency
        is_overdue = days_until_due is not None and days_until_due < 0
        is_urgent = days_until_due is not None and days_until_due <= 3
        
        event_title = pledge.event.title if pledge.event else "Church Event"
        remaining = pledge.remaining_amount
        
        if dry_run:
            self.stdout.write(
                f"Tungependa kumkumbusha {pledge.pledger_name} kuhusu {event_title} " \
                f"(Salio: TZS {remaining:,.2f}, zimebaki siku {days_until_due})"

            )
            return True
        
        # 1. Send SMS reminder
        try:
            from tithe.sms_api.africastalking import SMS
            phone = pledge.pledger_phone
            if phone:
                if is_overdue:
                    sms_message = (
                        f"Mpendwa, tunakukumbusha kuhusu ahadi yako "
                        f"ya TZS {remaining:,.0f} kwa ajili ya {event_title} ambayo imepitiliza muda. "
                        f"Tafadhali kamilisha wakati unapoweza. Tunakushukuru kwa moyo wako wa kutoa. Mungu akubariki."

                    )
                elif is_urgent:
                    sms_message = (
                        f" Mpendwa, ahadi yako ya TZS {remaining:,.0f} "
                        f"kwa ajili ya {event_title} inatakiwa kukamilika baada ya siku {days_until_due}. "
                        f"Tunathamini mchango wako. Mungu akubariki."

                    )
                else:
                    sms_message = (
                        f"Mpendwa, tunakukaribisha kukamilisha ahadi yako "
                        f"ya TZS {remaining:,.0f} kwa ajili ya {event_title} kufikia {pledge.due_date.strftime('%d %b %Y')}. "
                        f"Ushirika wako ni muhimu sana. Tunakushukuru. Mungu akubariki."

                    )
                
                SMS.send_sms(phone, sms_message)
                logger.info(f"SMS reminder sent to {phone} for pledge {pledge.id}")
        except Exception as e:
            logger.error(f"SMS reminder failed for pledge {pledge.id}: {e}")
        
        # 2. Send live in-app notification
        try:
            user = User.objects.filter(
                church_member__member=member,
                church_member__is_portal_active=True
            ).first()
            
            if user:
                if is_overdue:
                    title = "Kikumbusho cha Ahadi - Mpendwa wa Kristo"
                    message = (
                        f" tunakukumbusha kuhusu ahadi yako ya TZS {remaining:,.2f} "
                        f"kwa ajili ya {event_title} ambayo imepitiliza muda. Tafadhali kamilisha wakati unapoweza. "
                        f"Tunathamini moyo wako wa kutoa. Mungu akubariki."

                    )
                    priority = 'urgent'
                elif is_urgent:
                    title = "Kikumbusho cha Ahadi - Mpendwa wa Kristo"
                    message = (
                        f"Ahadi yako ya TZS {remaining:,.2f} kwa ajili ya {event_title} "
                        f"inatakiwa kukamilika baada ya siku {days_until_due}. Tunathamini mchango wako. Mungu akubariki."

                    )
                    priority = 'high'
                else:
                    title = "Kikumbusho cha Ahadi - Mpendwa wa Kristo"
                    message = (
                        f"Mpendwa, tunakukaribisha kukamilisha ahadi yako ya TZS {remaining:,.2f} "
                        f"kwa ajili ya {event_title} kufikia {pledge.due_date.strftime('%d %B %Y')}. "
                        f"Ushirika wako ni muhimu sana kwa maendeleo ya parokia. Tunakushukuru. Mungu akubariki."

                    )
                    priority = 'normal'
                
                notification = Notification.objects.create(
                    title=title,
                    message=message,
                    recipient_type='MEMBER',
                    member=member,
                    target_audience='PORTAL_ONLY',
                    priority=priority,
                    send_sms=False,
                    status='SENT',
                    sent_at=timezone.now()
                )
                
                UserNotification.objects.create(
                    user=user,
                    notification=notification,
                    is_read=False
                )
                
                # Broadcast via WebSocket
                from notifications.utils import broadcast_notification
                broadcast_notification(notification)
                
                logger.info(f"Live reminder sent to user {user.username}")
        except Exception as e:
            logger.error(f"Live reminder failed for pledge {pledge.id}: {e}")
        
        # 3. Send Email reminder
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            if user and user.email:
                if is_overdue:
                    email_subject = f"Kikumbusho cha Ahadi - Mpendwa wa Kristo - {event_title}"
                    email_body = f"""
Mpendwa {pledge.pledger_name},

Tumsifu Yesu Kristu. Tunakukumbusha kwa heshima kuhusu ahadi yako kwa ajili ya {event_title} ambayo imepitiliza muda.

Maelezo ya Ahadi:
- Jumla Iliyoahidiwa: {pledge.promised_amount:,.2f} TZS
- Kiasi Kilicholipwa: {pledge.paid_amount:,.2f} TZS
- Salio Lililosalia: {remaining:,.2f} TZS
- Tarehe ya Malipo: {pledge.due_date.strftime('%d %B %Y')} (IMECHELEWA)

Tafadhali kamilisha malipo yako wakati unapoweza. Tunathamini moyo wako wa kutoa na tunakushukuru kwa ushirika wako. 
Ikiwa unakabiliwa na changamoto yoyote, tafadhali wasiliana nasi ili tuweze kukusaidia kwa upendo.

Mungu akubariki na kukutunza.

Kwa heshima,
Timu ya Parokia ya Kristo Mfalme
"""
                else:
                    email_subject = f"Kikumbusho cha Ahadi - Mpendwa wa Kristo - {event_title}"
                    email_body = f"""
Mpendwa wa Kristu {pledge.pledger_name},

Tumsifu Yesu Kristu. Hii ni kikumbusho cha kirafiki kuhusu ahadi yako kwa ajili ya {event_title} inayokaribia.

Maelezo ya Ahadi:
- Jumla Iliyoahidiwa: {pledge.promised_amount:,.2f} TZS
- Kiasi Kilicholipwa: {pledge.paid_amount:,.2f} TZS
- Salio Lililosalia: {remaining:,.2f} TZS
- Tarehe ya Malipo: {pledge.due_date.strftime('%d %B %Y')} (zimebaki siku {days_until_due})

Tafadhali wasilisha ahadi yako kupitia lako la mtandao:
https://kristomfalme.com/portal/pledges/

Ushirika wako ni muhimu sana kwa maendeleo ya parokia. Tunakushukuru kwa moyo wako wa kutoa. 
Mungu akubariki na kukutunza.

Kwa heshima,
Timu ya Parokia ya Kristo Mfalme
"""
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
                logger.info(f"Email reminder sent to {user.email}")
        except Exception as e:
            logger.error(f"Email reminder failed: {e}")
        
        # Update the pledge's reminder tracking
        pledge.reminder_sent = True
        pledge.last_reminder_date = timezone.now()
        pledge.save(update_fields=['reminder_sent', 'last_reminder_date'])
        
        return True
