#!/usr/bin/env python3
"""
Automated SMS Setup Script
This will help you configure SMS settings interactively
"""

import os

def setup_sms():
    print("=== Kristo Mfalme SMS Setup ===\n")
    
    print("This script will help you configure SMS settings.")
    print("You'll need your Africa's Talking credentials.\n")
    
    # Get Africa's Talking credentials
    print("Please enter your Africa's Talking credentials:")
    print("(Get these from https://account.africastalking.com/)\n")
    
    username = input("Africa's Talking Username (or 'sandbox' for testing): ").strip()
    if not username:
        username = "sandbox"
        print("Using sandbox username for testing")
    
    api_key = input("Africa's Talking API Key: ").strip()
    if not api_key:
        print("⚠️  Warning: No API key provided. SMS will not work without it.")
        api_key = "your_actual_api_key_here"
    
    sender_id = input("Sender ID (optional, press Enter to skip): ").strip()
    if not sender_id:
        sender_id = "KristoMfalme"
    
    print("\n=== Configuration Summary ===")
    print(f"Username: {username}")
    print(f"API Key: {'SET' if api_key != 'your_actual_api_key_here' else 'NOT SET'}")
    print(f"Sender ID: {sender_id}")
    print(f"SMS Enabled: True")
    
    confirm = input("\nDo you want to add this to your .env file? (y/n): ").strip().lower()
    
    if confirm == 'y':
        # Check if .env exists
        env_path = '.env'
        env_exists = os.path.exists(env_path)
        
        # Prepare SMS configuration
        sms_config = f"""
# SMS Configuration - Added by setup script
SEND_SMS_ENABLED=True
AFRICASTALKING_USERNAME={username}
AFRICASTALKING_API_KEY={api_key}
AFRICASTALKING_SENDER_ID={sender_id}
"""
        
        if env_exists:
            # Append to existing .env
            with open(env_path, 'a') as f:
                f.write(sms_config)
            print(f"✅ SMS configuration added to {env_path}")
        else:
            # Create new .env
            with open(env_path, 'w') as f:
                f.write(sms_config)
            print(f"✅ Created {env_path} with SMS configuration")
        
        print("\n📱 Setup Complete!")
        print("Next steps:")
        print("1. Restart your Django server")
        print("2. Test SMS with: python manage.py shell -c \"from django.conf import settings; print('SMS Enabled:', getattr(settings, 'SEND_SMS_ENABLED', False))\"")
        print("3. Send test SMS: python manage.py shell -c \"from notifications.services import NotificationService; service = NotificationService(); result = service.at_service.send_sms(['+255712345678'], 'Test SMS'); print('Result:', result)\"")
        
    else:
        print("\nSetup cancelled. Here's your configuration to add manually:")
        print(sms_config)

if __name__ == "__main__":
    setup_sms()
