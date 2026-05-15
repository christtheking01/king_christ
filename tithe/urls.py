# tithepayment/urls.py
from django.urls import path
from . import views
from .api_auth import POSTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from .api_views import (
    api_member_lookup,
    api_submit_payment,
    api_recent_payments,
    api_print_receipt,
    api_payment_detail,
    api_dashboard_stats,
    api_sync_members,
    api_pos_settings,
    api_register_device,
    api_sync_offline_operations,
)

app_name = 'tithepayment'

urlpatterns = [
    # Main CRUD views
    path('', views.TithePaymentListView.as_view(), name='tithepayment_list'),
    path('summary/', views.TithePaymentSummaryView.as_view(), name='tithepayment_summary'),
    path('create/', views.TithePaymentCreateView.as_view(), name='tithepayment_create'),
    path('<int:pk>/', views.TithePaymentDetailView.as_view(), name='tithepayment_detail'),
    path('<int:pk>/update/', views.TithePaymentUpdateView.as_view(), name='tithepayment_update'),
    path('<int:pk>/delete/', views.TithePaymentDeleteView.as_view(), name='tithepayment_delete'),
    
    # Search and API endpoints
    path('search-members/', views.search_members, name='search_members'),
    path('get-member-details/<int:member_id>/', views.get_member_details, name='get_member_details'),
    path('quick-add/', views.quick_add_tithe_payment, name='quick_add_tithe_payment'),
    path('export/', views.export_tithe_payments, name='export_tithe_payments'),
    path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    
    # Additional reports and analytics
    path('reports/yearly/', views.YearlyReportView.as_view(), name='yearly_report'),
    path('reports/member/<int:member_id>/', views.MemberTitheReportView.as_view(), name='member_report'),
    path('analytics/dashboard/', views.TitheAnalyticsView.as_view(), name='analytics_dashboard'),

    # receipt 
    path('receipt/generate/<int:payment_id>/', views.generate_receipt, name='generate_receipt'),
    path('receipt/print/<int:receipt_id>/', views.print_receipt, name='print_receipt'),
    path('receipt/list/', views.receipt_list, name='receipt_list'),
    path('receipt/auto-generate/<int:payment_id>/', views.auto_generate_receipt, name='auto_generate_receipt'),
    
    # Bulk operations
    path('bulk/create/', views.bulk_payment_create, name='bulk_payment_create'),
    path('bulk/sms/', views.bulk_sms_send, name='bulk_sms'),
    path('bulk/sms/results/', views.bulk_sms_results, name='bulk_sms_results'),
    
    # POS Interface
    path('pos/', views.pos_home, name='pos_home'),
    path('pos/tithe/', views.pos_tithe, name='pos_tithe'),
    path('pos/offering/', views.pos_offering, name='pos_offering'),
    path('pos/pledge/', views.pos_pledge, name='pos_pledge'),
    path('pos/pin-login/', views.pos_pin_login, name='pos_pin_login'),
    path('pos/logout/', views.pos_logout, name='pos_logout'),
    path('pos/dashboard/', views.pos_dashboard, name='pos_dashboard'),
    path('pos/reports/', views.pos_reports, name='pos_reports'),
    path('pos/new-member/', views.pos_new_member, name='pos_new_member'),
    
    # POS API Endpoints
    path('pos/submit/', views.pos_tithe_submission, name='pos_tithe_submission'),
    path('pos/member-lookup/', views.pos_member_lookup, name='pos_member_lookup'),
    path('pos/print/<int:receipt_id>/', views.pos_print_receipt, name='pos_print_receipt'),
    path('pos/settings/', views.get_pos_settings, name='pos_settings'),
    path('api/recent/', views.api_recent_payments, name='api_recent_payments'),
    
    # JWT Authentication endpoints for Flutter app
    path('api/auth/login/', POSTokenObtainPairView.as_view(), name='pos_token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='pos_token_refresh'),

    # REST API v1 endpoints for Flutter app
    path('api/v1/members/lookup/', api_member_lookup, name='api_member_lookup'),
    path('api/v1/payments/submit/', api_submit_payment, name='api_submit_payment'),
    path('api/v1/payments/recent/', api_recent_payments, name='api_recent_payments'),
    path('api/v1/payments/<int:payment_id>/', api_payment_detail, name='api_payment_detail'),
    path('api/v1/receipts/<int:receipt_id>/print/', api_print_receipt, name='api_print_receipt'),
    
    # New mobile app endpoints
    path('api/v1/dashboard/stats/', api_dashboard_stats, name='api_dashboard_stats'),
    path('api/v1/sync/members/', api_sync_members, name='api_sync_members'),
    path('api/v1/settings/pos/', api_pos_settings, name='api_pos_settings'),
    path('api/v1/device/register/', api_register_device, name='api_register_device'),
    path('api/v1/sync/offline/', api_sync_offline_operations, name='api_sync_offline_operations'),
]