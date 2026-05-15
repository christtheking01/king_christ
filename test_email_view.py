# Add this to any views.py temporarily
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings

def test_email(request):
    """Test email configuration"""
    try:
        result = send_mail(
            'Test Email from Django',
            f'Testing email from Render.\n\nSettings:\nHost: {settings.EMAIL_HOST}\nUser: {settings.EMAIL_HOST_USER}\nFrom: {settings.DEFAULT_FROM_EMAIL}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],  # Send to yourself
            fail_silently=False,
        )
        return JsonResponse({
            'success': True,
            'message': f'Email sent! ({result} message)',
            'settings': {
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'user': settings.EMAIL_HOST_USER,
                'from': settings.DEFAULT_FROM_EMAIL,
                'backend': settings.EMAIL_BACKEND,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'settings': {
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'user': settings.EMAIL_HOST_USER,
                'from': settings.DEFAULT_FROM_EMAIL,
                'backend': settings.EMAIL_BACKEND,
            }
        }, status=500)
