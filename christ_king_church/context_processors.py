"""
Context processors for Christ King Church
Provides language and translation context to all templates
"""
from django.conf import settings
from django.utils.translation import get_language


def language_context(request):
    """
    Add language context to all templates for easy language switching
    """
    current_language = get_language()

    return {
        'LANGUAGE_CODE': current_language,
        'LANGUAGES': settings.LANGUAGES,
        'CURRENT_LANGUAGE_CODE': current_language,
        'CURRENT_LANGUAGE_NAME': dict(settings.LANGUAGES).get(current_language, 'English'),
        'IS_SWAHILI': current_language == 'sw',
        'IS_ENGLISH': current_language == 'en',
    }


def notification_counts_context(request):
    """
    Add notification counts for leadership approval items
    """
    if not request.user.is_authenticated:
        return {}
    
    pending_payroll_count = 0
    pending_budget_count = 0
    
    try:
        from finance.models import Payroll, Budget
        pending_payroll_count = Payroll.objects.filter(status='PENDING_VERIFICATION').count()
        pending_budget_count = Budget.objects.filter(status='PENDING_APPROVAL').count()
    except Exception:
        pass
    
    return {
        'pending_payroll_count': pending_payroll_count,
        'pending_budget_count': pending_budget_count,
    }


def menu_active_context(request):
    """
    Add active menu states based on current URL path
    """
    path = request.path
    
    return {
        # Notification menu states
        'send_to_member_active': '/notifications/send-to-member/' in path,
        'send_to_custom_active': '/notifications/send-to-custom/' in path,
        'send_tithe_reminder_active': '/notifications/send-tithe-reminder/' in path,
        'send_pledge_reminder_active': '/notifications/send-pledge-reminder/' in path,
        # Priest dashboard states
        'pending_approvals_active': '/catechesis/pending-requests/' in path,
        'pending_sacraments_active': '/catechesis/sacraments/pending/' in path,
        'payroll_verification_active': '/finance/payrolls/' in path and 'PENDING_VERIFICATION' in path,
        'priest_reports_active': '/analytics/' in path,
        # Leadership states
        'payroll_active': '/finance/payrolls/' in path,
        'budget_active': '/finance/budgets/' in path,
    }
