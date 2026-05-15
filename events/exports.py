"""
Export utilities for Events app
"""
from utils.exports import export_to_csv


def export_events_to_csv(events):
    """Export events to CSV"""
    headers = ['ID', 'Title', 'Date', 'Location', 'Type', 'Status', 'Created By']
    
    def extract_row(event):
        return [
            event.id,
            event.title,
            event.start_date.strftime('%Y-%m-%d %H:%M') if event.start_date else 'N/A',
            event.location or 'N/A',
            event.get_event_type_display(),
            event.get_status_display(),
            event.created_by.username if event.created_by else 'N/A'
        ]
    
    return export_to_csv(events, 'events', headers, extract_row)


def export_event_attendance_to_csv(attendances):
    """Export event attendance to CSV"""
    headers = ['ID', 'Event', 'Member', 'Attendance Status', 'Check-in Time']
    
    def extract_row(attendance):
        return [
            attendance.id,
            attendance.event.title,
            attendance.member.name if attendance.member else 'N/A',
            attendance.get_status_display(),
            attendance.check_in_time.strftime('%Y-%m-%d %H:%M') if attendance.check_in_time else 'N/A'
        ]
    
    return export_to_csv(attendances, 'event_attendance', headers, extract_row)
