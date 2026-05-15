"""
Management command to send tithe reminder notifications.

This command should be run periodically (e.g., monthly) via cron or scheduled task.
Example cron entry (run on 25th of each month at 9 AM):
0 9 25 * * cd /path/to/project && python manage.py send_tithe_reminders

Usage:
    python manage.py send_tithe_reminders
    python manage.py send_tithe_reminders --dry-run
    python manage.py send_tithe_reminders --month 2024-01
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from member.models import Member
from tithe.models import TithePayment
from notifications.models import Notification, UserNotification
from notifications.services import NotificationService
from users.models import User
import logging

logger = logging.getLogger(__name__)

SWAHILI_MONTHS = {
    1: 'Januari',
    2: 'Februari',
    3: 'Machi',
    4: 'Aprili',
    5: 'Mei',
    6: 'Juni',
    7: 'Julai',
    8: 'Agosti',
    9: 'Septemba',
    10: 'Oktoba',
    11: 'Novemba',
    12: 'Desemba'
}

def get_swahili_month(date):
    """Get Swahili month name from a date object"""
    if not date:
        return ''
    month_num = date.month
    return SWAHILI_MONTHS.get(month_num, '')


class Command(BaseCommand):
    help = 'Send reminder notifications for members who pay tithe but have not paid this month'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--month',
            type=str,
            help='Specific month to check (format: YYYY-MM, e.g., 2024-01)',
        )
        parser.add_argument(
            '--send-sms',
            action='store_true',
            default=True,
            help='Send SMS reminders (default: True)',
        )
        parser.add_argument(
            '--send-in-app',
            action='store_true',
            default=True,
            help='Send in-app notifications (default: True)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        month_str = options['month']
        send_sms = options['send_sms']
        send_in_app = options['send_in_app']

        # Determine which month to check
        if month_str:
            from datetime import datetime
            check_date = datetime.strptime(month_str, '%Y-%m').date()
        else:
            check_date = timezone.now().date()

        self.stdout.write(
            self.style.HTTP_INFO(
                f"Checking for tithe payments for {check_date.strftime('%B %Y')}..."
            )
        )

        # Get all members who pay tithe
        tithe_payers = Member.objects.active().filter(pays_tithe=True)

        # Find members who haven't paid this month
        unpaid_members = []
        for member in tithe_payers:
            # Check if member has paid tithe this month
            has_paid = TithePayment.objects.filter(
                name=member,
                date__year=check_date.year,
                date__month=check_date.month
            ).exists()

            if not has_paid:
                unpaid_members.append(member)

        total_unpaid = len(unpaid_members)
        self.stdout.write(
            self.style.WARNING(
                f"Found {total_unpaid} members who haven't paid tithe for {check_date.strftime('%B %Y')}"
            )
        )

        if dry_run:
            for member in unpaid_members[:10]:  # Show first 10
                self.stdout.write(
                    f"Would remind: {member.name} ({member.telephone or 'No phone'})"
                )
            if total_unpaid > 10:
                self.stdout.write(f"... and {total_unpaid - 10} more")
            return

        # Send reminders
        sms_sent = 0
        sms_failed = 0
        in_app_sent = 0

        for member in unpaid_members:
            # Send SMS
            if send_sms and member.telephone:
                result = self.send_sms_reminder(member, check_date)
                if result:
                    sms_sent += 1
                else:
                    sms_failed += 1

            # Send in-app notification
            if send_in_app:
                result = self.send_in_app_reminder(member, check_date)
                if result:
                    in_app_sent += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tithe reminders sent: {sms_sent} SMS sent, "
                f"{sms_failed} SMS failed, {in_app_sent} in-app notifications"
            )
        )

    def send_sms_reminder(self, member, check_date):
        """Send SMS reminder to a member"""
        try:
            from tithe.sms_service import sms_service

            month_name = get_swahili_month(check_date)
            year = check_date.year
            message = (
                f"Tumsifu Yesu {member.name}, kumbuka kuchangia Zaka "
                f"ya mwezi wa {month_name} {year}. Malaki 3:10. Asante!"
            )

            phone = str(member.telephone)
            result = sms_service.send_sms(phone, message)

            if result.get('success'):
                logger.info(f"Tithe SMS reminder sent to {member.name} ({phone})")
                return True
            else:
                logger.error(
                    f"Tithe SMS failed for {member.name}: {result.get('error')}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending tithe SMS to {member.name}: {e}")
            return False

    def send_in_app_reminder(self, member, check_date):
        """Send in-app notification to a member"""
        try:
            # Find the user's portal account linked to this member
            user = User.objects.filter(
                church_member__member=member,
                church_member__is_portal_active=True
            ).first()

            if not user:
                return False

            month_name = check_date.strftime('%B %Y')

            # Create notification
            notification = Notification.objects.create(
                title=f"Tithe Payment Reminder - {month_name}",
                message=(
                    f"Dear {member.name}, this is a friendly reminder to submit "
                    f"your tithe for {month_name}. Thank you for your faithfulness!"
                ),
                recipient_type='MEMBER',
                member=member,
                target_audience='PORTAL_ONLY',
                priority='normal',
                send_sms=False,
                status='SENT',
                sent_at=timezone.now()
            )

            # Create user notification
            UserNotification.objects.create(
                user=user,
                notification=notification,
                is_read=False
            )

            # Broadcast via WebSocket
            from notifications.utils import broadcast_notification
            broadcast_notification(notification)

            logger.info(f"In-app tithe reminder sent to {user.username}")
            return True

        except Exception as e:
            logger.error(f"Error sending in-app tithe reminder for {member.name}: {e}")
            return False
