from django import template

register = template.Library()

@register.filter
def is_approver(user):
    """Check if user has approver permissions"""
    return user.is_authenticated and hasattr(user, 'is_approver') and user.is_approver()