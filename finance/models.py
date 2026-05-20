from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from users.models import User
from member.models import Member
from events.models import Event
from .base_models import AuditableModelWithManager

# Create your models here.

class Category(AuditableModelWithManager):
    TYPE_CHOICES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
    ]
    
    INCOME_SUBCATEGORIES = [
        ('OFFERING', 'Offerings'),
        ('TITHE', 'Tithes'),
        ('DONATIONS', 'Donations'),
        ('INVESTMENT', 'Investment Income'),
        ('RENTAL', 'Rental Income'),
        ('EVENT_FEES', 'Event Fees'),
        ('OTHER_INCOME', 'Other Income'),
    ]
    
    EXPENSE_SUBCATEGORIES = [
        ('SALARIES', 'Salaries & Wages'),
        ('BENEFITS', 'Employee Benefits'),
        ('UTILITIES', 'Utilities'),
        ('MAINTENANCE', 'Maintenance & Repairs'),
        ('OFFICE_SUPPLIES', 'Office Supplies'),
        ('MARKETING', 'Marketing & Outreach'),
        ('INSURANCE', 'Insurance'),
        ('TAXES', 'Taxes'),
        ('DEPRECIATION', 'Depreciation'),
        ('INTEREST', 'Interest Expense'),
        ('PROGRAMS', 'Program Expenses'),
        ('MISSIONS', 'Mission Expenses'),
        ('OTHER_EXPENSE', 'Other Expenses'),
    ]
    
    ASSET_SUBCATEGORIES = [
        ('CASH', 'Cash & Cash Equivalents'),
        ('ACCOUNTS_RECEIVABLE', 'Accounts Receivable'),
        ('INVENTORY', 'Inventory'),
        ('PREPAID', 'Prepaid Expenses'),
        ('PROPERTY', 'Property & Equipment'),
        ('INVESTMENTS', 'Investments'),
        ('INTANGIBLE', 'Intangible Assets'),
    ]
    
    LIABILITY_SUBCATEGORIES = [
        ('ACCOUNTS_PAYABLE', 'Accounts Payable'),
        ('ACCRUED_EXPENSES', 'Accrued Expenses'),
        ('SHORT_TERM_DEBT', 'Short-term Debt'),
        ('LONG_TERM_DEBT', 'Long-term Debt'),
        ('DEFERRED_REVENUE', 'Deferred Revenue'),
    ]
    
    EQUITY_SUBCATEGORIES = [
        ('MEMBER_CONTRIBUTIONS', 'Member Contributions'),
        ('RETAINED_EARNINGS', 'Retained Earnings'),
        ('NET_ASSETS', 'Net Assets'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subcategory = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    budget_code = models.CharField(max_length=20, blank=True, null=True, help_text='Standard accounting code for budget tracking')
    department = models.CharField(max_length=100, blank=True, null=True, help_text='Department responsible for this category')
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['type', 'name']
        unique_together = ['user', 'name', 'type']
        indexes = [
            models.Index(fields=['user', 'type', 'is_active']),
            models.Index(fields=['budget_code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def get_subcategory_choices(self):
        if self.type == 'INCOME':
            return self.INCOME_SUBCATEGORIES
        elif self.type == 'EXPENSE':
            return self.EXPENSE_SUBCATEGORIES
        elif self.type == 'ASSET':
            return self.ASSET_SUBCATEGORIES
        elif self.type == 'LIABILITY':
            return self.LIABILITY_SUBCATEGORIES
        elif self.type == 'EQUITY':
            return self.EQUITY_SUBCATEGORIES
        return []
    
    @property
    def full_code(self):
        if self.budget_code:
            return f"{self.type}-{self.budget_code}"
        return self.type


class Transaction(AuditableModelWithManager):
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
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.type}: ${self.amount} - {self.description[:30]}"


class TitheReceipt(AuditableModelWithManager):
    PAYMENT_STATUS_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('mobile', 'Mobile Money'),
        ('cheque', 'Cheque'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tithe_receipts')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='tithe_receipts')
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Amount must be greater than 0')]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='cash')
    date = models.DateTimeField(default=timezone.now)
    receipt_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.member.name} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            from django.db import transaction, IntegrityError
            import random
            import string
            
            # Generate unique receipt number using timestamp + random for guaranteed uniqueness
            max_retries = 100
            prefix = f"RCT-{timezone.now().strftime('%Y%m')}-"
            
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        # Use timestamp + random component for guaranteed uniqueness
                        timestamp = int(timezone.now().timestamp() * 1000)
                        random_suffix = ''.join(random.choices(string.digits, k=4))
                        self.receipt_number = f"{prefix}{timestamp}{random_suffix}"
                        
                        # Double-check it doesn't exist
                        if TitheReceipt.objects.filter(receipt_number=self.receipt_number).exists():
                            continue
                        
                        super().save(*args, **kwargs)
                        break
                except IntegrityError:
                    if attempt < max_retries - 1:
                        continue
                    raise
        else:
            super().save(*args, **kwargs)


class Offering(AuditableModelWithManager):
    """Sunday/weekly offerings separate from tithes"""
    
    OFFERING_TYPE_CHOICES = [
        ('SUNDAY', 'Sunday Collection'),
        ('SPECIAL', 'Special Collection'),
        ('THANKSGIVING', 'Thanksgiving'),
        ('BUILDING', 'Building Fund'),
        ('MISSIONS', 'Missions'),
        ('CHARITY', 'Charity'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
        ('CHEQUE', 'Cheque'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offerings')
    offering_type = models.CharField(max_length=20, choices=OFFERING_TYPE_CHOICES, default='SUNDAY')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Amount must be greater than 0')]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    
    # Optional donor info (anonymous allowed)
    donor_name = models.CharField(max_length=255, blank=True, null=True, help_text='Leave blank for anonymous')
    donor_phone = models.CharField(max_length=20, blank=True, null=True)
    is_anonymous = models.BooleanField(default=False, help_text='Check if donor wishes to remain anonymous')
    
    # Link to member if donor is a registered member
    member = models.ForeignKey(
        Member, 
        on_delete=models.SET_NULL, 
        related_name='offerings', 
        blank=True, 
        null=True,
        help_text='If donor is a registered member'
    )
    
    notes = models.TextField(blank=True, null=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Offering'
        verbose_name_plural = 'Offerings'
    
    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous {self.get_offering_type_display()} - {self.amount}"
        return f"{self.donor_name or self.member.name if self.member else 'Unknown'} - {self.get_offering_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            from django.db import transaction, IntegrityError
            import random
            import string
            
            # Generate unique receipt number using timestamp + random for guaranteed uniqueness
            max_retries = 100
            prefix = f"OFF-{timezone.now().strftime('%Y%m')}-"
            
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        # Use timestamp + random component for guaranteed uniqueness
                        # This avoids race conditions with sequential numbering
                        timestamp = int(timezone.now().timestamp() * 1000)
                        random_suffix = ''.join(random.choices(string.digits, k=4))
                        self.receipt_number = f"{prefix}{timestamp}{random_suffix}"
                        
                        # Double-check it doesn't exist (extremely unlikely but possible)
                        if Offering.objects.filter(receipt_number=self.receipt_number).exists():
                            continue  # Retry with new random suffix
                        
                        super().save(*args, **kwargs)
                        break
                except IntegrityError:
                    if attempt < max_retries - 1:
                        continue
                    raise
        else:
            super().save(*args, **kwargs)


class Employee(AuditableModelWithManager):
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
    name = models.CharField(max_length=255,default='Unknown')
    employee_id = models.CharField(max_length=20, unique=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, null=True)
    base_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, 'Salary cannot be negative')]
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE, default='MONTHLY')
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    hire_date = models.DateField()
    
    class Meta: 
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.position}"

    @property
    def total_salary(self):
        return self.base_salary


class Payroll(AuditableModelWithManager):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PENDING_VERIFICATION', 'Pending Verification'),
        ('VERIFIED', 'Verified'),
        ('APPROVED', 'Approved'),
        ('PROCESSED', 'Processed'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payrolls')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, 'Salary cannot be negative')]
    )
    gross_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0, 'Gross salary cannot be negative')]
    )
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
        ('CHEQUE', 'Cheque'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='CASH'
    )
    tax_deduction = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0, 'Tax cannot be negative')]
    )
    other_deductions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0, 'Deductions cannot be negative')]
    )
    net_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0, 'Net salary cannot be negative')]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Verification workflow (for priest/chairperson)
    submitted_for_verification = models.BooleanField(default=False)
    submitted_for_verification_at = models.DateTimeField(blank=True, null=True)
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='submitted_payrolls'
    )
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_payrolls'
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Approval workflow
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_payrolls'
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-pay_period_end', '-created_at']
        unique_together = ['employee', 'pay_period_start', 'pay_period_end']
    
    def __str__(self):
        return f"{self.employee.name} - {self.pay_period_end} - {self.net_salary}"


