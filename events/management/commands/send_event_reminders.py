from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from events.models import Event, EventRegistration, EventReminder
from events.signals import send_event_reminder_sms
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send SMS reminders for upcoming events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending SMS (just show what would be sent)'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Look ahead this many hours for reminders (default: 24)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours_ahead = options['hours']
        
        self.stdout.write(f"Checking for event reminders (next {hours_ahead} hours)...")
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No SMS will be sent")
        
        # Get current time
        now = timezone.now()
        end_time = now + timedelta(hours=hours_ahead)
        
        # Find events with reminders due
        reminders_sent = 0
        reminders_failed = 0
        
        for reminder in EventReminder.objects.filter(sent=False).select_related('event'):
            event = reminder.event
            
            # Check if event is still active and not cancelled
            if event.status != 'PUBLISHED':
                continue
            
            # Calculate reminder time
            if event.start_time:
                event_datetime = timezone.make_aware(
                    timezone.datetime.combine(event.start_date, event.start_time)
                )
            else:
                # Default to 9:00 AM if no time specified
                event_datetime = timezone.make_aware(
                    timezone.datetime.combine(event.start_date, timezone.time(9, 0))
                )
            
            reminder_time = event_datetime - timedelta(minutes=reminder.minutes_before)
            
            # Check if it's time to send reminder
            if now >= reminder_time and event_datetime > now:
                self.stdout.write(f"\nProcessing reminder for: {event.title}")
                self.stdout.write(f"  Event time: {event_datetime}")
                self.stdout.write(f"  Reminder time: {reminder_time}")
                
                # Get confirmed registrations
                registrations = event.registrations.filter(
                    status='CONFIRMED'
                ).exclude(phone__isnull=True).exclude(phone='')
                
                self.stdout.write(f"  Registrations to notify: {registrations.count()}")
                
                if dry_run:
                    for registration in registrations:
                        self.stdout.write(f"    Would send SMS to: {registration.phone} ({registration.full_name})")
                    continue
                
                # Send SMS to each registration
                success_count = 0
                for registration in registrations:
                    if send_event_reminder_sms(event, registration):
                        success_count += 1
                    else:
                        reminders_failed += 1
                
                # Mark reminder as sent
                if success_count > 0:
                    reminder.sent = True
                    reminder.save()
                    reminders_sent += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Sent {success_count} reminders"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed to send any reminders"))
        
        # Also handle automatic reminders for events without explicit reminders
        self.stdout.write("\nChecking for automatic reminders (24h before event)...")
        
        auto_reminder_minutes = 1440  # 24 hours
        
        for event in Event.objects.filter(
            status='PUBLISHED',
            start_date__gte=now.date(),
            start_date__lte=(now + timedelta(hours=hours_ahead)).date()
        ):
            # Skip if event already has reminders configured
            if event.reminders.exists():
                continue
            
            # Calculate event datetime
            if event.start_time:
                event_datetime = timezone.make_aware(
                    timezone.datetime.combine(event.start_date, event.start_time)
                )
            else:
                event_datetime = timezone.make_aware(
                    timezone.datetime.combine(event.start_date, timezone.time(9, 0))
                )
            
            # Check if 24h reminder is due
            reminder_time = event_datetime - timedelta(minutes=auto_reminder_minutes)
            
            if now >= reminder_time and event_datetime > now:
                self.stdout.write(f"\nAuto-reminder for: {event.title}")
                
                registrations = event.registrations.filter(
                    status='CONFIRMED'
                ).exclude(phone__isnull=True).exclude(phone='')
                
                if registrations.count() == 0:
                    continue
                
                self.stdout.write(f"  Registrations to notify: {registrations.count()}")
                
                if dry_run:
                    for registration in registrations:
                        self.stdout.write(f"    Would send auto-reminder SMS to: {registration.phone} ({registration.full_name})")
                    continue
                
                # Send auto-reminder
                success_count = 0
                for registration in registrations:
                    if send_event_reminder_sms(event, registration):
                        success_count += 1
                    else:
                        reminders_failed += 1
                
                if success_count > 0:
                    # Create automatic reminder record
                    EventReminder.objects.create(
                        event=event,
                        reminder_type='SMS',
                        minutes_before=auto_reminder_minutes,
                        sent=True
                    )
                    reminders_sent += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Sent {success_count} auto-reminders"))
        
        # Summary
        self.stdout.write(f"\n=== SUMMARY ===")
        self.stdout.write(f"Reminders processed: {reminders_sent}")
        if reminders_failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed reminders: {reminders_failed}"))
        
        if dry_run:
            self.stdout.write("DRY RUN COMPLETED - No SMS were actually sent")
        else:
            self.stdout.write(self.style.SUCCESS("Event reminder processing completed"))
