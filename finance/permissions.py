from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class ParishRoles:
    """Role definitions for parish management system"""
    
    PARISH_ADMIN = 'admin'
    TREASURER = 'treasurer'
    SECRETARY = 'secretary'
    VIEWER = 'viewer'
    CATECHIST = 'catechist'
    PRIEST = 'priest'
    CHAIRPERSON = 'chairperson'
    VICE_CHAIRPERSON = 'vice_chairperson'
    COORDINATOR = 'coordinator'
    MEMBER = 'member'
    ACTIVE_MEMBER = 'active_member'
    LITURGICAL = 'liturgical'
    EVANGELIZATION = 'evangelization'
    YOUTH = 'youth'
    CHOIR = 'choir'
    READER = 'reader'
    
    CHOICES = [
        (PARISH_ADMIN, 'Admin'),
        (TREASURER, 'Treasurer'),
        (SECRETARY, 'Secretary'),
        (MEMBER, 'member'),
    ]


class ParishPermissions:
    """Permission definitions for parish operations"""
    
    # Finance permissions
    CAN_VIEW_FINANCE = 'can_view_finance'
    CAN_MANAGE_TRANSACTIONS = 'can_manage_transactions'
    CAN_APPROVE_TRANSACTIONS = 'can_approve_transactions'
    CAN_MANAGE_PAYROLL = 'can_manage_payroll'
    CAN_APPROVE_PAYROLL = 'can_approve_payroll'
    CAN_MANAGE_BUDGETS = 'can_manage_budgets'
    CAN_APPROVE_BUDGETS = 'can_approve_budgets'
    CAN_MANAGE_EXPENSES = 'can_manage_expenses'
    CAN_APPROVE_EXPENSES = 'can_approve_expenses'
    
    # Tithe permissions
    CAN_VIEW_TITHE = 'can_view_tithe'
    CAN_RECORD_TITHE = 'can_record_tithe'
    CAN_MANAGE_TITHE = 'can_manage_tithe'
    
    # Offering permissions
    CAN_VIEW_OFFERINGS = 'can_view_offerings'
    CAN_RECORD_OFFERINGS = 'can_record_offerings'
    
    # Pledge permissions
    CAN_VIEW_PLEDGES = 'can_view_pledges'
    CAN_MANAGE_PLEDGES = 'can_manage_pledges'
    CAN_SEND_REMINDERS = 'can_send_reminders'
    
    # Member permissions
    CAN_VIEW_MEMBERS = 'can_view_members'
    CAN_MANAGE_MEMBERS = 'can_manage_members'
    
    # Admin permissions
    CAN_DELETE_RECORDS = 'can_delete_records'
    CAN_RESTORE_RECORDS = 'can_restore_records'
    CAN_VIEW_AUDIT_LOG = 'can_view_audit_log'
    CAN_MANAGE_USERS = 'can_manage_users'

    # Catechesis permissions
    CAN_VIEW_CATECHESIS = 'can_view_catechesis'
    CAN_MANAGE_CATECHESIS = 'can_manage_catechesis'
    CAN_APPROVE_SACRAMENTS = 'can_approve_sacraments'
    CAN_REVIEW_SACRAMENTS = 'can_review_sacraments'
    CAN_COMPLETE_SACRAMENTS = 'can_complete_sacraments'

