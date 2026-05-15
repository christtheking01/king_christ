"""
Export utilities for Member app
"""
from utils.exports import export_to_csv


def export_members_to_csv(members):
    """Export members to CSV"""
    headers = ['ID', 'Name', 'Code', 'Phone', 'Location', 'Gender', 'Status', 'Community', 'Ministry', 'Membership Category', 'Pays Tithe', 'Working', 'Schooling']
    
    def extract_row(member):
        return [
            member.id,
            member.name,
            member.code or 'N/A',
            str(member.telephone) if member.telephone else 'N/A',
            member.location or 'N/A',
            member.get_gender_display() if member.gender else 'N/A',
            'Active' if member.active else 'Inactive',
            member.shepherd.name if member.shepherd else 'N/A',
            member.ministry.name if member.ministry else 'N/A',
            member.get_membership_category_display() if member.membership_category else 'N/A',
            'Yes' if member.pays_tithe else 'No',
            'Yes' if member.working else 'No',
            'Yes' if member.schooling else 'No'
        ]
    
    return export_to_csv(members, 'members', headers, extract_row)
