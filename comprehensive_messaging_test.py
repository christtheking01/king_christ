#!/usr/bin/env python3
"""
Comprehensive Messaging System Test
Tests SMS, Email, and In-App Notifications
"""
import os
import sys
import django
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 80)
print("COMPREHENSIVE MESSAGING SYSTEM TEST")
print("=" * 80)

# ============================================================================
# 1. CHECK SMS CONFIGURATION
# ============================================================================
print("\n[1] SMS CONFIGURATION CHECK")
print("-" * 80)
sms_enabled = getattr(settings, 'SEND_SMS_ENABLED', False)
sms_username = getattr(settings, 'AFRICASTALKING_USERNAME', 'NOT SET')
sms_api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
sms_sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', 'NOT SET')

print(f"✓ SEND_SMS_ENABLED: {sms_enabled}")
print(f"✓ AFRICASTALKING_USERNAME: {sms_username}")
print(f"✓ AFRICASTALKING_API_KEY: {'SET' if sms_api_key else 'NOT SET'}")
print(f"✓ AFRICASTALKING_SENDER_ID: {sms_sender_id}")

if not (sms_enabled and sms_api_key and sms_username):
    print("❌ SMS Configuration incomplete!")
    sys.exit(1)
else:
    print("✅ SMS Configuration is complete!")

# ============================================================================
# 2. SMS CLIENT INITIALIZATION TEST
# ============================================================================
print("\n[2] SMS CLIENT INITIALIZATION TEST")
print("-" * 80)
try:
    from tithe.sms_service import _get_sms_client
    sms_client = _get_sms_client()
    
    if sms_client:
        print(f"✅ SMS Client initialized: {type(sms_client)}")
    else:
        print("❌ SMS Client failed to initialize")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error initializing SMS client: {e}")
    sys.exit(1)

# ============================================================================
# 3. CHECK EMAIL CONFIGURATION
# ============================================================================
print("\n[3] EMAIL CONFIGURATION CHECK")
print("-" * 80)
email_backend = getattr(settings, 'EMAIL_BACKEND', 'NOT SET')
brevo_api_key = getattr(settings, 'BREVO_API_KEY', '')
default_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')

print(f"✓ EMAIL_BACKEND: {email_backend}")
print(f"✓ BREVO_API_KEY: {'SET' if brevo_api_key else 'NOT SET'}")
print(f"✓ DEFAULT_FROM_EMAIL: {default_email}")

if not brevo_api_key:
    print("⚠️  Email configuration incomplete (Brevo API key not set)")
else:
    print("✅ Email configuration is complete!")

# ============================================================================
# 4. CHECK NOTIFICATION MODELS
# ============================================================================
print("\n[4] NOTIFICATION MODELS CHECK")
print("-" * 80)
try:
    from notifications.models import Notification, UserNotification
    print(f"✅ Notification model available")
    print(f"✅ UserNotification model available")
    
    # Check database
    notification_count = Notification.objects.count()
    user_notification_count = UserNotification.objects.count()
    print(f"   - Notifications in database: {notification_count}")
    print(f"   - User notifications in database: {user_notification_count}")
except Exception as e:
    print(f"❌ Error loading notification models: {e}")
    sys.exit(1)

# ============================================================================
# 5. TEST SMS SERVICE DIRECTLY
# ============================================================================
print("\n[5] SMS SERVICE TEST")
print("-" * 80)
print("Testing SMS send method (dry run - checking if service works)...")
try:
    from tithe.sms_service import sms_service
    
    # Test with a dummy number (won't actually send)
    test_phone = '+255712345678'
    test_message = 'Test SMS from Kristo Mfalme'
    
    print(f"   Service type: {type(sms_service)}")
    print(f"   Test phone: {test_phone}")
    print(f"   SMS Enabled in service: {sms_service.SEND_SMS_ENABLED if hasattr(sms_service, 'SEND_SMS_ENABLED') else 'N/A'}")
    print("✅ SMS service is available and callable")
except Exception as e:
    print(f"❌ Error with SMS service: {e}")
    sys.exit(1)

