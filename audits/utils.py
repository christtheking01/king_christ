import ipaddress
import re


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return None


def parse_user_agent(user_agent):
    data = {
        'browser': 'Unknown',
        'os': 'Unknown',
        'device': 'Unknown'
    }

    if not user_agent:
        return data

    browsers = [
        (r'Chrome/(\d+)', 'Chrome'),
        (r'Firefox/(\d+)', 'Firefox'),
        (r'Safari/(\d+)', 'Safari'),
        (r'Edge/(\d+)', 'Edge'),
        (r'Opera|OPR/(\d+)', 'Opera'),
        (r'MSIE\s(\d+)|Trident.*rv:(\d+)', 'Internet Explorer'),
    ]

    for pattern, name in browsers:
        if re.search(pattern, user_agent):
            data['browser'] = name
            break

    os_patterns = [
        (r'Windows NT 10', 'Windows 10'),
        (r'Windows NT 6.3', 'Windows 8.1'),
        (r'Windows NT 6.2', 'Windows 8'),
        (r'Windows NT 6.1', 'Windows 7'),
        (r'Macintosh|Mac OS X', 'Mac OS'),
        (r'Linux', 'Linux'),
        (r'Android', 'Android'),
        (r'iPhone|iPad|iPod', 'iOS'),
    ]

    for pattern, name in os_patterns:
        if re.search(pattern, user_agent):
            data['os'] = name
            break

    if 'Mobile' in user_agent:
        data['device'] = 'Mobile'
    elif 'Tablet' in user_agent:
        data['device'] = 'Tablet'
    else:
        data['device'] = 'Desktop'

    return data


def get_location_from_ip(ip):
    if not ip:
        return 'Unknown'
    
    if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
        return 'Local Network'

    return 'Unknown'


def check_suspicious_activity(user, ip_address):
    from django.utils import timezone
    from datetime import timedelta
    from .models import LoginHistory, SecurityAlert

    last_24h = timezone.now() - timedelta(hours=24)

    failed_attempts = LoginHistory.objects.filter(
        username_attempted=user.username if user else '',
        status='FAILED',
        timestamp__gte=last_24h
    ).count()

    if failed_attempts >= 5:
        existing = SecurityAlert.objects.filter(
            alert_type='MULTIPLE_FAILED_LOGINS',
            user=user,
            status__in=['NEW', 'INVESTIGATING'],
            created_at__gte=last_24h
        ).exists()

        if not existing:
            SecurityAlert.objects.create(
                alert_type='MULTIPLE_FAILED_LOGINS',
                severity='HIGH' if failed_attempts >= 10 else 'MEDIUM',
                title=f'Multiple Failed Login Attempts ({failed_attempts})',
                description=f'User {user.username if user else "Unknown"} had {failed_attempts} failed login attempts in the last 24 hours.',
                user=user,
                ip_address=ip_address
            )

    return failed_attempts >= 5