# Role-based permission mapping
ROLE_PERMISSIONS = {

    ParishRoles.PARISH_ADMIN: [
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_MANAGE_TRANSACTIONS,
        ParishPermissions.CAN_APPROVE_TRANSACTIONS,
        ParishPermissions.CAN_MANAGE_PAYROLL,
        ParishPermissions.CAN_APPROVE_PAYROLL,
        ParishPermissions.CAN_MANAGE_BUDGETS,
        ParishPermissions.CAN_APPROVE_BUDGETS,
        ParishPermissions.CAN_MANAGE_EXPENSES,
        ParishPermissions.CAN_APPROVE_EXPENSES,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_RECORD_TITHE,
        ParishPermissions.CAN_MANAGE_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_RECORD_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
        ParishPermissions.CAN_MANAGE_PLEDGES,
        ParishPermissions.CAN_SEND_REMINDERS,
        ParishPermissions.CAN_VIEW_MEMBERS,
        ParishPermissions.CAN_MANAGE_MEMBERS,
        ParishPermissions.CAN_DELETE_RECORDS,
        ParishPermissions.CAN_RESTORE_RECORDS,
        ParishPermissions.CAN_VIEW_AUDIT_LOG,
        ParishPermissions.CAN_MANAGE_USERS,
    ],

    ParishRoles.TREASURER: [
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_MANAGE_TRANSACTIONS,
        ParishPermissions.CAN_MANAGE_PAYROLL,
        ParishPermissions.CAN_APPROVE_PAYROLL,
        ParishPermissions.CAN_MANAGE_BUDGETS,
        ParishPermissions.CAN_APPROVE_BUDGETS,
        ParishPermissions.CAN_MANAGE_EXPENSES,
        ParishPermissions.CAN_APPROVE_EXPENSES,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_RECORD_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_RECORD_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
        ParishPermissions.CAN_MANAGE_PLEDGES,
        ParishPermissions.CAN_SEND_REMINDERS,
        ParishPermissions.CAN_VIEW_MEMBERS,
    ],

    ParishRoles.SECRETARY: [
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_MANAGE_TRANSACTIONS,
        ParishPermissions.CAN_MANAGE_EXPENSES,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_RECORD_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_RECORD_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
        ParishPermissions.CAN_SEND_REMINDERS,
        ParishPermissions.CAN_VIEW_MEMBERS,
        ParishPermissions.CAN_MANAGE_MEMBERS,
    ],

    ParishRoles.VIEWER: [
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
        ParishPermissions.CAN_VIEW_MEMBERS,
    ],

        ParishRoles.CATECHIST: [
        ParishPermissions.CAN_VIEW_MEMBERS,
        ParishPermissions.CAN_VIEW_CATECHESIS,
        ParishPermissions.CAN_MANAGE_CATECHESIS,
        ParishPermissions.CAN_REVIEW_SACRAMENTS,
        ParishPermissions.CAN_COMPLETE_SACRAMENTS,
    ],

    ParishRoles.PRIEST: [
        ParishPermissions.CAN_VIEW_MEMBERS,
        ParishPermissions.CAN_VIEW_CATECHESIS,
        ParishPermissions.CAN_MANAGE_CATECHESIS,
        ParishPermissions.CAN_APPROVE_SACRAMENTS,
        ParishPermissions.CAN_REVIEW_SACRAMENTS,
        ParishPermissions.CAN_COMPLETE_SACRAMENTS,
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
    ],

    ParishRoles.MEMBER: [
        ParishPermissions.CAN_VIEW_MEMBERS,
        ParishPermissions.CAN_VIEW_FINANCE,
        ParishPermissions.CAN_VIEW_TITHE,
        ParishPermissions.CAN_VIEW_OFFERINGS,
        ParishPermissions.CAN_VIEW_PLEDGES,
        ParishPermissions.CAN_VIEW_MEMBERS,
    ],

}


def has_parish_permission(user, permission):
    """Check if user has a specific parish permission"""
    if not user or not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Get user's parish role from profile (assuming it's stored there)
    role = getattr(user, 'roles', None)
    if not role:
        return False
    
    return permission in ROLE_PERMISSIONS.get(role, [])


def require_parish_permission(permission):
    """Decorator to require specific parish permission"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if has_parish_permission(request.user, permission):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to perform this action.')
                return redirect('home')
        return _wrapped_view
    return decorator


class PermissionMixin:
    """Mixin for class-based views to check parish permissions"""
    required_permission = None
    
    def dispatch(self, request, *args, **kwargs):
        if self.required_permission and not has_parish_permission(request.user, self.required_permission):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
