from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

from .models import AuditLog, LoginHistory, DataBackup, SecurityAlert
from users.models import User


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.roles == 'admin')


def get_user_type(user):
    """
    Classify user into: 'administrator', 'church_member', or 'unknown'
    Administrator roles include: admin, chairperson, vice_chairperson, secretary, 
    accountant, treasurer, priest, catechist, coordinator
    """
    if user is None:
        return 'unknown'
    
    admin_roles = [
        'admin', 'Admin', 
        'chairperson', 'vice_chairperson',
        'secretary', 'accountant', 'treasurer',
        'priest', 'catechist', 'coordinator'
    ]
    
    if user.is_superuser or user.is_staff or user.roles in admin_roles:
        return 'administrator'
    return 'church_member'


def get_logs_grouped_by_user_type(logs_queryset):
    """
    Group audit logs by user type: administrator, church_member, unknown
    """
    admin_logs = []
    member_logs = []
    unknown_logs = []
    
    for log in logs_queryset:
        user_type = get_user_type(log.user)
        if user_type == 'administrator':
            admin_logs.append(log)
        elif user_type == 'church_member':
            member_logs.append(log)
        else:
            unknown_logs.append(log)
    
    return {
        'administrator': admin_logs,
        'church_member': member_logs,
        'unknown': unknown_logs,
    }


