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
    
    # Offerings
    path('offerings/', views.offering_list, name='offering_list'),
    path('offerings/add/', views.add_offering, name='add_offering'),
    path('offerings/<int:pk>/edit/', views.edit_offering, name='edit_offering'),
    path('offerings/<int:pk>/delete/', views.delete_offering, name='delete_offering'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_categories'),
    path('categories/<int:pk>/edit/', views.edit_category, name='edit_category'),
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
    path('payrolls/<int:pk>/submit-for-verification/', views.submit_payroll_for_verification, name='submit_payroll_for_verification'),
    path('payrolls/<int:pk>/verify/', views.verify_payroll, name='verify_payroll'),
    path('payrolls/<int:pk>/reject/', views.reject_payroll, name='reject_payroll'),
    
    # Budget Management
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.create_budget, name='create_budget'),
    path('budgets/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('budgets/<int:pk>/edit/', views.edit_budget, name='edit_budget'),
    path('budgets/<int:pk>/submit-for-approval/', views.submit_budget_for_approval, name='submit_budget_for_approval'),
    path('budgets/<int:pk>/approve/', views.approve_budget, name='approve_budget'),
    path('budgets/<int:pk>/reject/', views.reject_budget, name='reject_budget'),
    path('budgets/<int:pk>/add-allocation/', views.add_budget_allocation, name='add_budget_allocation'),
    path('budgets/<int:pk>/allocation/<int:allocation_id>/edit/', views.edit_budget_allocation, name='edit_budget_allocation'),
    path('budgets/<int:pk>/allocation/<int:allocation_id>/delete/', views.delete_budget_allocation, name='delete_budget_allocation'),
    path('budgets/reports/', views.budget_reports, name='budget_reports'),
    path('budgets/transfer-request/', views.budget_transfer_request, name='budget_transfer_request'),
    path('budgets/transfer/<int:pk>/approve/', views.approve_budget_transfer, name='approve_budget_transfer'),
    path('budgets/transfer/<int:pk>/reject/', views.reject_budget_transfer, name='reject_budget_transfer'),
    path('budgets/variances/', views.budget_variances, name='budget_variances'),
    path('budgets/alerts/<int:pk>/acknowledge/', views.acknowledge_budget_alert, name='acknowledge_budget_alert'),
    
    # Budget Export
    path('budgets/export/', views.export_budgets, name='export_budgets'),
    path('budgets/<int:pk>/export-allocations/', views.export_budget_allocations, name='export_budget_allocations'),
    path('budgets/reports/export/', views.export_budget_reports, name='export_budget_reports'),
    
    # Budget Print
    path('budgets/<int:pk>/print/', views.print_budget, name='print_budget'),
    path('budgets/<int:pk>/print-allocations/', views.print_budget_allocations, name='print_budget_allocations'),
    
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
    path('pledges-payments/<int:pk>/delete/', views.pledge_payment_delete, name='pledge_payment_delete'),
    
    # Leadership Approval Views
    path('leadership/payroll-approvals/', views.leadership_payroll_approvals, name='leadership_payroll_approvals'),
    path('leadership/payroll/<int:pk>/', views.leadership_payroll_detail, name='leadership_payroll_detail'),
    path('leadership/budget-approvals/', views.leadership_budget_approvals, name='leadership_budget_approvals'),
    path('leadership/budget/<int:pk>/', views.leadership_budget_detail, name='leadership_budget_detail'),
    path('leadership/expense-approvals/', views.leadership_expense_approvals, name='leadership_expense_approvals'),
    path('leadership/expense/<int:pk>/', views.leadership_expense_detail, name='leadership_expense_detail'),
]