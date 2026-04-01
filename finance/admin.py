from django.contrib import admin
from finance.models import (
    Category, Transaction, Employee, Payroll, Budget, BudgetAllocation, ExpenseReport, 
    ExpenseItem, TitheReceipt)

# Register your models here.

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(Employee)
admin.site.register(Payroll)
admin.site.register(Budget) 
admin.site.register(BudgetAllocation)
admin.site.register(ExpenseReport)
admin.site.register(ExpenseItem)
admin.site.register(TitheReceipt)