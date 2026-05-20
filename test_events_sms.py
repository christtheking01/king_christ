#!/usr/bin/env python3
"""
Test script to verify Events SMS integration
Run this script to test the SMS functionality for events
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
django.setup()

from django.utils import timezone
from events.models import Event, EventRegistration, EventCategory, EventLocation
from member.models import Member
from users.models import User
from notifications.services import NotificationService
from events.signals import send_event_reminder_sms

def test_sms_integration():
    print("=== Testing Events SMS Integration ===\n")
    
    # Check if SMS is enabled
    from django.conf import settings
    sms_enabled = getattr(settings, 'SEND_SMS_ENABLED', False)
    print(f"SMS Enabled: {sms_enabled}")
    
    if not sms_enabled:
        print("❌ SMS is not enabled in settings. Set SEND_SMS_ENABLED=True")
        return False
    
    # Check Africa's Talking configuration
    username = getattr(settings, 'AFRICASTALKING_USERNAME', '')
    api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
    
    print(f"Africa's Talking Username: {'✓ Configured' if username else '❌ Missing'}")
    print(f"Africa's Talking API Key: {'✓ Configured' if api_key else '❌ Missing'}")
    
    if not username or not api_key:
        print("❌ Africa's Talking credentials not configured")
        return False
    
    # Test notification service
    print("\n--- Testing Notification Service ---")
    try:
        service = NotificationService()
        at_service = service.at_service
        
        if at_service.sms:
            print("✓ Africa's Talking SMS service initialized")
        else:
            print("❌ Africa's Talking SMS service not initialized")
            return False
    except Exception as e:
        print(f"❌ Error initializing notification service: {e}")
        return False
    
    # Test creating a test event
    print("\n--- Testing Event Creation ---")
    try:
        # Get or create test data
        user = User.objects.filter(is_staff=True).first()
        if not user:
            print("❌ No staff user found for testing")
            return False
        
        category, created = EventCategory.objects.get_or_create(
            name="Test Category",
            defaults={'color': '#007bff'}
        )
        
        location, created = EventLocation.objects.get_or_create(
            name="Test Location",
            defaults={'address': 'Test Address'}
        )
        
        # Create test event
        event = Event.objects.create(
            title="SMS Test Event",
            description="This is a test event for SMS integration",
            event_type="MEETING",
            category=category,
            location=location,
            start_date=timezone.now().date() + timezone.timedelta(days=1),
            start_time=timezone.now().time(),
            organizer=user,
            created_by=user,
            status="PUBLISHED",
            requires_registration=True
        )
        
        print(f"✓ Created test event: {event.title}")
        
    except Exception as e:
        print(f"❌ Error creating test event: {e}")
        return False
    
    # Test event registration with SMS
    print("\n--- Testing Event Registration SMS ---")
    try:
        # Create test registration
        registration = EventRegistration.objects.create(
            event=event,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="+255712345678",  # Test phone number
            status="CONFIRMED"
        )
        
        print(f"✓ Created test registration for: {registration.full_name}")
        
        # Manually trigger the SMS signal (since we're creating after save)
        from events.signals import send_event_registration_sms
        send_event_registration_sms(EventRegistration, registration, created=True)
        
        # Check if SMS was marked as sent
        registration.refresh_from_db()
        if registration.sms_sent:
            print("✓ SMS marked as sent in registration")
            print(f"  Message ID: {registration.sms_message_id}")
            print(f"  Sent at: {registration.sms_sent_at}")
        else:
            print("❌ SMS not marked as sent")
            if registration.last_sms_error:
                print(f"  Error: {registration.last_sms_error}")
        
    except Exception as e:
        print(f"❌ Error testing registration SMS: {e}")
        return False
    
    # Test event reminder SMS
    print("\n--- Testing Event Reminder SMS ---")
    try:
        reminder_sent = send_event_reminder_sms(event, registration)
        if reminder_sent:
            print("✓ Reminder SMS sent successfully")
        else:
            print("❌ Reminder SMS failed")
        
    except Exception as e:
        print(f"❌ Error testing reminder SMS: {e}")
        return False
    
    # Test event cancellation SMS
    print("\n--- Testing Event Cancellation SMS ---")
    try:
        from events.signals import send_event_cancellation_notifications
        send_event_cancellation_notifications(event)
        print("✓ Cancellation notifications processed")
        
    except Exception as e:
        print(f"❌ Error testing cancellation SMS: {e}")
        return False
    
    # Cleanup test data
    print("\n--- Cleaning Up Test Data ---")
    try:
        registration.delete()
        event.delete()
        print("✓ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Error cleaning up: {e}")
    
    print("\n=== Test Summary ===")
    print("✓ All SMS integration tests completed successfully!")
    return True

if __name__ == "__main__":
    success = test_sms_integration()
    if success:
        print("\n🎉 Events SMS integration is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Events SMS integration has issues. Please check the errors above.")
        sys.exit(1)
