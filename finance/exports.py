"""
Export utilities for Finance app - CSV and PDF generation
"""
from utils.exports import export_to_csv, generate_pdf_response
from django.template.loader import render_to_string
from django.utils import timezone


def export_expense_reports_to_csv(expense_reports):
    """Export expense reports to CSV"""
    headers = ['ID', 'Title', 'Employee', 'Total Amount', 'Date Submitted', 'Status', 'Description']
    
    def extract_row(report):
        return [
            report.id,
            report.title,
            report.employee.name if report.employee else 'N/A',
            float(report.total_amount),
            report.date_submitted.strftime('%Y-%m-%d'),
            report.status,
            report.description or ''
        ]
    
    return export_to_csv(expense_reports, 'expense_reports', headers, extract_row)


def export_offerings_to_csv(offerings):
    """Export offerings to CSV"""
    headers = ['ID', 'Date', 'Amount', 'Type', 'Payment Method', 'Member', 'Donor Name', 'Notes']
    
    def extract_row(offering):
        return [
            offering.id,
            offering.date.strftime('%Y-%m-%d'),
            float(offering.amount),
            offering.get_offering_type_display(),
            offering.get_payment_method_display(),
            offering.member.name if offering.member else 'N/A',
            offering.donor_name or 'Anonymous',
            offering.notes or ''
        ]
    
    return export_to_csv(offerings, 'offerings', headers, extract_row)


def export_payroll_to_csv(payrolls):
    """Export payroll to CSV"""
    headers = ['ID', 'Employee', 'Period Start', 'Period End', 'Basic Salary', 'Gross Salary', 'Deductions', 'Net Salary', 'Status', 'Payment Method']
    
    def extract_row(payroll):
        return [
            payroll.id,
            payroll.employee.name,
            payroll.pay_period_start.strftime('%Y-%m-%d'),
            payroll.pay_period_end.strftime('%Y-%m-%d'),
            float(payroll.basic_salary),
            float(payroll.gross_salary),
            float(payroll.other_deductions),
            float(payroll.net_salary),
            payroll.status,
            payroll.get_payment_method_display()
        ]
    
    return export_to_csv(payrolls, 'payroll', headers, extract_row)


def export_transactions_to_csv(transactions):
    """Export transactions to CSV"""
    headers = ['ID', 'Date', 'Reference', 'Type', 'Category', 'Amount', 'Status', 'Description']
    
    def extract_row(transaction):
        return [
            transaction.id,
            transaction.date.strftime('%Y-%m-%d'),
            transaction.reference_number or 'N/A',
            transaction.type,
            transaction.category.name if transaction.category else 'N/A',
            float(transaction.amount),
            transaction.status,
            transaction.description or ''
        ]
    
    return export_to_csv(transactions, 'transactions', headers, extract_row)


def export_expense_reports_to_pdf(expense_reports, template_context=None):
    """Export expense reports to PDF"""
    context = template_context or {}
    context['expense_reports'] = expense_reports
    context['generated_at'] = timezone.now()
    
    html_content = render_to_string('finance/pdf/expense_reports.html', context)
    return generate_pdf_response(html_content, 'expense_reports')


def export_offerings_to_pdf(offerings, template_context=None):
    """Export offerings to PDF"""
    context = template_context or {}
    context['offerings'] = offerings
    context['generated_at'] = timezone.now()
    
    html_content = render_to_string('finance/pdf/offerings.html', context)
    return generate_pdf_response(html_content, 'offerings')


def export_payroll_to_pdf(payrolls, template_context=None):
    """Export payroll to PDF"""
    context = template_context or {}
    context['payrolls'] = payrolls
    context['generated_at'] = timezone.now()
    
    html_content = render_to_string('finance/pdf/payroll.html', context)
    return generate_pdf_response(html_content, 'payroll')


def export_budgets_to_csv(budgets):
    """Export budgets to CSV"""
    headers = ['ID', 'Name', 'Period Start', 'Period End', 'Total Budget', 'Spent', 'Remaining', 'Status', 'Created By']
    
    def extract_row(budget):
        return [
            budget.id,
            budget.name,
            budget.start_date.strftime('%Y-%m-%d') if budget.start_date else 'N/A',
            budget.end_date.strftime('%Y-%m-%d') if budget.end_date else 'N/A',
            float(budget.total_amount),
            float(budget.spent_amount) if hasattr(budget, 'spent_amount') else 0,
            float(budget.remaining_amount) if hasattr(budget, 'remaining_amount') else float(budget.total_amount),
            budget.get_status_display(),
            budget.created_by.username if budget.created_by else 'N/A'
        ]
    
    return export_to_csv(budgets, 'budgets', headers, extract_row)


def export_budget_allocations_to_csv(allocations):
    """Export budget allocations to CSV"""
    headers = ['ID', 'Budget', 'Category', 'Allocated Amount', 'Spent Amount', 'Remaining', 'Notes']
    
    def extract_row(allocation):
        return [
            allocation.id,
            allocation.budget.name if allocation.budget else 'N/A',
            allocation.category.name if allocation.category else 'N/A',
            float(allocation.allocated_amount),
            float(allocation.spent_amount) if hasattr(allocation, 'spent_amount') else 0,
            float(allocation.remaining_amount) if hasattr(allocation, 'remaining_amount') else float(allocation.allocated_amount),
            allocation.notes or ''
        ]
    
    return export_to_csv(allocations, 'budget_allocations', headers, extract_row)


def export_budget_reports_to_csv(report_data):
    """Export budget reports to CSV"""
    headers = ['Report Type', 'Category/Type', 'Count', 'Total Budgeted', 'Total Spent', 'Total Remaining']
    
    data = []
    
    # Budget summary by type
    for budget_type, summary in report_data.get('budget_summary', {}).items():
        data.append({
            'report_type': 'Budget Summary',
            'category': budget_type,
            'count': summary.get('count', 0),
            'total_budgeted': summary.get('total_budgeted', 0),
            'total_spent': summary.get('total_spent', 0),
            'total_remaining': summary.get('total_remaining', 0)
        })
    
    # Monthly trends
    for month_data in report_data.get('monthly_data', []):
        data.append({
            'report_type': 'Monthly Trend',
            'category': month_data.get('month', 'N/A'),
            'count': '-',
            'total_budgeted': month_data.get('budgeted', 0),
            'total_spent': month_data.get('spent', 0),
            'total_remaining': month_data.get('budgeted', 0) - month_data.get('spent', 0)
        })
    
    def extract_row(item):
        return [
            item['report_type'],
            item['category'],
            item['count'] if item['count'] != '-' else 0,
            float(item['total_budgeted']),
            float(item['total_spent']),
            float(item['total_remaining'])
        ]
    
    return export_to_csv(data, 'budget_reports', headers, extract_row)