class Budget(AuditableModelWithManager):
    TYPE_CHOICES = [
        ('OPERATING', 'Operating Budget'),
        ('CAPITAL', 'Capital Budget'),
        ('PROGRAM', 'Program Budget'),
        ('EVENT', 'Event Budget'),
        ('MISSION', 'Mission Budget'),
        ('EMERGENCY', 'Emergency Fund'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    FISCAL_YEAR_CHOICES = [
        ('JAN_DEC', 'January - December'),
        ('JUL_JUN', 'July - June'),
        ('OCT_SEP', 'October - September'),
        ('CUSTOM', 'Custom Period'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    budget_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='OPERATING')
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Budget amount must be greater than 0')]
    )
    approved_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        blank=True, 
        null=True,
        help_text='Final approved amount after review'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    fiscal_year = models.CharField(max_length=4, blank=True, null=True, help_text='Fiscal year (e.g., 2024)')
    fiscal_period = models.CharField(max_length=10, choices=FISCAL_YEAR_CHOICES, default='JAN_DEC')
    
    # Approval workflow
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='submitted_budgets'
    )
    submitted_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_budgets'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Budget tracking
    variance_threshold = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.0,
        help_text='Variance threshold percentage for alerts'
    )
    requires_monthly_review = models.BooleanField(default=True)
    auto_carry_forward = models.BooleanField(default=False, help_text='Automatically carry forward unspent amounts')
    
    # Department/Division tracking
    department = models.CharField(max_length=100, blank=True, null=True)
    budget_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='managed_budgets'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'start_date']),
            models.Index(fields=['budget_type', 'fiscal_year']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.name} - ${self.total_amount} ({self.get_status_display()})"
    
    @property
    def allocated_amount(self):
        return self.allocations.aggregate(total=models.Sum('allocated_amount'))['total'] or 0
    
    @property
    def spent_amount(self):
        return self.allocations.aggregate(total=models.Sum('spent_amount'))['total'] or 0
    
    @property
    def remaining_amount(self):
        return (self.approved_amount or self.total_amount) - self.spent_amount
    
    @property
    def usage_percentage(self):
        budget_total = self.approved_amount or self.total_amount
        if budget_total > 0:
            return (self.spent_amount / budget_total) * 100
        return 0
    
    @property
    def variance_amount(self):
        return self.allocated_amount - self.spent_amount
    
    @property
    def variance_percentage(self):
        if self.allocated_amount > 0:
            return abs((self.spent_amount - self.allocated_amount) / self.allocated_amount) * 100
        return 0
    
    @property
    def is_over_budget(self):
        return self.spent_amount > (self.approved_amount or self.total_amount)
    
    @property
    def days_remaining(self):
        return (self.end_date - timezone.now().date()).days
    
    @property
    def is_expired(self):
        return timezone.now().date() > self.end_date
    
    def submit_for_approval(self, submitted_by_user):
        if self.status == 'DRAFT':
            self.status = 'PENDING_APPROVAL'
            self.submitted_by = submitted_by_user
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False
    
    def approve(self, approved_by_user, approved_amount=None):
        if self.status == 'PENDING_APPROVAL':
            self.status = 'ACTIVE'
            self.approved_by = approved_by_user
            self.approved_at = timezone.now()
            if approved_amount:
                self.approved_amount = approved_amount
            else:
                self.approved_amount = self.total_amount
            self.save()
            return True
        return False
    
    def reject(self, approved_by_user, reason):
        if self.status == 'PENDING_APPROVAL':
            self.status = 'CANCELLED'
            self.approved_by = approved_by_user
            self.approved_at = timezone.now()
            self.rejection_reason = reason
            self.save()
            return True
        return False


