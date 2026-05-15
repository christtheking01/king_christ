from django.utils import timezone
from django.db import models
from member.models import Member
from . import sms_service

class TithePayment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank'), 
    ]
    
    # SMS tracking fields
    sms_sent = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    sms_message_id = models.CharField(max_length=100, blank=True, null=True)
    sms_failure_count = models.IntegerField(default=0)
    last_sms_error = models.TextField(blank=True, null=True)

    date = models.DateTimeField(default=timezone.now, verbose_name='Invoice Date')
    name = models.ForeignKey(Member, verbose_name="Member", on_delete=models.CASCADE)  # Direct reference
    contact_number = models.CharField(max_length=13, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=50, 
        choices=PAYMENT_STATUS_CHOICES,
        default='cash'
    )
    
    def __str__(self):
        return f"{self.name} - {self.amount} - {self.date.strftime('%Y-%m-%d')}"

    

class TitheReceipt(models.Model):
    tithe_payment = models.OneToOneField(
        'TithePayment',
        on_delete=models.CASCADE,
        related_name='receipt'
    )

    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=255, blank=True, null=True)

    is_printed = models.BooleanField(default=False)
    printed_at = models.DateTimeField(blank=True, null=True)
    print_attempts = models.IntegerField(default=0)
    last_print_error = models.TextField(blank=True, null=True)

    church_name = models.CharField(max_length=255, default="Christ The King Parish")
    church_address = models.TextField(default="")
    church_phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Tithe Receipt"
        verbose_name_plural = "Tithe Receipts"

    def __str__(self):
        # Member.name is a string field, not a related object
        return f"Receipt {self.receipt_number} - {self.tithe_payment.name.name}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            today = timezone.now().date()
            last_receipt = TitheReceipt.objects.filter(
                generated_at__date=today
            ).order_by('-id').first()

            if last_receipt and last_receipt.receipt_number:
                try:
                    last_number = int(last_receipt.receipt_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1

            self.receipt_number = f"TITH-{today.strftime('%Y%m%d')}-{new_number:04d}"

        super().save(*args, **kwargs)

    def get_print_data(self):
        payment = self.tithe_payment
        member = payment.name  # This is a Member instance

        # Member has a .name field (CharField), not get_full_name()
        member_name = member.name if hasattr(member, 'name') else str(member)

        return {
            'receipt_number': self.receipt_number,
            'member_name': member_name,
            'member_id': getattr(member, 'member_id', getattr(member, 'id', 'N/A')),
            'phone_number': payment.contact_number or '',
            'amount': f"{payment.amount:,.2f}",
            'payment_method': payment.get_status_display(),
            'payment_date': payment.date.strftime('%Y-%m-%d %H:%M:%S'),
            'receipt_date': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'church_name': self.church_name,
            'church_address': self.church_address or '',
            'church_phone': self.church_phone or '',
        }

    def mark_printed(self):
        self.is_printed = True
        self.printed_at = timezone.now()
        self.print_attempts += 1
        self.save()


class DeviceRegistration(models.Model):
    """Register mobile devices for push notifications and tracking"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=[
        ('android', 'Android'),
        ('ios', 'iOS'),
    ])
    push_token = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    app_version = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-last_seen']
        verbose_name = "Device Registration"
        verbose_name_plural = "Device Registrations"
    
    def __str__(self):
        return f"{self.device_name or self.device_id} - {self.user.username}"
    
    @classmethod
    def register_device(cls, user, device_id, device_type, push_token=None, device_name=None, app_version=None):
        """Register or update a device for a user"""
        device, created = cls.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_type': device_type,
                'push_token': push_token,
                'device_name': device_name,
                'app_version': app_version,
                'is_active': True,
                'last_seen': timezone.now(),
            }
        )
        return device, created


class SyncLog(models.Model):
    """Track data synchronization for mobile apps"""
    device = models.ForeignKey(DeviceRegistration, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=[
        ('members', 'Members'),
        ('payments', 'Payments'),
        ('settings', 'Settings'),
        ('full', 'Full Sync'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ], default='started')
    
    items_synced = models.IntegerField(default=0)
    total_items = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    sync_timestamp = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # For incremental sync
    last_sync_token = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-sync_timestamp']
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
    
    def __str__(self):
        return f"{self.device.device_name} - {self.sync_type} ({self.status})"
    
    def mark_completed(self, items_synced=None, error_message=None):
        """Mark sync as completed"""
        self.status = 'completed' if not error_message else 'failed'
        self.completed_at = timezone.now()
        if items_synced is not None:
            self.items_synced = items_synced
        if error_message:
            self.error_message = error_message
        self.save()


class OfflineOperation(models.Model):
    """Track operations performed offline that need to be synced"""
    device = models.ForeignKey(DeviceRegistration, on_delete=models.CASCADE, related_name='offline_operations')
    operation_type = models.CharField(max_length=20, choices=[
        ('create_payment', 'Create Payment'),
        ('update_member', 'Update Member'),
        ('create_member', 'Create Member'),
    ])
    data = models.JSONField()  # Store the operation data
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Sync'),
        ('synced', 'Synced'),
        ('failed', 'Failed Sync'),
        ('conflict', 'Conflict'),
    ], default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    sync_attempts = models.IntegerField(default=0)
    last_sync_attempt = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Conflict resolution
    server_data = models.JSONField(null=True, blank=True)
    resolved_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Offline Operation"
        verbose_name_plural = "Offline Operations"
    
    def __str__(self):
        return f"{self.device.device_name} - {self.operation_type} ({self.status})"
    
    def mark_synced(self):
        """Mark operation as successfully synced"""
        self.status = 'synced'
        self.sync_attempts += 1
        self.last_sync_attempt = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark sync attempt as failed"""
        self.status = 'failed'
        self.sync_attempts += 1
        self.last_sync_attempt = timezone.now()
        self.error_message = error_message
        self.save()