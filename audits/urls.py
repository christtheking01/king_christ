from django.urls import path
from . import views

app_name = 'audits'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.audit_dashboard, name='audit_dashboard'),
    
    # Audit Logs
    path('logs/', views.audit_log_list, name='audit_log_list'),
    path('logs/<uuid:pk>/', views.audit_log_detail, name='audit_log_detail'),
    
    # Login History
    path('login-history/', views.login_history_list, name='login_history_list'),
    
    # Security Alerts
    path('alerts/', views.security_alerts, name='security_alerts'),
    path('alerts/<uuid:pk>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Backup Management
    path('backups/', views.backup_list, name='backup_list'),
    path('backups/create/', views.create_backup, name='create_backup'),
]