class BudgetAllocation(AuditableModelWithManager):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='allocations')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    allocated_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0, 'Allocated amount cannot be negative')]
    )
    spent_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0, 'Spent amount cannot be negative')]
    )
    committed_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text='Amount committed but not yet spent'
    )
    
    # Budget period tracking
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    
    # Approval and control
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_allocations'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    
    # Variance tracking
    original_allocation = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text='Original allocation amount for tracking changes'
    )
    variance_reason = models.TextField(blank=True, null=True, help_text='Reason for allocation variance')
    
    # Monthly tracking
    january = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    february = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    march = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    april = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    may = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    june = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    july = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    august = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    september = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    october = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    november = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    december = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['budget', 'category']
        ordering = ['category__name']
        indexes = [
            models.Index(fields=['budget', 'category']),
            models.Index(fields=['allocated_amount']),
        ]
    
    def __str__(self):
        return f"{self.budget.name} - {self.category.name}: ${self.allocated_amount}"
    
    @property
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount
    
    @property
    def available_amount(self):
        return self.allocated_amount - self.spent_amount - self.committed_amount
    
    @property
    def usage_percentage(self):
        if self.allocated_amount > 0:
            return (self.spent_amount / self.allocated_amount) * 100
        return 0
    
    @property
    def commitment_percentage(self):
        if self.allocated_amount > 0:
            return (self.committed_amount / self.allocated_amount) * 100
        return 0
    
    @property
    def total_utilization(self):
        if self.allocated_amount > 0:
            return ((self.spent_amount + self.committed_amount) / self.allocated_amount) * 100
        return 0
    
    @property
    def variance_amount(self):
        if self.original_allocation:
            return self.allocated_amount - self.original_allocation
        return 0
    
    @property
    def variance_percentage(self):
        if self.original_allocation and self.original_allocation > 0:
            return (abs(self.allocated_amount - self.original_allocation) / self.original_allocation) * 100
        return 0
    
    @property
    def is_over_allocated(self):
        return (self.spent_amount + self.committed_amount) > self.allocated_amount
    
    def get_month_amount(self, month):
        month_fields = {
            1: self.january, 2: self.february, 3: self.march,
            4: self.april, 5: self.may, 6: self.june,
            7: self.july, 8: self.august, 9: self.september,
            10: self.october, 11: self.november, 12: self.december
        }
        return month_fields.get(month, 0)
    
    def set_month_amount(self, month, amount):
        month_fields = {
            1: 'january', 2: 'february', 3: 'march',
            4: 'april', 5: 'may', 6: 'june',
            7: 'july', 8: 'august', 9: 'september',
            10: 'october', 11: 'november', 12: 'december'
        }
        if month in month_fields:
            setattr(self, month_fields[month], amount)
    
    def update_spent_amount(self):
        """Update spent amount based on related transactions"""
        from django.db.models import Sum
        
        # Get all transactions for this category within budget period
        transactions = Transaction.objects.filter(
            category=self.category,
            date__gte=self.budget.start_date,
            date__lte=self.budget.end_date,
            status='COMPLETED',
            type='Expense'
        )
        
        total_spent = transactions.aggregate(total=Sum('amount'))['total'] or 0
        self.spent_amount = total_spent
        self.save(update_fields=['spent_amount'])
    
    def commit_amount(self, amount, reason=""):
        """Commit an amount for future spending"""
        if self.available_amount >= amount:
            self.committed_amount += amount
            self.save()
            return True
        return False
    
    def uncommit_amount(self, amount):
        """Uncommit an amount"""
        if self.committed_amount >= amount:
            self.committed_amount -= amount
            self.save()
            return True
        return False
    
    def spend_committed(self, amount):
        """Convert committed amount to spent amount"""
        if self.committed_amount >= amount:
            self.committed_amount -= amount
            self.spent_amount += amount
            self.save()
            return True
        return False


