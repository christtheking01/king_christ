import json
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings

from .models import AuditLog

AUDIT_MODELS = [
    'member.Member',
    'member.Ministry',
    'member.Community',
    'member.Committee',
    'member.MinistryLeader',
    'member.CommunityLeader',
    'users.User',
    'users.UserProfile',
    'users.family',
    'users.FamilyMembership',
    'finance.Category',
    'finance.Transaction',
    'finance.TitheReceipt',
    'finance.Employee',
    'finance.Payroll',
    'finance.Budget',
    'finance.BudgetAllocation',
    'finance.ExpenseReport',
    'finance.ExpenseItem',
    'tithe.TithePayment',
    'notifications.Notification',
    'notifications.NotificationLog',
    'catechesis.CatechesisMember',
    'catechesis.Sacrament',
    'catechesis.SacramentRequest',
]


def get_model_label(model_class):
    return f"{model_class._meta.app_label}.{model_class._meta.model_name.capitalize()}"


def should_audit(model_class):
    model_label = get_model_label(model_class)
    return model_label in AUDIT_MODELS


def get_model_fields(instance):
    fields = {}
    for field in instance._meta.fields:
        try:
            value = getattr(instance, field.name)
            if hasattr(value, 'pk'):
                value = str(value)
            fields[field.name] = str(value) if value is not None else None
        except:
            fields[field.name] = 'N/A'
    return fields


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if not should_audit(sender):
        return

    try:
        action = 'CREATE' if created else 'UPDATE'
        user = None

        new_values = get_model_fields(instance)

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=get_model_label(sender),
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            new_values=new_values,
            status='SUCCESS'
        )
    except Exception:
        pass


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if not should_audit(sender):
        return

    try:
        user = None

        AuditLog.objects.create(
            user=user,
            action='DELETE',
            model_name=get_model_label(sender),
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            old_values={'deleted': True},
            status='SUCCESS'
        )
    except Exception:
        pass
