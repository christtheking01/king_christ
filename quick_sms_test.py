#!/usr/bin/env python3
"""
Quick SMS Test - Simple methods to test SMS sending
"""

print("=== Quick SMS Testing Methods ===\n")

print("METHOD 1: Django Shell (Recommended)")
print("1. Open Django shell:")
print("   python manage.py shell")
print("\n2. Run these commands one by one:")
print("   from django.conf import settings")
print("   print('SMS Enabled:', getattr(settings, 'SEND_SMS_ENABLED', False))")
print("   from notifications.services import NotificationService")
print("   service = NotificationService()")
print("   result = service.at_service.send_sms(['+255712345678'], 'Test SMS from Kristo Mfalme')")
print("   print('Result:', result)")

print("\n" + "="*50)
print("METHOD 2: One-liner Shell Command")
print("python manage.py shell -c \"from notifications.services import NotificationService; service = NotificationService(); result = service.at_service.send_sms(['+255712345678'], 'Test SMS'); print('Success:', result.get('success'), 'Message ID:', result.get('response', {}).get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId', 'N/A'))\"")

print("\n" + "="*50)
print("METHOD 3: Test Event Registration SMS")
print("python manage.py shell -c \"from events.models import Event, EventRegistration, EventCategory, EventLocation; from users.models import User; from django.utils import timezone; user = User.objects.filter(is_staff=True).first(); category, _ = EventCategory.objects.get_or_create(name='Test', defaults={'color': '#007bff'}); location, _ = EventLocation.objects.get_or_create(name='Test Location'); event = Event.objects.create(title='SMS Test Event', start_date=timezone.now().date() + timezone.timedelta(days=1), organizer=user, created_by=user, status='PUBLISHED', requires_registration=True); registration = EventRegistration.objects.create(event=event, first_name='Test', last_name='User', email='test@example.com', phone='+255712345678', status='CONFIRMED'); print('Created test registration:', registration.id); from events.signals import send_event_registration_sms; send_event_registration_sms(EventRegistration, registration, created=True); registration.refresh_from_db(); print('SMS sent:', registration.sms_sent, 'Message ID:', registration.sms_message_id); registration.delete(); event.delete(); print('Test completed')\"")

print("\n" + "="*50)
print("METHOD 4: Check Configuration Only")
print("python manage.py shell -c \"from django.conf import settings; print('SMS Settings:'); print('  SEND_SMS_ENABLED:', getattr(settings, 'SEND_SMS_ENABLED', False)); print('  AFRICASTALKING_USERNAME:', getattr(settings, 'AFRICASTALKING_USERNAME', 'NOT SET')); print('  AFRICASTALKING_API_KEY:', 'SET' if getattr(settings, 'AFRICASTALKING_API_KEY', '') else 'NOT SET')\"")

print("\n" + "="*50)
print("METHOD 5: Test Management Command")
print("# Test event reminders (dry run)")
print("python manage.py send_event_reminders --dry-run")
print("\n# Test event reminders (actual)")
print("python manage.py send_event_reminders --hours=1")

print("\n" + "="*50)
print("METHOD 6: Environment Check")
print("echo 'Checking environment:'")
print("echo 'Python path:'")
echo $PYTHONPATH
echo 'Django settings:'
python manage.py check --deploy")

print("\nChoose the method that works best for your setup!")
print("Start with METHOD 1 (Django shell) for basic testing.")