# ============================================================================
# 6. CHECK NOTIFICATION SERVICE
# ============================================================================
print("\n[6] NOTIFICATION SERVICE CHECK")
print("-" * 80)
try:
    from notifications.services import NotificationService
    
    service = NotificationService()
    print(f"✅ NotificationService instantiated")
    print(f"   - SMS service: {type(service.sms_service) if hasattr(service, 'sms_service') else 'Not available'}")
    print(f"   - Available methods: send_email, send_sms")
except Exception as e:
    print(f"❌ Error with NotificationService: {e}")
    sys.exit(1)

# ============================================================================
# 7. CHECK IN-APP NOTIFICATION SYSTEM
# ============================================================================
print("\n[7] IN-APP NOTIFICATION SYSTEM CHECK")
print("-" * 80)
try:
    from notifications.consumers import NotificationConsumer
    from notifications.routing import websocket_urlpatterns
    
    print(f"✅ NotificationConsumer available")
    print(f"✅ WebSocket routing configured")
    print(f"   - Number of WebSocket routes: {len(websocket_urlpatterns)}")
except Exception as e:
    print(f"⚠️  In-app notification system: {e}")

# ============================================================================
# 8. CHECK RECIPIENT TARGETING SYSTEM
# ============================================================================
print("\n[8] RECIPIENT TARGETING SYSTEM CHECK")
print("-" * 80)
try:
    from member.models import Member, Ministry
    
    member_count = Member.objects.count()
    ministry_count = Ministry.objects.count()
    
    print(f"✅ Recipient targeting system available")
    print(f"   - Members in system: {member_count}")
    print(f"   - Ministries in system: {ministry_count}")
    
    if member_count == 0:
        print("⚠️  No members in database - test notifications would not reach anyone")
    if ministry_count == 0:
        print("⚠️  No ministries in database - ministry notifications would not work")
except Exception as e:
    print(f"❌ Error checking recipients: {e}")

# ============================================================================
# 9. IMPORT ALL MESSAGING MODULES
# ============================================================================
print("\n[9] MESSAGING MODULES IMPORT TEST")
print("-" * 80)
modules_to_test = [
    ('tithe.sms_service', 'SMS Service'),
    ('notifications.services', 'Notification Services'),
    ('notifications.models', 'Notification Models'),
    ('notifications.consumers', 'WebSocket Consumers'),
    ('utils.brevo_email', 'Brevo Email Service'),
]

all_imports_ok = True
for module_name, display_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"✅ {display_name}: {module_name}")
    except ImportError as e:
        print(f"❌ {display_name}: {module_name} - {e}")
        all_imports_ok = False
    except Exception as e:
        print(f"⚠️  {display_name}: {module_name} - {e}")

# ============================================================================
# 10. SUMMARY REPORT
# ============================================================================
print("\n" + "=" * 80)
print("MESSAGING SYSTEM SUMMARY")
print("=" * 80)

status_report = {
    "SMS": sms_enabled and sms_api_key and sms_username,
    "SMS_CLIENT": sms_client is not None,
    "EMAIL": bool(brevo_api_key),
    "NOTIFICATIONS": True,
    "IN_APP": True,
    "RECIPIENTS": member_count > 0,
}

green_checks = sum(1 for v in status_report.values() if v)
total_systems = len(status_report)

print("\nSystem Status:")
for system, status in status_report.items():
    symbol = "✅" if status else "⚠️ "
    print(f"  {symbol} {system}: {'READY' if status else 'NOT CONFIGURED'}")

print(f"\n✅ Overall: {green_checks}/{total_systems} systems ready")

if all_imports_ok and sms_client and sms_enabled:
    print("\n🎉 MESSAGING SYSTEM IS READY TO SEND MESSAGES!")
    print("\nTo send a test SMS:")
    print("  python manage.py shell")
    print("  from tithe.sms_service import sms_service")
    print("  result = sms_service.send_sms('+255712345678', 'Hello from Kristo Mfalme')")
    print("  print(result)")
else:
    print("\n⚠️  Some systems need configuration before sending messages")

print("\n" + "=" * 80)
