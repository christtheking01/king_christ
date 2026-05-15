from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    path('api/tithes/', views.tithe_analytics_api, name='tithe_analytics_api'),
    path('api/finance/', views.finance_analytics_api, name='finance_analytics_api'),
    path('api/members/', views.member_analytics_api, name='member_analytics_api'),
    path('reports/tithes/', views.tithing_report, name='tithing_report'),
    path('reports/finance/', views.financial_report, name='financial_report'),
    path('security/blocked-users/', views.blocked_users_list, name='blocked_users'),
    path('security/unblock/<int:user_id>/', views.unblock_user_view, name='unblock_user'),
    
    # Export
    path('export/financial/', views.export_financial_report, name='export_financial_report'),
    path('export/tithes/', views.export_tithe_analytics, name='export_tithe_analytics'),
    path('export/members/', views.export_member_analytics, name='export_member_analytics'),
]
