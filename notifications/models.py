from django.db import models
from users.models import User
from django.utils import timezone
from member.models import Member, Ministry, Committee, Community

class Notification(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENDING', 'Sending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]
    
    RECIPIENT_TYPE_CHOICES = [
        ('MEMBER', 'Member'),
        ('MINISTRY', 'Ministry'),
        ('COMMITTEE', 'Committee'),
        ('COMMUNITY', 'Community'),
        ('ALL', 'All'),
        ('TITHE_PAYERS', 'Tithe_payer'),
        ('CUSTOM_PHONES', 'Custom_phones'),
    ]
    
    TARGET_AUDIENCE_CHOICES = [
        ('ALL', 'All_Users'),
        ('STAFF_ONLY', 'Staff_Only'),
        ('MEMBERS_ONLY', 'Members_Only'),
        ('PORTAL_ONLY', 'Portal_Only'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField(help_text="Message content (max 160 characters for single SMS)")
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE_CHOICES)
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_AUDIENCE_CHOICES,
        default='ALL',
        help_text="Who should receive this notification in the portal/app"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text="Notification priority level"
    )
    
    # Foreign keys for different recipient types
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    ministry = models.ForeignKey(
        Ministry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    # Custom phone numbers for non-registered recipients
    custom_phone_numbers = models.TextField(
        null=True,
        blank=True,
        help_text="Enter phone numbers separated by commas (e.g., +255712345678, +255723456789)"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # SMS tracking
    send_sms = models.BooleanField(default=True, help_text="Send SMS via AfricasTalking")
    total_recipients = models.IntegerField(default=0)
    sms_sent_count = models.IntegerField(default=0)
    sms_failed_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.get_recipient_type_display()}"
    
    def get_recipients(self):
        """Get all recipients based on recipient_type"""
        recipients = []

        if self.recipient_type == 'MEMBER' and self.member:
            recipients = [self.member]
        elif self.recipient_type == 'MINISTRY' and self.ministry:
            recipients = Member.objects.active().filter(ministry=self.ministry)
        elif self.recipient_type == 'COMMITTEE' and self.committee:
            # Get members who are in this committee (same committee name)
            committee_members = Committee.objects.filter(Commitee_name=self.committee.Commitee_name).values_list('member', flat=True)
            recipients = Member.objects.active().filter(id__in=committee_members)
        elif self.recipient_type == 'COMMUNITY' and self.community:
            recipients = Member.objects.active().filter(shepherd=self.community)
        elif self.recipient_type == 'ALL':
            recipients = Member.objects.active()
        elif self.recipient_type == 'TITHE_PAYERS':
            # Get members who pay tithe
            recipients = Member.objects.active().filter(pays_tithe=True)
        elif self.recipient_type == 'CUSTOM_PHONES':
            # Custom phone numbers - return empty list, handled in get_phone_numbers()
            recipients = []

        return recipients
    
    def get_phone_numbers(self):
        """Extract valid phone numbers from recipients"""
        # Handle custom phone numbers list
        if self.recipient_type == 'CUSTOM_PHONES' and self.custom_phone_numbers:
            import re
            phones = re.split(r'[,;\n]', self.custom_phone_numbers)
            return [p.strip() for p in phones if p.strip() and len(p.strip()) > 5]

        recipients = self.get_recipients()
        phone_numbers = []

        for recipient in recipients:
            # Handle Member objects (they have 'telephone' field)
            if hasattr(recipient, 'telephone') and recipient.telephone:
                phone_str = str(recipient.telephone)
                if phone_str and len(phone_str) > 5:
                    phone_numbers.append(phone_str)

        return phone_numbers
    
    def get_target_users(self):
        """
        Get target users for portal/app notifications based on target_audience.
        This returns User queryset for real-time notification delivery.
        """
        from users.models import User, ChurchMember
        
        users = User.objects.filter(is_active=True)
        
        if self.target_audience == 'STAFF_ONLY':
            users = users.filter(is_staff=True)
        elif self.target_audience == 'MEMBERS_ONLY':
            # Users with church_member role or regular members (not staff)
            users = users.filter(is_staff=False)
        elif self.target_audience == 'PORTAL_ONLY':
            # Only users who have a linked ChurchMember portal account
            users = users.filter(church_member__isnull=False, church_member__is_portal_active=True)
        
        return users.distinct()
    
    def create_user_notifications(self):
        """
        Create UserNotification records for all target users.
        Called when notification is sent to enable real-time tracking.
        """
        from .utils import broadcast_notification
        
        target_users = self.get_target_users()
        user_notifications = []
        
        for user in target_users:
            user_notifications.append(
                UserNotification(
                    user=user,
                    notification=self,
                    is_read=False,
                    is_sent_via_websocket=False
                )
            )
        
        if user_notifications:
            UserNotification.objects.bulk_create(
                user_notifications,
                ignore_conflicts=True
            )
            
            # Broadcast to WebSocket groups
            broadcast_notification(self)
        
        return len(user_notifications)


class NotificationLog(models.Model):
    """Track individual SMS sends"""
    notification = models.ForeignKey(
        Notification, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default='PENDING')
    at_message_id = models.CharField(max_length=255, null=True, blank=True)
    cost = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification.title} -> {self.member.name}"
    

class NotificationReadStatus(models.Model):
    """Track which users have read which notifications"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='read_status')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_reads')
    read_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=True)  # Since this is created when read
    
    class Meta:
        unique_together = ['notification', 'user']  # One read status per user per notification
        ordering = ['-read_at']
    
    def __str__(self):
        return f"{self.user.username} read {self.notification.title}"


class UserNotification(models.Model):
    """
    Track individual notifications for each user.
    This allows for real-time notifications and per-user read status.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_notifications'
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='user_notifications'
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_sent_via_websocket = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'notification']
        ordering = ['-sent_at']
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title}"
    
    def mark_as_read(self):
        """Mark this notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class IncomingSMS(models.Model):
    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20)
    text = models.TextField()
    date = models.CharField(max_length=50)  # Africa's Talking sends as string
    message_id = models.CharField(max_length=50, unique=True)  # Prevent duplicates
    link_id = models.CharField(max_length=50, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, null=True)
    processed = models.BooleanField(default=False)  # Track if processed

    def __str__(self):
        return f"SMS from {self.from_number} to {self.to_number}"

    class Meta:
        verbose_name = 'Incoming SMS'
        verbose_name_plural = 'Incoming SMS'
        ordering = ['-received_at']

class DeliveryReport(models.Model):
    phone_number   = models.CharField(max_length=20)
    message_id     = models.CharField(max_length=100)
    status         = models.CharField(max_length=50)  # Success / Failed
    network_code   = models.CharField(max_length=20, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    received_at    = models.DateTimeField(auto_now_add=True)
    
    # Link to original notification log for better tracking
    notification_log = models.ForeignKey(
        'NotificationLog', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='delivery_reports'
    )

    def __str__(self):
        return f"{self.phone_number} - {self.status}"