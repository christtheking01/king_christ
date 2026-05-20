#!/usr/bin/env python3
"""Test email configuration - Run in Render Shell"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'christ_king_church.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")

try:
    result = send_mail(
        'Test Email from Render',
        'This is a test email from your Django app on Render.',
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER],  # Send to yourself
        fail_silently=False,
    )
    print(f"\n✅ Email sent successfully! ({result} message sent)")
except Exception as e:
    print(f"\n❌ Email failed: {e}")