@login_required
@user_passes_test(is_admin_or_staff)
def audit_dashboard(request):
    today = timezone.now().date()
    last_30_days = timezone.now() - timedelta(days=30)

    stats = {
        'total_logs_today': AuditLog.objects.filter(timestamp__date=today).count(),
        'total_logs_month': AuditLog.objects.filter(timestamp__gte=last_30_days).count(),
        'failed_logins_today': LoginHistory.objects.filter(
            timestamp__date=today,
            status='FAILED'
        ).count(),
        'active_users_today': AuditLog.objects.filter(
            timestamp__date=today
        ).values('user').distinct().count(),
        'alerts_count': SecurityAlert.objects.filter(
            status__in=['NEW', 'INVESTIGATING']
        ).count(),
    }

    action_counts = AuditLog.objects.filter(
        timestamp__gte=last_30_days
    ).values('action').annotate(count=Count('action')).order_by('-count')[:5]

    # Get recent logs grouped by user type
    recent_logs_qs = AuditLog.objects.select_related('user').order_by('-timestamp')[:50]
    grouped_logs = get_logs_grouped_by_user_type(recent_logs_qs)
    
    # Get stats by user type for today
    today_logs = AuditLog.objects.filter(timestamp__date=today).select_related('user')
    admin_count = 0
    member_count = 0
    unknown_count = 0
    for log in today_logs:
        user_type = get_user_type(log.user)
        if user_type == 'administrator':
            admin_count += 1
        elif user_type == 'church_member':
            member_count += 1
        else:
            unknown_count += 1
    
    stats['admin_logs_today'] = admin_count
    stats['member_logs_today'] = member_count
    stats['unknown_logs_today'] = unknown_count

    recent_alerts = SecurityAlert.objects.select_related('user').order_by('-created_at')[:5]

    context = {
        'stats': stats,
        'action_counts': action_counts,
        'grouped_logs': grouped_logs,
        'recent_alerts': recent_alerts,
        'audit_active': 'active',
    }
    return render(request, 'audit/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user').all()

    user_id = request.GET.get('user')
    action = request.GET.get('action')
    model_name = request.GET.get('model')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')

    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if model_name:
        logs = logs.filter(model_name__icontains=model_name)
    if status:
        logs = logs.filter(status=status)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    if search:
        logs = logs.filter(
            Q(object_repr__icontains=search) |
            Q(path__icontains=search) |
            Q(ip_address__icontains=search)
        )

    logs = logs.order_by('-timestamp')
    
    # Group logs by user type for display
    grouped_logs = get_logs_grouped_by_user_type(logs[:100])  # Group first 100 for display
    
    # Get user type counts
    admin_roles = [
        'admin', 'Admin', 
        'chairperson', 'vice_chairperson',
        'secretary', 'accountant', 'treasurer',
        'priest', 'catechist', 'coordinator'
    ]
    user_type_counts = {
        'administrator': logs.filter(user__is_superuser=True).count() + 
                        logs.filter(user__is_staff=True).count() + 
                        logs.filter(user__roles__in=admin_roles).count(),
        'church_member': logs.filter(user__is_superuser=False, user__is_staff=False).exclude(
            user__roles__in=admin_roles
        ).filter(user__isnull=False).count(),
        'unknown': logs.filter(user__isnull=True).count(),
    }

    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = User.objects.filter(is_active=True).order_by('username')
    action_choices = AuditLog.ACTION_CHOICES

    context = {
        'page_obj': page_obj,
        'grouped_logs': grouped_logs,
        'user_type_counts': user_type_counts,
        'users': users,
        'action_choices': action_choices,
        'filters': {
            'user': user_id,
            'action': action,
            'model': model_name,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        },
        'audit_logs_active': 'active',
    }
    return render(request, 'audit/log_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def audit_log_detail(request, pk):
    log = get_object_or_404(AuditLog, pk=pk)
    
    context = {
        'log': log,
        'audit_logs_active': 'active',
    }
    return render(request, 'audit/log_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def login_history_list(request):
    history = LoginHistory.objects.select_related('user').all()

    user_id = request.GET.get('user')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    ip_address = request.GET.get('ip')

    if user_id:
        history = history.filter(user_id=user_id)
    if status:
        history = history.filter(status=status)
    if date_from:
        history = history.filter(timestamp__date__gte=date_from)
    if date_to:
        history = history.filter(timestamp__date__lte=date_to)
    if ip_address:
        history = history.filter(ip_address__icontains=ip_address)

    history = history.order_by('-timestamp')

    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = User.objects.filter(is_active=True).order_by('username')
    status_choices = LoginHistory.STATUS_CHOICES

    context = {
        'page_obj': page_obj,
        'users': users,
        'status_choices': status_choices,
        'filters': {
            'user': user_id,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'ip': ip_address,
        },
        'login_history_active': 'active',
    }
    return render(request, 'audit/login_history.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def security_alerts(request):
    alerts = SecurityAlert.objects.select_related('user', 'resolved_by').all()

    severity = request.GET.get('severity')
    status = request.GET.get('status')
    alert_type = request.GET.get('type')

    if severity:
        alerts = alerts.filter(severity=severity)
    if status:
        alerts = alerts.filter(status=status)
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)

    alerts = alerts.order_by('-created_at')

    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'severity_choices': SecurityAlert.SEVERITY_CHOICES,
        'status_choices': SecurityAlert.STATUS_CHOICES,
        'alert_type_choices': SecurityAlert.ALERT_TYPE_CHOICES,
        'filters': {
            'severity': severity,
            'status': status,
            'type': alert_type,
        },
        'alerts_active': 'active',
    }
    return render(request, 'audit/security_alerts.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def resolve_alert(request, pk):
    if request.method == 'POST':
        alert = get_object_or_404(SecurityAlert, pk=pk)
        resolution_notes = request.POST.get('resolution_notes', '')
        
        alert.status = 'RESOLVED'
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = resolution_notes
        alert.save()

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
@user_passes_test(is_admin_or_staff)
def backup_list(request):
    backups = DataBackup.objects.select_related('created_by').all().order_by('-created_at')

    paginator = Paginator(backups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'backup_active': 'active',
    }
    return render(request, 'audit/backup_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def create_backup(request):
    if request.method == 'POST':
        from django.core.management import call_command
        import os
        import json
        from datetime import datetime

        backup_name = request.POST.get('name', f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        description = request.POST.get('description', '')

        backup = DataBackup.objects.create(
            name=backup_name,
            description=description,
            created_by=request.user,
            status='IN_PROGRESS'
        )

        try:
            output_dir = os.path.join('backups', 'data')
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f'{backup_name}.json')
            
            with open(output_file, 'w') as f:
                call_command('dumpdata', '--indent', '2', stdout=f)
            
            backup.status = 'COMPLETED'
            backup.file_path = output_file
            backup.completed_at = timezone.now()
            backup.save()

            return JsonResponse({
                'status': 'success',
                'backup_id': str(backup.id),
                'message': 'Backup created successfully'
            })
        except Exception as e:
            backup.status = 'FAILED'
            backup.error_message = str(e)
            backup.save()

            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error'}, status=400)
