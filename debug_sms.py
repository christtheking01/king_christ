#!/usr/bin/env python3
"""
Debug script to check SMS configuration and test initialization
"""
import os
import django
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
django.setup()

from django.conf import settings

print("=== SMS Configuration Debug ===")
print(f"SEND_SMS_ENABLED: {getattr(settings, 'SEND_SMS_ENABLED', 'NOT SET')}")
print(f"AFRICASTALKING_USERNAME: {getattr(settings, 'AFRICASTALKING_USERNAME', 'NOT SET')}")
print(f"AFRICASTALKING_SENDER_ID: {getattr(settings, 'AFRICASTALKING_SENDER_ID', 'NOT SET')}")
print(f"AFRICASTALKING_API_KEY: {'SET' if getattr(settings, 'AFRICASTALKING_API_KEY', '') else 'NOT SET'}")

# Test SMS client initialization
print("\n=== Testing SMS Client Initialization ===")
try:
    from notifications.services import _get_sms_client
    sms_client = _get_sms_client()
    
    if sms_client:
        print("✅ SMS client initialized successfully")
        print(f"SMS client type: {type(sms_client)}")
    else:
        print("❌ SMS client initialization failed")
        
except Exception as e:
    print(f"❌ Error during SMS client initialization: {e}")

# Check environment variables directly
print("\n=== Environment Variables ===")
env_file = find_dotenv()
print(f".env file location: {env_file}")
if env_file and os.path.exists(env_file):
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'SMS' in line.upper() or 'AFRICA' in line.upper():
                print(f"Found: {line.strip()}")

print("\n=== Settings Loading ===")
print(f"Settings module: {settings.SETTINGS_MODULE}")
print(f"DEBUG: {settings.DEBUG}")
