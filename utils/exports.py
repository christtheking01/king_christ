"""
Shared export utilities for all apps - CSV and PDF generation
"""
import csv
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
import io


def export_to_csv(data, filename, headers, row_extractor):
    """
    Generic CSV export function
    
    Args:
        data: QuerySet or list of objects
        filename: Base filename (without extension)
        headers: List of column headers
        row_extractor: Function that takes an object and returns list of values
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    
    for item in data:
        writer.writerow(row_extractor(item))
    
    return response


# PDF Export using weasyprint (if available) or fallback to HTML
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def generate_pdf_response(html_content, filename):
    """Generate PDF response from HTML content"""
    if WEASYPRINT_AVAILABLE:
        pdf_file = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        return response
    else:
        # Fallback to HTML if weasyprint not available
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.html"'
        return response
