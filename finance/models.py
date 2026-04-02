from django.db import models
from django.utils import timezone
from users.models import User
from member.models import Member
from events.models import Event

# Create your models here.

class Category(models.Model):
    TYPE_CHOICES = [
        ('OFFERING', 'Offering'),
        ('OFFERING_GRATITUDE', 'Offering_gratitude'),
        ('TITHE','Tithe'),
        ('SALARY', 'Salary'),
        ('ALLOWANCE', 'Allowance'),
        ('BONUS', 'Bonus'),
        ('UTILITIES', 'Utilities'),
        ('MAINTENANCE', 'Maintenance'),
        ('EVENTS', 'Events'),
        ('MISSIONS', 'Missions'),
        ('OTHERS','Others')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=57, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.type})"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='COMPLETED')
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.type}: ${self.amount} - {self.description[:30]}"


class TitheReceipt(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('mobile', 'Mobile Money'),
        ('cheque', 'Cheque'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tithe_receipts')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='tithe_receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='cash')
    date = models.DateTimeField(default=timezone.now)
    receipt_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.member.name} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate unique receipt number
            last_receipt = TitheReceipt.objects.filter(
                date__year=timezone.now().year,
                date__month=timezone.now().month
            ).order_by('receipt_number').last()
            
            if last_receipt:
                last_number = int(last_receipt.receipt_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.receipt_number = f"RCT-{timezone.now().strftime('%Y%m')}-{new_number:04d}"
        
        super().save(*args, **kwargs)


class Employee(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ON_LEAVE', 'On Leave'),
    ]
    
    PAYMENT_TYPE = [
        ('MONTHLY', 'Monthly'),
        ('WEEKLY', 'Weekly'),
        ('BI_WEEKLY', 'Bi-Weekly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='employment')
    employee_id = models.CharField(max_length=20, unique=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, null=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default='MONTHLY')
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    hire_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.name} - {self.position}"
    
    @property
    def total_salary(self):
        return self.base_salary + self.housing_allowance + self.transport_allowance + self.other_allowances


class Payroll(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payrolls')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-pay_period_end', '-created_at']
        unique_together = ['employee', 'pay_period_start', 'pay_period_end']
    
    def __str__(self):
        return f"{self.employee.member.name} - {self.pay_period_end} - {self.net_salary}"


class Budget(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - ${self.total_amount}"
    
    @property
    def spent_amount(self):
        return self.allocations.aggregate(total=models.Sum('spent_amount'))['total'] or 0
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.spent_amount


class BudgetAllocation(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='allocations')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    allocated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['budget', 'category']
        ordering = ['category__name']
    
    def __str__(self):
        return f"{self.budget.name} - {self.category.name}: ${self.allocated_amount}"
    
    @property
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount


class ExpenseReport(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REIMBURSED', 'Reimbursed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_reports')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='expense_reports', blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_submitted = models.DateField(auto_now_add=True)
    date_approved = models.DateField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='approved_expenses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_submitted', '-created_at']
    
    def __str__(self):
        return f"{self.title} - ${self.total_amount}"


class ExpenseItem(models.Model):
    expense_report = models.ForeignKey(ExpenseReport, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_incurred = models.DateField()
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date_incurred', '-created_at']
    
    def __str__(self):
        return f"{self.description} - ${self.amount}"


class EventPledge(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pledges')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='pledges')
    # Member is now optional - can be null for external pledgers
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='pledges', blank=True, null=True)
    # Fields for external/non-member pledgers
    external_name = models.CharField(max_length=255, blank=True, null=True, help_text='Name for non-member pledgers')
    external_phone = models.CharField(max_length=20, blank=True, null=True, help_text='Phone for non-member pledgers')
    promised_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(blank=True, null=True, help_text='Deadline to complete the pledge')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    last_reminder_date = models.DateTimeField(blank=True, null=True)
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Event Pledge'
        verbose_name_plural = 'Event Pledges'
        # Allow multiple pledges per event, but not duplicate member+event or external+event
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'member'],
                condition=models.Q(member__isnull=False),
                name='unique_member_event_pledge'
            ),
            models.UniqueConstraint(
                fields=['event', 'external_name', 'external_phone'],
                condition=models.Q(member__isnull=True),
                name='unique_external_event_pledge'
            ),
        ]
    
    def __str__(self):
        pledger = self.member.name if self.member else self.external_name or 'Unknown'
        return f"{pledger} - {self.promised_amount} for {self.event.title}"
    
    @property
    def pledger_name(self):
        return self.member.name if self.member else self.external_name or 'Unknown'
    
    @property
    def pledger_phone(self):
        if self.member and self.member.telephone:
            return str(self.member.telephone)
        return self.external_phone
    
    @property
    def remaining_amount(self):
        return self.promised_amount - self.paid_amount
    
    @property
    def progress_percentage(self):
        if self.promised_amount > 0:
            return (self.paid_amount / self.promised_amount) * 100
        return 0
    
    def update_status(self):
        if self.paid_amount >= self.promised_amount:
            self.status = 'COMPLETED'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        elif self.due_date and timezone.now().date() > self.due_date:
            self.status = 'OVERDUE'
        else:
            self.status = 'PENDING'
        self.save()
    
    def send_reminder_sms(self):
        from tithe.sms_api.africastalking import SMS
        remaining = self.remaining_amount
        phone = self.pledger_phone
        
        if remaining > 0 and phone:
            message = f"Dear {self.pledger_name}, this is a reminder that you pledged {self.promised_amount} for {self.event.title}. Remaining balance: {remaining}. Due: {self.due_date or 'ASAP'}. Thank you! - Christ King Church"
            try:
                SMS.send_sms(phone.as_e164 if hasattr(phone, 'as_e164') else str(phone), message)
                self.reminder_sent = True
                self.last_reminder_date = timezone.now()
                self.save()
                return True
            except Exception as e:
                print(f"SMS Error: {e}")
                return False
        return False
    
    def send_payment_notification(self, payment_amount):
        from tithe.sms_api.africastalking import SMS
        phone = self.pledger_phone
        
        if phone:
            total_paid = self.paid_amount
            remaining = self.remaining_amount
            message = f"Dear {self.pledger_name}, thank you for your contribution of {payment_amount} for {self.event.title}. Total paid: {total_paid}. Remaining: {remaining}. God bless you! - Christ King Church"
            try:
                SMS.send_sms(phone.as_e164 if hasattr(phone, 'as_e164') else str(phone), message)
                self.notification_sent = True
                self.save()
                return True
            except Exception as e:
                print(f"SMS Error: {e}")
                return False
        return False


class PledgePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    ]
    
    pledge = models.ForeignKey(EventPledge, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_date = models.DateField(default=timezone.now)
    received_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pledge_payments')
    notes = models.TextField(blank=True, null=True)
    sms_notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"{self.pledge.member.name} - {self.amount} on {self.payment_date}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update pledge paid_amount
        if is_new:
            pledge = self.pledge
            pledge.paid_amount = pledge.payments.aggregate(total=models.Sum('amount'))['total'] or 0
            pledge.update_status()
            
            # Send notification SMS
            if not self.sms_notification_sent:
                success = pledge.send_payment_notification(self.amount)
                if success:
                    self.sms_notification_sent = True
                    super().save(update_fields=['sms_notification_sent'])