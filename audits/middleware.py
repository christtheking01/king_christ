import json
import re
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.conf import settings
from .models import AuditLog, LoginHistory
from .utils import get_client_ip, parse_user_agent, get_location_from_ip

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
            self._log_action(request, response)

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
        
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
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


class LoginHistoryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._track_login_logout(request, response)
        return response

    def _track_login_logout(self, request, response):
        path = request.path
        method = request.method

        if method != 'POST':
            return

        if '/login' in path or '/_login_' in path:
            self._log_login_attempt(request, response)
        elif '/logout' in path or '/_logout' in path:
            self._log_logout(request)

    def _log_login_attempt(self, request, response):
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_data = parse_user_agent(user_agent)

        username = request.POST.get('username', '')
        
        success = response.status_code == 302 or response.status_code == 200
        
        user = None
        if success and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            username = user.username

        LoginHistory.objects.create(
            user=user,
            username_attempted=username,
            ip_address=ip,
            user_agent=user_agent[:500],
            location=get_location_from_ip(ip),
            device_info=ua_data.get('device', ''),
            browser=ua_data.get('browser', ''),
            os=ua_data.get('os', ''),
            status='SUCCESS' if success else 'FAILED',
            failure_reason='' if success else 'Invalid credentials',
            session_key=request.session.session_key if request.session else ''
        )

    def _log_logout(self, request):
        if not request.user.is_authenticated:
            return

        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_data = parse_user_agent(user_agent)

        LoginHistory.objects.create(
            user=request.user,
            username_attempted=request.user.username,
            ip_address=ip,
            user_agent=user_agent[:500],
            location=get_location_from_ip(ip),
            device_info=ua_data.get('device', ''),
            browser=ua_data.get('browser', ''),
            os=ua_data.get('os', ''),
            status='LOGOUT',
            session_key=request.session.session_key if request.session else ''
        )