class BudgetVariance(AuditableModelWithManager):
    VARIANCE_TYPES = [
        ('BUDGET_VS_ACTUAL', 'Budget vs Actual'),
        ('PERIOD_COMPARISON', 'Period Comparison'),
        ('FORECAST_VS_ACTUAL', 'Forecast vs Actual'),
        ('ALLOCATION_VARIANCE', 'Allocation Variance'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='variances')
    allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE, null=True, blank=True, related_name='variances')
    variance_type = models.CharField(max_length=30, choices=VARIANCE_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    
    # Variance amounts
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2)
    variance_amount = models.DecimalField(max_digits=15, decimal_places=2)
    variance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Analysis
    description = models.TextField(help_text='Description of the variance')
    causes = models.TextField(blank=True, null=True, help_text='Root causes of the variance')
    impact_assessment = models.TextField(blank=True, null=True, help_text='Impact on overall budget')
    corrective_actions = models.TextField(blank=True, null=True, help_text='Recommended corrective actions')
    
    # Tracking
    period_start = models.DateField()
    period_end = models.DateField()
    detected_date = models.DateTimeField(auto_now_add=True)
    resolved_date = models.DateTimeField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    
    # Responsibility
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_variances')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_variances')
    
    class Meta:
        ordering = ['-detected_date']
        indexes = [
            models.Index(fields=['budget', 'variance_type', 'severity']),
            models.Index(fields=['detected_date']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.budget.name} - {self.variance_type}: {self.variance_percentage}%"


class BudgetPeriod(AuditableModelWithManager):
    PERIOD_TYPES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
        ('CUSTOM', 'Custom'),
    ]
    
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='periods')
    name = models.CharField(max_length=100, help_text='Period name (e.g., "Q1 2024", "January 2024")')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Budget amounts for this period
    planned_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    committed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status tracking
    is_closed = models.BooleanField(default=False)
    closed_date = models.DateTimeField(blank=True, null=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_periods')
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['start_date']
        unique_together = ['budget', 'start_date', 'end_date']
        indexes = [
            models.Index(fields=['budget', 'period_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.budget.name} - {self.name}"
    
    @property
    def variance_amount(self):
        return self.actual_amount - self.planned_amount
    
    @property
    def variance_percentage(self):
        if self.planned_amount > 0:
            return (self.variance_amount / self.planned_amount) * 100
        return 0
    
    @property
    def remaining_amount(self):
        return self.planned_amount - self.actual_amount


class BudgetTransfer(AuditableModelWithManager):
    TRANSFER_TYPES = [
        ('REALLOCATION', 'Reallocation'),
        ('BORROW', 'Borrow from Another Budget'),
        ('EMERGENCY', 'Emergency Transfer'),
        ('ADJUSTMENT', 'Budget Adjustment'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    source_budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transfer_outs')
    target_budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transfer_ins')
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    reason = models.TextField(help_text='Reason for the transfer')
    
    # Category-specific transfer (optional)
    source_allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE, null=True, blank=True, related_name='transfer_outs')
    target_allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE, null=True, blank=True, related_name='transfer_ins')
    
    # Approval workflow
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfer_requests')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transfers')
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Execution
    executed_at = models.DateTimeField(blank=True, null=True)
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='executed_transfers')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_budget', 'status']),
            models.Index(fields=['target_budget', 'status']),
            models.Index(fields=['transfer_type']),
        ]
    
    def __str__(self):
        return f"{self.source_budget.name} → {self.target_budget.name}: ${self.amount}"


class BudgetAlert(AuditableModelWithManager):
    ALERT_TYPES = [
        ('OVER_BUDGET', 'Over Budget'),
        ('HIGH_UTILIZATION', 'High Utilization'),
        ('VARIANCE', 'Budget Variance'),
        ('EXPIRY', 'Budget Expiry'),
        ('PERIOD_END', 'Period Ending'),
        ('APPROVAL_NEEDED', 'Approval Needed'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='alerts')
    allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    
    # Notifications
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['budget', 'is_active', 'priority']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['is_acknowledged']),
        ]
    
    def __str__(self):
        return f"{self.budget.name} - {self.alert_type}: {self.title}"


