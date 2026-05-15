#!/usr/bin/env python3
"""
SMS Environment Setup Helper
This script will help you configure SMS settings
"""

print("=== SMS Configuration Setup ===\n")

print("Your SMS is currently DISABLED because:")
print("1. SEND_SMS_ENABLED is not set in .env file")
print("2. Africa's Talking credentials are not configured\n")

print("TO ENABLE SMS, follow these steps:\n")

print("STEP 1: Get Africa's Talking Credentials")
print("- Go to https://account.africastalking.com/")
print("- Sign up or login")
print("- Go to 'SMS' > 'API Keys' or 'Settings'")
print("- Copy your Username and API Key\n")

print("STEP 2: Update your .env file")
print("Add these lines to your .env file:\n")

print("# SMS Configuration")
print("SEND_SMS_ENABLED=True")
print("AFRICASTALKING_USERNAME=your_africastalking_username")
print("AFRICASTALKING_API_KEY=your_africastalking_api_key")
print("AFRICASTALKING_SENDER_ID=your_sender_id  # Optional\n")

print("STEP 3: Replace the placeholder values:")
print("- your_africastalking_username: Your AT username")
print("- your_africastalking_api_key: Your AT API key")
print("- your_sender_id: Your registered sender ID (optional)\n")

print("STEP 4: Restart your Django server")
print("The changes will take effect after restart\n")

print("STEP 5: Test SMS configuration")
print("Run this command to verify:")
print("python manage.py shell -c \"from django.conf import settings; print('SMS Enabled:', getattr(settings, 'SEND_SMS_ENABLED', False)); print('AT Username:', getattr(settings, 'AFRICASTALKING_USERNAME', 'NOT SET')); print('AT API Key:', 'SET' if getattr(settings, 'AFRICASTALKING_API_KEY', '') else 'NOT SET')\"")

print("\n" + "="*50)
print("QUICK SETUP TEMPLATE:")
print("Copy this to your .env file (replace with your actual credentials):")
print()
print("SEND_SMS_ENABLED=True")
print("AFRICASTALKING_USERNAME=sandbox")
print("AFRICASTALKING_API_KEY=your_actual_api_key_here")
print("AFRICASTALKING_SENDER_ID=KristoMfalme")

print("\nNOTE: Use 'sandbox' as username for testing, but get real API key from Africa's Talking")
