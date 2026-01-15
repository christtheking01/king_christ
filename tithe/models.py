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
    contact_number = models.CharField(max_length=13)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=50, 
        choices=PAYMENT_STATUS_CHOICES,
        default='cash'
    )
    
    def __str__(self):
        return f"{self.name} - {self.amount} - {self.date.strftime('%Y-%m-%d')}"

    

class TitheReceipt(models.Model):
    # Link to existing TithePayment
    tithe_payment = models.OneToOneField(
        'TithePayment', 
        on_delete=models.CASCADE,
        related_name='receipt'
    )
    
    # Receipt Information
    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=255, blank=True, null=True)
    
    # Printing Status
    is_printed = models.BooleanField(default=False)
    printed_at = models.DateTimeField(blank=True, null=True)
    print_attempts = models.IntegerField(default=0)
    last_print_error = models.TextField(blank=True, null=True)
    
    # Church Information (Customize as needed)
    church_name = models.CharField(max_length=255, default="Your Church Name")
    church_address = models.TextField(default="Your Church Address")
    church_phone = models.CharField(max_length=20, default="+255 XXX XXX XXX")
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Tithe Receipt"
        verbose_name_plural = "Tithe Receipts"
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.tithe_payment.name}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number: TITH-YYYYMMDD-0001
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
        """Format data for printing from TithePayment"""
        payment = self.tithe_payment
        
        return {
            'receipt_number': self.receipt_number,
            'member_name': payment.name.get_full_name() if hasattr(payment.name, 'get_full_name') else str(payment.name),
            'member_id': getattr(payment.name, 'member_id', 'N/A'),
            'phone_number': payment.contact_number,
            'amount': f"{payment.amount:,.2f}",
            'payment_method': payment.get_status_display(),
            'payment_date': payment.date.strftime('%Y-%m-%d %H:%M:%S'),
            'receipt_date': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'church_name': self.church_name,
            'church_address': self.church_address,
            'church_phone': self.church_phone,
        }
    
    def mark_printed(self):
        """Mark receipt as printed"""
        self.is_printed = True
        self.printed_at = timezone.now()
        self.print_attempts += 1
        self.save()