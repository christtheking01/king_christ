from django.db import models
from users.models import User
from django.utils import timezone
from member.models import Member, Ministry, Community

class Notification(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENDING', 'Sending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]
    
    RECIPIENT_TYPE_CHOICES = [
        ('MEMBER', 'Individual Member'),
        ('MINISTRY', 'Ministry Members'),
        ('COMMUNITY', 'Community Members'),
        ('ALL', 'All Active Members'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField(help_text="Message content (max 160 characters for single SMS)")
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE_CHOICES)
    
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
    community = models.ForeignKey(
        Community, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='notifications'
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
        elif self.recipient_type == 'COMMUNITY' and self.community:
            recipients = Member.objects.active().filter(shepherd=self.community)
        elif self.recipient_type == 'ALL':
            recipients = Member.objects.active()
        
        return recipients
    
    def get_phone_numbers(self):
        """Extract valid phone numbers from recipients"""
        recipients = self.get_recipients()
        phone_numbers = []
        
        for recipient in recipients:
            if recipient.telephone:
                phone_str = str(recipient.telephone)
                if phone_str and len(phone_str) > 5:
                    phone_numbers.append(phone_str)
        
        return phone_numbers


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