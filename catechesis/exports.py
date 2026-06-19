"""
Export utilities for Catechesis app
"""
from utils.exports import export_to_csv


def export_students_to_csv(students):
    """Export catechism students to CSV"""
    headers = ['ID', 'First Name', 'Last Name', 'Category', 'Date of Birth', 'Email', 'Phone', 'Address', 'Registration Date']
    
    def extract_row(student):
        return [
            student.id,
            student.first_name,
            student.last_name,
            student.get_member_category_display(),
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else 'N/A',
            student.email or 'N/A',
            student.phone or 'N/A',
            student.address or 'N/A',
            student.registration_date.strftime('%Y-%m-%d') if student.registration_date else 'N/A'
        ]
    
    return export_to_csv(students, 'catechism_students', headers, extract_row)


def export_member_analytics_to_csv(members_data):
    """Export individual member course progress to CSV"""
    headers = ['Member ID', 'Name', 'Category', 'Total Requests', 'Completed', 'In Progress', 'Pending', 'Progress %']
    
    def extract_row(data):
        return [
            data['member_id'],
            data['name'],
            data['category'],
            data['total_requests'],
            data['completed'],
            data['in_progress'],
            data['pending'],
            f"{data['progress_percentage']:.1f}%"
        ]
    
    return export_to_csv(members_data, 'member_course_progress', headers, extract_row)


def export_enrollment_records_to_csv(enrollments):
    """Export class enrollment records to CSV"""
    headers = ['Enrollment ID', 'Member Name', 'Class Name', 'Sacrament Type', 'Status', 'Enrolled Date', 'Completed Date']
    
    def extract_row(enrollment):
        return [
            enrollment.id,
            enrollment.catechesis_member.full_name(),
            enrollment.sacrament_class.name if enrollment.sacrament_class else 'N/A',
            enrollment.sacrament_class.get_sacrament_type_display() if enrollment.sacrament_class else 'N/A',
            enrollment.get_status_display(),
            enrollment.enrolled_date.strftime('%Y-%m-%d') if enrollment.enrolled_date else 'N/A',
            enrollment.completed_date.strftime('%Y-%m-%d') if enrollment.completed_date else 'N/A'
        ]
    
    return export_to_csv(enrollments, 'enrollment_records', headers, extract_row)


def export_attendance_records_to_csv(attendance_records):
    """Export attendance records to CSV"""
    headers = ['Date', 'Member Name', 'Class Name', 'Status', 'Notes', 'Recorded By', 'Recorded At']
    
    def extract_row(attendance):
        return [
            attendance.class_date.strftime('%Y-%m-%d'),
            attendance.catechesis_member.full_name(),
            attendance.sacrament_class.name,
            attendance.get_status_display(),
            attendance.notes or 'N/A',
            attendance.recorded_by.username if attendance.recorded_by else 'N/A',
            attendance.recorded_at.strftime('%Y-%m-%d %H:%M') if attendance.recorded_at else 'N/A'
        ]
    
    return export_to_csv(attendance_records, 'attendance_records', headers, extract_row)
