"""
Security Middleware for Rate Limiting and Account Lockout
Prevents brute force attacks and suspicious login activity
"""
import time
import hashlib
from datetime import timedelta
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Security Configuration
MAX_LOGIN_ATTEMPTS = 5  # Max failed attempts before lockout
LOCKOUT_DURATION = 1800  # 30 minutes in seconds
RATE_LIMIT_WINDOW = 300  # 5 minutes window for rate limiting
MAX_REQUESTS_PER_WINDOW = 10  # Max login attempts per IP per window
ACCOUNT_LOCKOUT_DURATION = 3600  # 1 hour account lockout after repeated failures
SUSPICIOUS_THRESHOLD = 3  # Alert threshold for suspicious activity


class SecurityMiddleware(MiddlewareMixin):
    """
    Comprehensive security middleware providing:
    - Rate limiting per IP address
    - Account lockout after failed attempts
    - Suspicious activity detection
    - Automatic blocking of brute force attacks
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.protected_paths = [
            '/accounts/_login_/',
            '/accounts/login/',
            '/api/login/',
            '/login/',
        ]

    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

    def _get_ip_hash(self, ip):
        """Create a hash of IP for cache keys using SHA-256"""
        return hashlib.sha256(ip.encode()).hexdigest()

    def _is_protected_path(self, path):
        """Check if path is a login/authentication endpoint"""
        return any(protected in path for protected in self.protected_paths)

    def process_request(self, request):
        """Process incoming requests for security checks"""
        if not self._is_protected_path(request.path):
            return None

        # Only apply rate limiting to POST requests (actual login attempts)
        if request.method != 'POST':
            return None

        ip = self._get_client_ip(request)
        ip_hash = self._get_ip_hash(ip)

        # Check if IP is already blocked
        block_key = f"security:blocked_ip:{ip_hash}"
        if cache.get(block_key):
            logger.warning(f"Blocked request from banned IP: {ip}")
            return HttpResponseForbidden(
                "Access temporarily blocked due to suspicious activity. Please try again later."
            )

        # Rate limiting per IP (only for POST requests)
        rate_key = f"security:rate_limit:{ip_hash}"
        request_count = cache.get(rate_key, 0)

        if request_count >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return HttpResponseForbidden(
                "Too many requests. Please wait a few minutes before trying again."
            )

        # Increment rate counter
        cache.set(rate_key, request_count + 1, RATE_LIMIT_WINDOW)

        # Check for account-specific lockout
        username = request.POST.get('username', '').lower()
        if username:
            lockout_key = f"security:account_lockout:{username}"
            if cache.get(lockout_key):
                # ttl() is only available on Redis backends, not LocMemCache
                try:
                    remaining = cache.ttl(lockout_key) if hasattr(cache, 'ttl') else None
                    minutes = remaining // 60 if remaining else ACCOUNT_LOCKOUT_DURATION // 60
                except (AttributeError, NotImplementedError):
                    minutes = ACCOUNT_LOCKOUT_DURATION // 60
                logger.warning(f"Login attempt on locked account: {username}")
                return HttpResponseForbidden(
                    f"Account temporarily locked due to too many failed attempts. "
                    f"Please try again in {minutes} minutes."
                )

        return None

    def process_response(self, request, response):
        """Process responses to track login success/failure"""
        if not self._is_protected_path(request.path):
            return response

        if request.method != 'POST':
            return response

        ip = self._get_client_ip(request)
        ip_hash = self._get_ip_hash(ip)
        username = request.POST.get('username', '').lower()

        # Determine if login was successful
        is_successful = (
            response.status_code == 302 and 
            hasattr(request, 'user') and 
            request.user.is_authenticated
        )

        if is_successful:
            # Clear failure counters on successful login
            self._clear_failure_counters(ip_hash, username)
            logger.info(f"Successful login for {username} from IP {ip}")
        else:
            # Track failed attempt
            self._track_failed_attempt(ip_hash, username, ip)

        return response

    def _clear_failure_counters(self, ip_hash, username):
        """Clear all failure tracking counters"""
        # Clear IP-based failures
        ip_fail_key = f"security:ip_failures:{ip_hash}"
        cache.delete(ip_fail_key)
        
        # Clear account-based failures
        if username:
            account_fail_key = f"security:account_failures:{username}"
            cache.delete(account_fail_key)

    def _track_failed_attempt(self, ip_hash, username, ip):
        """Track failed login attempt and apply lockouts if needed"""
        current_time = time.time()
        
        # Track IP-based failures
        ip_fail_key = f"security:ip_failures:{ip_hash}"
        ip_failures = cache.get(ip_fail_key, [])
        
        # Add current failure with timestamp
        ip_failures.append(current_time)
        
        # Keep only failures within the lockout window
        cutoff_time = current_time - LOCKOUT_DURATION
        ip_failures = [f for f in ip_failures if f > cutoff_time]
        
        cache.set(ip_fail_key, ip_failures, LOCKOUT_DURATION)

        # Check if IP should be blocked
        if len(ip_failures) >= MAX_LOGIN_ATTEMPTS * 2:  # IP gets blocked after double threshold
            block_key = f"security:blocked_ip:{ip_hash}"
            cache.set(block_key, True, LOCKOUT_DURATION * 2)
            logger.warning(f"IP {ip} blocked due to excessive failed attempts")

        # Track account-based failures
        if username:
            account_fail_key = f"security:account_failures:{username}"
            account_failures = cache.get(account_fail_key, [])
            account_failures.append(current_time)
            
            # Keep only recent failures
            account_failures = [f for f in account_failures if f > cutoff_time]
            cache.set(account_fail_key, account_failures, ACCOUNT_LOCKOUT_DURATION)

            # Lock account if threshold reached
            if len(account_failures) >= MAX_LOGIN_ATTEMPTS:
                lockout_key = f"security:account_lockout:{username}"
                cache.set(lockout_key, True, ACCOUNT_LOCKOUT_DURATION)
                logger.warning(f"Account {username} locked due to {len(account_failures)} failed attempts")


class LoginAttemptLogger:
    """Helper class to log and monitor login attempts"""
    
    @staticmethod
    def log_attempt(username, ip, user_agent, success, failure_reason=''):
        """Log login attempt for auditing"""
        from audits.models import LoginHistory
        from audits.utils import get_client_ip
        
        try:
            LoginHistory.objects.create(
                username_attempted=username,
                ip_address=ip,
                user_agent=user_agent[:500] if user_agent else '',
                status='SUCCESS' if success else 'FAILED',
                failure_reason=failure_reason
            )
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")

    @staticmethod
    def get_recent_failures(username, minutes=30):
        """Get count of recent failed attempts for a username"""
        from django.utils import timezone
        from datetime import timedelta
        from audits.models import LoginHistory
        
        try:
            cutoff = timezone.now() - timedelta(minutes=minutes)
            return LoginHistory.objects.filter(
                username_attempted=username,
                status='FAILED',
                timestamp__gte=cutoff
            ).count()
        except Exception:
            return 0


class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (customize based on your needs)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:;"
        )
        response['Content-Security-Policy'] = csp
        
        return response