class ExpenseReport(AuditableModelWithManager):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REIMBURSED', 'Reimbursed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_reports')
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='expense_reports', 
        blank=True, 
        null=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Amount must be greater than 0')]
    )
    date_submitted = models.DateField(auto_now_add=True)
    date_approved = models.DateField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='approved_expenses'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_submitted', '-created_at']
    
    def __str__(self):
        return f"{self.title} - ${self.total_amount}"


class ExpenseItem(AuditableModelWithManager):
    expense_report = models.ForeignKey(ExpenseReport, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Amount must be greater than 0')]
    )
    date_incurred = models.DateField()
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['date_incurred', '-created_at']
    
    def __str__(self):
        return f"{self.description} - ${self.amount}"


class EventPledge(AuditableModelWithManager):
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
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        related_name='pledges', 
        blank=True, 
        null=True
    )
    # Fields for external/non-member pledgers
    external_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text='Name for non-member pledgers'
    )
    external_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text='Phone for non-member pledgers'
    )
    promised_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Promised amount must be greater than 0')]
    )
    paid_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0, 'Paid amount cannot be negative')]
    )
    due_date = models.DateField(blank=True, null=True, help_text='Deadline to complete the pledge')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    last_reminder_date = models.DateTimeField(blank=True, null=True)
    notification_sent = models.BooleanField(default=False)
    
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
        """Send SMS reminder about pledge payment"""
        from tithe.sms_service import sms_service
        remaining = self.remaining_amount
        phone = self.pledger_phone
        
        if remaining > 0 and phone:
            message = f"Ndugu {self.pledger_name}, hii ni kikumbusho kuwa umeahidi {self.promised_amount} kwa ajili ya {self.event.title}. Salio lililobaki: {remaining}. Tarehe ya malipo: {self.due_date or 'MAPEMA'}. Asante!"
            try:
                phone_str = phone.as_e164 if hasattr(phone, 'as_e164') else str(phone)
                result = sms_service.send_sms(phone_str, message)
                
                if result.get('success'):
                    self.reminder_sent = True
                    self.last_reminder_date = timezone.now()
                    self.save(update_fields=['reminder_sent', 'last_reminder_date'])
                    return True
                return False
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"SMS Error sending reminder to {phone}: {e}")
                return False
        return False
    
    def send_payment_notification(self, payment_amount):
        """Send SMS notification about pledge payment received"""
        from tithe.sms_service import sms_service
        phone = self.pledger_phone
        
        if phone:
            total_paid = self.paid_amount
            remaining = self.remaining_amount
            message = f"Ndugu {self.pledger_name}, asante kwa mchango wako wa {payment_amount} kwa ajili ya {self.event.title}. Jumla iliyolipwa: {total_paid}. Salio lililobaki: {remaining}. Mungu akubariki!"
            try:
                phone_str = phone.as_e164 if hasattr(phone, 'as_e164') else str(phone)
                result = sms_service.send_sms(phone_str, message)
                
                if result.get('success'):
                    self.notification_sent = True
                    self.sms_notification_sent = True
                    self.save(update_fields=['notification_sent', 'sms_notification_sent'])
                    return True
                return False
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"SMS Error sending payment notification to {phone}: {e}")
                return False
        return False


