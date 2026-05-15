from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Transaction, Offering, TitheReceipt, Employee, Payroll, 
    Budget, BudgetAllocation, ExpenseReport, ExpenseItem, EventPledge, PledgePayment
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'user', 'created_at', 'created_by']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'type']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'type', 'amount', 'category', 'user', 'status', 'is_deleted']
    list_filter = ['type', 'status', 'date', 'is_deleted']
    search_fields = ['description', 'reference_number']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'deleted_at', 'deleted_by']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
    soft_delete_selected.short_description = "Soft delete selected transactions"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore_selected.short_description = "Restore selected transactions"


@admin.register(Offering)
class OfferingAdmin(admin.ModelAdmin):
    list_display = ['date', 'offering_type', 'amount', 'donor_name', 'is_anonymous', 'is_deleted']
    list_filter = ['offering_type', 'date', 'payment_method', 'is_anonymous', 'is_deleted']
    search_fields = ['donor_name', 'receipt_number', 'notes']
    readonly_fields = ['receipt_number', 'created_at', 'modified_at', 'created_by', 'modified_by']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
    soft_delete_selected.short_description = "Soft delete selected offerings"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore_selected.short_description = "Restore selected offerings"


@admin.register(TitheReceipt)
class TitheReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'member', 'amount', 'date', 'is_deleted']
    list_filter = ['date', 'payment_method', 'is_deleted']
    search_fields = ['receipt_number', 'member__name']
    readonly_fields = ['receipt_number', 'created_at', 'modified_at', 'created_by', 'modified_by']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name', 'position', 'department', 'base_salary', 'status', 'is_deleted']
    list_filter = ['status', 'department', 'payment_type', 'is_deleted']
    search_fields = ['employee_id', 'name', 'position']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by']
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'pay_period_start', 'pay_period_end', 'net_salary', 'status', 'approved_by']
    list_filter = ['status', 'pay_period_end', 'is_deleted']
    search_fields = ['employee__name']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'approved_at']
    date_hierarchy = 'pay_period_end'

    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'pay_period_start', 'pay_period_end')
        }),
        ('Salary Details', {
            'fields': ('basic_salary', 'gross_salary', 'net_salary')
        }),
        ('Payment Information', {
            'fields': ('payment_date',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'notes')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'modified_by', 'modified_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['approve_payroll', 'soft_delete_selected', 'restore_selected']
    
    def approve_payroll(self, request, queryset):
        for obj in queryset:
            obj.approve(request.user)
    approve_payroll.short_description = "Approve selected payrolls"
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
    soft_delete_selected.short_description = "Soft delete selected payrolls"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore_selected.short_description = "Restore selected payrolls"


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_amount', 'spent_amount', 'remaining_amount', 'status', 'approved_by']
    list_filter = ['status', 'start_date', 'is_deleted']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'approved_at']
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['approve_budget', 'soft_delete_selected', 'restore_selected']
    
    def approve_budget(self, request, queryset):
        for obj in queryset:
            obj.approve(request.user)
    approve_budget.short_description = "Approve selected budgets"
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
    soft_delete_selected.short_description = "Soft delete selected budgets"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore_selected.short_description = "Restore selected budgets"


@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = ['budget', 'category', 'allocated_amount', 'spent_amount', 'remaining_amount']
    list_filter = ['budget']
    search_fields = ['budget__name', 'category__name']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by']


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'total_amount', 'status', 'date_submitted', 'approved_by']
    list_filter = ['status', 'date_submitted', 'is_deleted']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'date_submitted']
    date_hierarchy = 'date_submitted'
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['approve_expense', 'reject_expense', 'soft_delete_selected', 'restore_selected']
    
    def approve_expense(self, request, queryset):
        for obj in queryset:
            obj.approve(request.user)
    approve_expense.short_description = "Approve selected expense reports"
    
    def reject_expense(self, request, queryset):
        for obj in queryset:
            obj.reject(request.user)
    reject_expense.short_description = "Reject selected expense reports"
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
    soft_delete_selected.short_description = "Soft delete selected expense reports"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore_selected.short_description = "Restore selected expense reports"


@admin.register(ExpenseItem)
class ExpenseItemAdmin(admin.ModelAdmin):
    list_display = ['expense_report', 'description', 'amount', 'date_incurred', 'category']
    list_filter = ['category', 'date_incurred']
    search_fields = ['description', 'receipt_number']
    readonly_fields = ['created_at', 'created_by', 'modified_by']


@admin.register(EventPledge)
class EventPledgeAdmin(admin.ModelAdmin):
    list_display = ['pledger_name', 'event', 'promised_amount', 'paid_amount', 'status', 'due_date', 'is_deleted']
    list_filter = ['status', 'due_date', 'event', 'is_deleted']
    search_fields = ['member__name', 'external_name', 'event__title']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'reminder_sent', 'last_reminder_date']
    date_hierarchy = 'due_date'
    
    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PledgePayment)
class PledgePaymentAdmin(admin.ModelAdmin):
    list_display = ['pledge', 'amount', 'payment_method', 'payment_date', 'received_by', 'sms_notification_sent']
    list_filter = ['payment_method', 'payment_date', 'sms_notification_sent']
    search_fields = ['pledge__member__name', 'pledge__external_name']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by']
    date_hierarchy = 'payment_date'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)