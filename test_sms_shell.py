#!/usr/bin/env python3
"""
Django Shell SMS Testing Script
Run this to test SMS functionality through Django shell
"""

import os
import sys

# Add project to Python path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')

def test_sms_via_shell():
    """Test SMS using Django shell commands"""
    
    print("=== SMS Testing via Django Shell ===\n")
    
    # Commands to run in Django shell
    commands = [
        "# Check SMS configuration",
        "from django.conf import settings",
        "print('SMS Enabled:', getattr(settings, 'SEND_SMS_ENABLED', False))",
        "print('AT Username:', getattr(settings, 'AFRICASTALKING_USERNAME', 'Not configured'))",
        "print('AT API Key:', 'Configured' if getattr(settings, 'AFRICASTALKING_API_KEY', '') else 'Not configured')",
        "",
        "# Test notification service",
        "from notifications.services import NotificationService",
        "service = NotificationService()",
        "print('AT Service initialized:', service.at_service.sms is not None)",
        "",
        "# Test direct SMS",
        "from tithe.sms_api.africastalking import SMS",
        "result = SMS.send_sms('+255712345678', 'Test message from Kristo Mfalme System')",
        "print('SMS Result:', result)",
        "",
        "# Test event registration SMS",
        "from events.models import Event, EventRegistration, EventCategory, EventLocation",
        "from users.models import User",
        "from django.utils import timezone",
        "",
        "# Create test event",
        "user = User.objects.filter(is_staff=True).first()",
        "category, _ = EventCategory.objects.get_or_create(name='Test', defaults={'color': '#007bff'})",
        "location, _ = EventLocation.objects.get_or_create(name='Test Location')",
        "event = Event.objects.create(title='SMS Test Event', start_date=timezone.now().date() + timezone.timedelta(days=1), organizer=user, created_by=user, status='PUBLISHED', requires_registration=True)",
        "",
        "# Create test registration",
        "registration = EventRegistration.objects.create(event=event, first_name='Test', last_name='User', email='test@example.com', phone='+255712345678', status='CONFIRMED')",
        "print('Created test registration:', registration)",
        "",
        "# Manually trigger SMS",
        "from events.signals import send_event_registration_sms",
        "send_event_registration_sms(EventRegistration, registration, created=True)",
        "",
        "# Check SMS status",
        "registration.refresh_from_db()",
        "print('SMS sent:', registration.sms_sent)",
        "print('SMS sent at:', registration.sms_sent_at)",
        "print('SMS message ID:', registration.sms_message_id)",
        "if registration.last_sms_error:",
        "    print('SMS error:', registration.last_sms_error)",
        "",
        "# Cleanup",
        "registration.delete()",
        "event.delete()",
        "print('Test data cleaned up')",
    ]
    
    print("Run these commands in Django shell:")
    print("python manage.py shell")
    print("\nThen copy/paste these commands:\n")
    
    for cmd in commands:
        if cmd.startswith('#'):
            print(f"\033[92m{cmd}\033[0m")  # Green for comments
        else:
            print(cmd)
    
    print("\n" + "="*50)
    print("Alternative: One-liner shell command:")
    print("python manage.py shell -c \"from notifications.services import NotificationService; service = NotificationService(); result = service.at_service.send_sms(['+255712345678'], 'Test SMS'); print('Result:', result)\"")

if __name__ == "__main__":
    test_sms_via_shell()