class PledgePayment(AuditableModelWithManager):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    ]
    
    pledge = models.ForeignKey(EventPledge, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01, 'Payment amount must be greater than 0')]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_date = models.DateField(default=timezone.now)
    received_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pledge_payments')
    notes = models.TextField(blank=True, null=True)
    sms_notification_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"{self.pledge.pledger_name} - {self.amount} on {self.payment_date}"
    
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


class PledgeReceipt(AuditableModelWithManager):
    """Receipt for pledge payments"""
    pledge_payment = models.OneToOneField(
        PledgePayment,
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
    
    church_name = models.CharField(max_length=255, default="Parokia ya Kristo Mfalme")
    church_address = models.TextField(default="S.L.P 1310")
    church_phone = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Pledge Receipt"
        verbose_name_plural = "Pledge Receipts"
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.pledge_payment.pledge.pledger_name}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            from django.db import transaction, IntegrityError
            import random
            import string
            
            # Generate unique receipt number using timestamp + random for guaranteed uniqueness
            max_retries = 100
            today = timezone.now().date()
            prefix = f"PLDG-{today.strftime('%Y%m%d')}-"
            
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        # Use timestamp + random component for guaranteed uniqueness
                        timestamp = int(timezone.now().timestamp() * 1000)
                        random_suffix = ''.join(random.choices(string.digits, k=4))
                        self.receipt_number = f"{prefix}{timestamp}{random_suffix}"
                        
                        # Double-check it doesn't exist
                        if PledgeReceipt.objects.filter(receipt_number=self.receipt_number).exists():
                            continue
                        
                        super().save(*args, **kwargs)
                        break
                except IntegrityError:
                    if attempt < max_retries - 1:
                        continue
                    raise
        else:
            super().save(*args, **kwargs)
    
    def get_print_data(self):
        payment = self.pledge_payment
        pledge = payment.pledge
        
        return {
            'receipt_number': self.receipt_number,
            'pledger_name': pledge.pledger_name,
            'event_title': pledge.event.title if pledge.event else 'General Pledge',
            'phone_number': pledge.pledger_phone or '',
            'amount': f"{payment.amount:,.2f}",
            'payment_method': payment.get_payment_method_display(),
            'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
            'receipt_date': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'promised_amount': f"{pledge.promised_amount:,.2f}",
            'paid_amount': f"{pledge.paid_amount:,.2f}",
            'remaining_amount': f"{pledge.remaining_amount:,.2f}",
            'church_name': self.church_name,
            'church_address': self.church_address or '',
            'church_phone': self.church_phone or '',
        }
    
    def mark_printed(self):
        self.is_printed = True
        self.printed_at = timezone.now()
        self.print_attempts += 1
        self.save()