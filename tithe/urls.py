# tithepayment/urls.py
from django.urls import path
from . import views

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
]