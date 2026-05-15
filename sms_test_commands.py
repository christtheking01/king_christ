#!/usr/bin/env python3
"""
SMS Testing Commands - Copy and paste these commands
"""

print("=== SMS Testing Commands ===\n")

print("1. BASIC CONFIGURATION CHECK:")
print("python manage.py shell -c \"from django.conf import settings; print('SMS Enabled:', getattr(settings, 'SEND_SMS_ENABLED', False)); print('AT Username:', getattr(settings, 'AFRICASTALKING_USERNAME', 'NOT SET')); print('AT API Key:', 'SET' if getattr(settings, 'AFRICASTALKING_API_KEY', '') else 'NOT SET')\"")

print("\n2. SIMPLE SMS TEST:")
print("python manage.py shell -c \"from notifications.services import NotificationService; service = NotificationService(); result = service.at_service.send_sms(['+255712345678'], 'Test SMS from Kristo Mfalme'); print('Success:', result.get('success')); print('Message ID:', result.get('response', {}).get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId', 'N/A') if result.get('success') else 'N/A'); print('Error:', result.get('error') if not result.get('success') else 'None')\"")

print("\n3. EVENT REGISTRATION SMS TEST:")
print("python manage.py shell -c \"from events.models import Event, EventRegistration, EventCategory, EventLocation; from users.models import User; from django.utils import timezone; user = User.objects.filter(is_staff=True).first(); category, _ = EventCategory.objects.get_or_create(name='Test', defaults={'color': '#007bff'}); location, _ = EventLocation.objects.get_or_create(name='Test Location'); event = Event.objects.create(title='SMS Test Event', start_date=timezone.now().date() + timezone.timedelta(days=1), organizer=user, created_by=user, status='PUBLISHED', requires_registration=True); registration = EventRegistration.objects.create(event=event, first_name='Test', last_name='User', email='test@example.com', phone='+255712345678', status='CONFIRMED'); print('Created test registration:', registration.id); from events.signals import send_event_registration_sms; send_event_registration_sms(EventRegistration, registration, created=True); registration.refresh_from_db(); print('SMS sent:', registration.sms_sent); print('Message ID:', registration.sms_message_id); registration.delete(); event.delete(); print('Test completed')\"")

print("\n4. INTERACTIVE SHELL METHOD:")
print("python manage.py shell")
print("# Then run these commands interactively:")
print("from django.conf import settings")
print("from notifications.services import NotificationService")
print("service = NotificationService()")
print("result = service.at_service.send_sms(['+255712345678'], 'Test SMS')")
print("print('Result:', result)")

print("\n5. EVENT REMINDERS TEST:")
print("python manage.py send_event_reminders --dry-run")

print("\n6. DIRECT AFRICAS TALKING TEST:")
print("python manage.py shell -c \"from tithe.sms_api.africastalking import SMS; result = SMS.send_sms('+255712345678', 'Direct AT test'); print('Result:', result)\"")

print("\nChoose a method and replace '+255712345678' with your test phone number")
