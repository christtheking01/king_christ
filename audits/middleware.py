import re
import logging
import asyncio
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

logger = logging.getLogger(__name__)

EXEMPT_PATHS = [
    r'^/static/',
    r'^/media/',
    r'^/audits/',
    r'/favicon\.ico$',
]

EXEMPT_ACTIONS = ['VIEW']

AUDIT_MODELS = [
    'member.Member',
    'member.Ministry',
    'member.Community',
    'member.Committee',
    'users.User',
    'users.family',
    'finance.Transaction',
    'finance.Budget',
    'finance.Employee',
    'finance.Payroll',
    'tithe.TithePayment',
    'catechesis.CatechesisMember',
    'catechesis.SacramentRequest',
]


# ============================================================
# AUDIT MIDDLEWARE
# ============================================================

class AuditMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if self._is_exempt(request.path):
            return None
        request.audit_start_time = now()
        return None

    def process_response(self, request, response):
        if self._is_exempt(request.path) or not hasattr(request, 'audit_start_time'):
            return response

        if request.user.is_authenticated:
            try:
                self._log_action(request, response)
            except Exception as e:
                logger.error(f"AuditMiddleware failed to log action: {e}")

        return response

    def _is_exempt(self, path):
        for pattern in EXEMPT_PATHS:
            if re.match(pattern, path):
                return True
        return False

    def _log_action(self, request, response):
        action = self._determine_action(request)
        if action in EXEMPT_ACTIONS:
            return

        model_name = self._extract_model_name(request)

        from audits.models import AuditLog
        from audits.utils import get_client_ip

        AuditLog.objects.create(
            user=request.user,
            action=action,
            model_name=model_name,
            path=request.path,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            status='SUCCESS' if response.status_code < 400 else 'FAILED'
        )

    def _determine_action(self, request):
        method = request.method
        path = request.path

        if '/create' in path or '/add' in path:
            return 'CREATE'
        elif '/edit' in path or '/update' in path:
            return 'UPDATE'
        elif '/delete' in path:
            return 'DELETE'
        elif '/export' in path:
            return 'EXPORT'
        elif '/import' in path:
            return 'IMPORT'
        elif '/approve' in path:
            return 'APPROVE'
        elif '/reject' in path:
            return 'REJECT'
        elif '/download' in path:
            return 'DOWNLOAD'
        elif '/print' in path:
            return 'PRINT'
        elif '/backup' in path:
            return 'BACKUP'
        elif '/restore' in path:
            return 'RESTORE'
        elif method == 'POST':
            return 'UPDATE'
        elif method == 'GET':
            return 'VIEW'

        return 'VIEW'

    def _extract_model_name(self, request):
        path = request.path
        for model in AUDIT_MODELS:
            app, model_name = model.split('.')
            if app in path or model_name.lower() in path:
                return model
        return ''


# ============================================================
# PASSWORD CHANGE MIDDLEWARE
# ============================================================

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'force_password_change', False):

            allowed_urls = [
                '/accounts/change_password/',
                '/accounts/_login_/',
                '/accounts/_logout_/',
                '/static/',
                '/media/',
                '/api/',
            ]

            is_allowed = any(request.path.startswith(url) for url in allowed_urls)

            if not is_allowed:
                return redirect(
                    f"{reverse('change_password')}?next={request.path}"
                )

        response = self.get_response(request)
        return response


# ============================================================
# LOGIN HISTORY MIDDLEWARE
# ============================================================

class LoginHistoryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Capture authenticated user BEFORE the view runs.
        # Logout clears request.user, so we must save it here.
        user_before = (
            request.user
            if hasattr(request, 'user') and request.user.is_authenticated
            else None
        )

        try:
            response = self.get_response(request)
        except asyncio.CancelledError:
            # Client disconnected or request cancelled - this is normal, log at debug level
            logger.debug(f"Request cancelled by client: {request.path}")
            # Return an empty response to avoid breaking the middleware chain
            from django.http import HttpResponse
            return HttpResponse(status=204)  # No Content
        except Exception as e:
            # Log unexpected errors but allow them to propagate
            logger.error(f"LoginHistoryMiddleware error in get_response: {e}")
            raise

        self._track_login_logout(request, response, user_before)
        return response

    def _track_login_logout(self, request, response, user_before):
        if request.method != 'POST':
            return

        path = request.path

        try:
            if '/login' in path or '/_login_' in path:
                self._log_login_attempt(request, response)
            elif '/logout' in path or '/_logout' in path:
                self._log_logout(request, user_before)
        except Exception as e:
            logger.error(f"LoginHistoryMiddleware error on path {path}: {e}")

    def _log_login_attempt(self, request, response):
        from audits.models import LoginHistory
        from audits.utils import get_client_ip, get_location_from_ip

        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_data = self._parse_user_agent_safe(user_agent)

        # Only a redirect + authenticated user = real success
        # 200 means the form was re-rendered with errors
        success = (
            response.status_code == 302
            and hasattr(request, 'user')
            and request.user.is_authenticated
        )

        user = request.user if success else None
        username = user.username if user else request.POST.get('username', '')

        try:
            LoginHistory.objects.create(
                user=user,
                username_attempted=username,
                ip_address=ip,
                user_agent=user_agent[:500],
                location=self._get_location_safe(ip),
                device_info=ua_data.get('device', ''),
                browser=ua_data.get('browser', ''),
                os=ua_data.get('os', ''),
                status='SUCCESS' if success else 'FAILED',
                failure_reason='' if success else 'Invalid credentials',
                session_key=self._get_session_key(request),
            )
        except Exception as e:
            logger.error(f"Failed to log login attempt for '{username}': {e}")

    def _log_logout(self, request, user_before):
        if not user_before:
            return

        from audits.models import LoginHistory
        from audits.utils import get_client_ip, get_location_from_ip

        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_data = self._parse_user_agent_safe(user_agent)

        try:
            LoginHistory.objects.create(
                user=user_before,
                username_attempted=user_before.username,
                ip_address=ip,
                user_agent=user_agent[:500],
                location=self._get_location_safe(ip),
                device_info=ua_data.get('device', ''),
                browser=ua_data.get('browser', ''),
                os=ua_data.get('os', ''),
                status='LOGOUT',
                failure_reason='',
                session_key=self._get_session_key(request),
            )
        except Exception as e:
            logger.error(f"Failed to log logout for '{user_before.username}': {e}")

    # ── Helpers ──────────────────────────────────────────────

    def _get_session_key(self, request):
        """Safely get session key — returns empty string if None or missing."""
        try:
            return request.session.session_key or ''
        except AttributeError:
            return ''

    def _parse_user_agent_safe(self, user_agent):
        """Parse user agent string — returns empty dict on any failure."""
        try:
            from audits.utils import parse_user_agent
            result = parse_user_agent(user_agent)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    def _get_location_safe(self, ip):
        """Get location from IP — returns empty string on any failure."""
        try:
            from audits.utils import get_location_from_ip
            return get_location_from_ip(ip) or ''
        except Exception:
            return ''