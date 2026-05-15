#!/usr/bin/env python3
"""
Africa's Talking Callback URLs for SMS Webhooks
"""

print("=== Africa's Talking Callback URLs ===\n")

print("Your Django app already has the webhook endpoints set up.")
print("Here are the callback URLs you need to configure in Africa's Talking dashboard:\n")

print("📱 INCOMING SMS CALLBACK URL:")
print("   https://your-domain.com/notifications/sms/incoming/")
print("   (For receiving SMS from your members)\n")

print("📤 DELIVERY REPORT CALLBACK URL:")
print("   https://your-domain.com/notifications/sms/delivery/")
print("   (For tracking SMS delivery status)\n")

print("=" * 50)
print("🔧 HOW TO SET UP IN AFRICA'S TALKING:")
print("1. Login to https://account.africastalking.com/")
print("2. Go to SMS > Callback URLs")
print("3. Enter the URLs above (replace 'your-domain.com')")
print("4. Save the settings\n")

print("=" * 50)
print("🌐 FOR DIFFERENT ENVIRONMENTS:")
print("\nDEVELOPMENT (Local):")
print("   Use ngrok or similar service:")
print("   https://abc123.ngrok.io/notifications/sms/incoming/")
print("   https://abc123.ngrok.io/notifications/sms/delivery/\n")

print("PRODUCTION:")
print("   https://your-church-domain.com/notifications/sms/incoming/")
print("   https://your-church-domain.com/notifications/sms/delivery/\n")

print("RAILWAY:")
print("   https://your-app-name.railway.app/notifications/sms/incoming/")
print("   https://your-app-name.railway.app/notifications/sms/delivery/\n")

print("RENDER:")
print("   https://your-app-name.onrender.com/notifications/sms/incoming/")
print("   https://your-app-name.onrender.com/notifications/sms/delivery/\n")

print("=" * 50)
print("✅ WEBHOOK ENDPOINTS ALREADY EXIST:")
print("• /notifications/sms/incoming/ → sms_incoming view")
print("• /notifications/sms/delivery/ → sms_delivery_report view")
print("• Both handle POST requests from Africa's Talking")
print("• Both return 'OK' status for successful processing")
