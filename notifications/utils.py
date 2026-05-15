from django.apps import apps

def get_minister_members(ministry):
    """Get all members belonging to a ministry"""
    phones = []
    try:
        Member = apps.get_model('members', 'Member')
        members = Member.objects.filter(ministry=ministry, active=True)
        for member in members:
            if member.telephone:
                phones.append(str(member.telephone))
    except Exception as e:
        print(f"Error getting ministry members: {e}")
    return phones

def get_ministry_leaders_phone(ministry):
    """Get phone numbers of ministry leaders"""
    phones = []
    try:
        # Ministry has leader field (CharField) and phone field
        if ministry.phone:
            phones.append(str(ministry.phone))
        
        # Also check if there are committee members for this ministry
        Committee = apps.get_model('members', 'Committee')
        committees = Committee.objects.filter(member__ministry=ministry)
        for committee in committees:
            if committee.phone:
                phones.append(str(committee.phone))
    except Exception as e:
        print(f"Error getting ministry leaders: {e}")
    return phones

def get_community_members(community):
    """Get all members belonging to a community"""
    phones = []
    try:
        Member = apps.get_model('members', 'Member')
        members = Member.objects.filter(shepherd=community, active=True)
        for member in members:
            if member.telephone:
                phones.append(str(member.telephone))
    except Exception as e:
        print(f"Error getting community members: {e}")
    return phones

def get_community_leaders_phone(community):
    """Get phone numbers of community leaders"""
    phones = []
    try:
        # Get CommunityLeader objects for this community
        CommunityLeader = apps.get_model('members', 'CommunityLeader')
        leaders = CommunityLeader.objects.filter(community_name=community)
        for leader in leaders:
            if leader.phone:
                phones.append(str(leader.phone))
    except Exception as e:
        print(f"Error getting community leaders: {e}")
    return phones

def get_committee_members(committee):
    """Get members of a specific committee"""
    phones = []
    try:
        Member = apps.get_model('members', 'Member')
        members = Member.objects.filter(committee__id=committee.id, active=True)
        for member in members:
            if member.telephone:
                phones.append(str(member.telephone))
    except Exception as e:
        print(f"Error getting committee members: {e}")
    return phones

def get_all_members_phones():
    """Get phone numbers of all active members"""
    phones = []
    try:
        Member = apps.get_model('members', 'Member')
        members = Member.objects.filter(active=True)
        for member in members:
            if member.telephone:
                phones.append(str(member.telephone))
    except Exception as e:
        print(f"Error getting all members: {e}")
    return phones

def format_phone_for_kenya(phone_number):
    """Format phone number for Tz (+255)"""
    if not phone_number:
        return None
    
    # Convert to string and clean
    phone = str(phone_number).strip()
    
    # Remove any non-digit characters except +
    phone = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    # If it starts with +, return as is
    if phone.startswith('+'):
        return phone
    
    # If it starts with 254, add +
    if phone.startswith('255'):
        return '+' + phone
    
    # If it starts with 0, replace with +254
    if phone.startswith('0'):
        return '+255' + phone[1:]
    
    # If it's 10 digits and starts with 7, add +254
    if len(phone) == 9 and phone[0] in ['1', '7']:
        return '+255' + phone
    
    # Default: prepend +254
    return '+255' + phone


def broadcast_notification(notification):
    """
    Broadcast a notification to WebSocket consumers for real-time delivery.
    This sends the notification to the appropriate channel groups.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    import json
    
    channel_layer = get_channel_layer()
    
    # Build notification data
    notification_data = {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'priority': notification.priority if hasattr(notification, 'priority') else 'normal',
        'recipient_type': notification.recipient_type,
        'target_audience': notification.target_audience if hasattr(notification, 'target_audience') else 'ALL',
        'created_at': notification.created_at.isoformat() if notification.created_at else None,
        'created_by': notification.created_by.get_full_name() if notification.created_by else 'System',
    }
    
    # Determine which groups to send to based on target_audience
    target_audience = getattr(notification, 'target_audience', 'ALL')
    
    if target_audience == 'STAFF_ONLY':
        # Send only to staff group
        async_to_sync(channel_layer.group_send)(
            "staff_notifications",
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
    elif target_audience == 'MEMBERS_ONLY':
        # Send only to members group (non-staff)
        async_to_sync(channel_layer.group_send)(
            "member_notifications",
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
    elif target_audience == 'PORTAL_ONLY':
        # Send to portal members only - handled via personal groups
        from .models import UserNotification
        user_notifications = UserNotification.objects.filter(
            notification=notification,
            is_sent_via_websocket=False
        ).select_related('user')
        
        for un in user_notifications:
            # Send to personal group
            async_to_sync(channel_layer.group_send)(
                f"user_{un.user.id}_notifications",
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )
            
            # Mark as sent
            un.is_sent_via_websocket = True
            un.save(update_fields=['is_sent_via_websocket'])
    else:  # ALL
        # Send to both staff and members
        async_to_sync(channel_layer.group_send)(
            "staff_notifications",
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
        async_to_sync(channel_layer.group_send)(
            "member_notifications",
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )


def get_user_notification_count(user):
    """Get unread notification count for a specific user"""
    from .models import UserNotification
    return UserNotification.objects.filter(
        user=user,
        is_read=False
    ).count()


def mark_user_notification_sent(user_notification_id):
    """Mark a user notification as sent via WebSocket"""
    from .models import UserNotification
    try:
        un = UserNotification.objects.get(id=user_notification_id)
        un.is_sent_via_websocket = True
        un.save(update_fields=['is_sent_via_websocket'])
    except UserNotification.DoesNotExist:
        pass