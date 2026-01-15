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