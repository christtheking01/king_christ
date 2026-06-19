"""
Export utilities for Analytics app
"""
from utils.exports import export_to_csv


def format_currency(amount):
    """Format number as currency with commas"""
    try:
        return f"{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "0.00"


def export_financial_report_to_csv(data):
    """Export financial report data to CSV"""
    headers = ['Date', 'Income', 'Expenses', 'Net', 'Tithes', 'Offerings']
    
    def extract_row(item):
        return [
            item['date'].strftime('%Y-%m-%d') if item.get('date') else 'N/A',
            format_currency(item.get('income', 0)),
            format_currency(item.get('expenses', 0)),
            format_currency(item.get('net', 0)),
            format_currency(item.get('tithes', 0)),
            format_currency(item.get('offerings', 0))
        ]
    
    return export_to_csv(data, 'financial_report', headers, extract_row)


def export_member_analytics_to_csv(data):
    """Export member analytics to CSV"""
    headers = ['Category', 'Count', 'Percentage']
    
    def extract_row(item):
        return [
            item.get('category', 'N/A'),
            item.get('count', 0),
            f"{item.get('percentage', 0):.1f}%"
        ]
    
    return export_to_csv(data, 'member_analytics', headers, extract_row)


def export_tithe_analytics_to_csv(data):
    """Export tithe analytics to CSV"""
    headers = ['Period', 'Total Amount', 'Average Amount', 'Count']
    
    def extract_row(item):
        return [
            item.get('period', 'N/A'),
            format_currency(item.get('total_amount', 0)),
            format_currency(item.get('average_amount', 0)),
            item.get('count', 0)
        ]
    
    return export_to_csv(data, 'tithe_analytics', headers, extract_row)
