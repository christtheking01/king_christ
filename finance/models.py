from django.db import models
from django.utils import timezone
from users.models import User
from member.models import Member

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