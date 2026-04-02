from django.urls import path
from . import views


urlpatterns = [
    # Dashboard
    path('financial_dashboard/', views.dashboard, name='financial_dashboard'),
    
    # Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/<int:pk>/edit/', views.edit_transaction, name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_categories'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
    
    # Employee Management
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('employees/<int:pk>/edit/', views.edit_employee, name='edit_employee'),
    path('employees/<int:pk>/delete/', views.delete_employee, name='delete_employee'),
    
    # Payroll Management
    path('payrolls/', views.payroll_list, name='payroll_list'),
    path('payrolls/generate/', views.generate_payroll, name='generate_payroll'),
    path('payrolls/<int:pk>/process/', views.process_payroll, name='process_payroll'),
    
    # Budget Management
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.create_budget, name='create_budget'),
    path('budgets/<int:pk>/', views.budget_detail, name='budget_detail'),
    
    # Expense Reports
    path('expense-reports/', views.expense_report_list, name='expense_report_list'),
    path('expense-reports/create/', views.create_expense_report, name='create_expense_report'),
    
    # Receipt Management (moved from tithe app)
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/<int:pk>/download/', views.download_receipt, name='download_receipt'),
    
    # API Endpoints
    path('api/financial-summary/', views.financial_summary_api, name='financial_summary_api'),
    path('api/member-search/', views.member_search_api, name='member_search_api'),
    
    # Pledge Management
    path('pledges/', views.pledge_list, name='pledge_list'),
    path('pledges/create/', views.pledge_create, name='pledge_create'),
    path('pledges/<int:pk>/', views.pledge_detail, name='pledge_detail'),
    path('pledges/<int:pk>/edit/', views.pledge_edit, name='pledge_edit'),
    path('pledges/<int:pk>/delete/', views.pledge_delete, name='pledge_delete'),
    path('pledges/<int:pk>/send-reminder/', views.pledge_send_reminder, name='pledge_send_reminder'),
    path('pledges/bulk-reminder/', views.pledge_bulk_reminder, name='pledge_bulk_reminder'),
    
    # Pledge Payments
    path('pledges/<int:pledge_pk>/payment/add/', views.pledge_payment_add, name='pledge_payment_add'),
    path('pledge-payments/<int:pk>/delete/', views.pledge_payment_delete, name='pledge_payment_delete'),
]