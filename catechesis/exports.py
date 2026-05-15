"""
Export utilities for Catechesis app
"""
from utils.exports import export_to_csv


def export_students_to_csv(students):
    """Export catechism students to CSV"""
    headers = ['ID', 'Name', 'Class', 'Year', 'Status', 'Parent/Guardian', 'Phone']
    
    def extract_row(student):
        return [
            student.id,
            student.name,
            student.class_name or 'N/A',
            student.year or 'N/A',
            student.get_status_display(),
            student.parent_name or 'N/A',
            student.parent_phone or 'N/A'
        ]
    
    return export_to_csv(students, 'catechism_students', headers, extract_row)
