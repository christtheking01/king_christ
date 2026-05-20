from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from .models import (
    Category, Transaction, Offering, TitheReceipt, Employee, Payroll, Budget, BudgetAllocation, 
    ExpenseReport, ExpenseItem, EventPledge, PledgePayment, BudgetVariance, BudgetAlert, BudgetTransfer )
from member.models import Member
from events.models import Event
from django.db.models import ExpressionWrapper, FloatField,F
from .permissions import (
    ParishRoles, ParishPermissions, has_parish_permission, 
    require_parish_permission, PermissionMixin
)
import csv


# Leadership Approval Views
@login_required
def leadership_payroll_approvals(request):
    """Leadership view for payroll approvals - simplified for priests/admins"""
    # Check if user has leadership role
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    pending_payrolls = Payroll.objects.filter(status='PENDING_VERIFICATION').order_by('-submitted_for_verification_at')
    
    context = {
        'pending_payrolls': pending_payrolls,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_payroll_approvals.html', context)


@login_required
def leadership_payroll_detail(request, pk):
    """Leadership view for payroll detail with approval/reject and comments"""
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    payroll = get_object_or_404(Payroll, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            payroll.status = 'VERIFIED'
            payroll.verified_by = request.user
            payroll.verified_at = timezone.now()
            payroll.approver_comment = comment
            payroll.save()
            messages.success(request, f"Payroll for {payroll.employee.name} approved successfully")
        elif action == 'reject':
            payroll.status = 'REJECTED'
            payroll.verified_by = request.user
            payroll.verified_at = timezone.now()
            payroll.approver_comment = comment
            payroll.save()
            messages.success(request, f"Payroll for {payroll.employee.name} rejected")
        
        return redirect('finance:leadership_payroll_approvals')
    
    context = {
        'payroll': payroll,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_payroll_detail.html', context)


@login_required
def leadership_budget_approvals(request):
    """Leadership view for budget approvals - simplified for priests/admins"""
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    pending_budgets = Budget.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')
    
    context = {
        'pending_budgets': pending_budgets,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_budget_approvals.html', context)


@login_required
def leadership_budget_detail(request, pk):
    """Leadership view for budget detail with approval/reject and comments"""
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    budget = get_object_or_404(Budget, pk=pk)
    allocations = budget.allocations.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            budget.status = 'APPROVED'
            budget.approved_by = request.user
            budget.approved_at = timezone.now()
            budget.approver_comment = comment
            budget.save()
            messages.success(request, f"Budget '{budget.name}' approved successfully")
        elif action == 'reject':
            budget.status = 'REJECTED'
            budget.approved_by = request.user
            budget.approved_at = timezone.now()
            budget.approver_comment = comment
            budget.save()
            messages.success(request, f"Budget '{budget.name}' rejected")
        
        return redirect('finance:leadership_budget_approvals')
    
    context = {
        'budget': budget,
        'allocations': allocations,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_budget_detail.html', context)


@login_required
def leadership_expense_approvals(request):
    """Leadership view for expense report approvals - simplified for priests/admins"""
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    pending_expenses = ExpenseReport.objects.filter(status='PENDING').order_by('-date_submitted')
    
    context = {
        'pending_expenses': pending_expenses,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_expense_approvals.html', context)


@login_required
def leadership_expense_detail(request, pk):
    """Leadership view for expense report detail with approval/reject and comments"""
    if not (request.user.is_superuser or request.user.roles in ['priest', 'admin', 'chair_person', 'secretary']):
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    expense = get_object_or_404(ExpenseReport, pk=pk)
    items = expense.items.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            expense.status = 'APPROVED'
            expense.approved_by = request.user
            expense.date_approved = timezone.now()
            expense.notes = comment
            expense.save()
            messages.success(request, f"Expense report approved successfully")
        elif action == 'reject':
            expense.status = 'REJECTED'
            expense.approved_by = request.user
            expense.date_approved = timezone.now()
            expense.notes = comment
            expense.save()
            messages.success(request, f"Expense report rejected")
        
        return redirect('finance:leadership_expense_approvals')
    
    context = {
        'expense': expense,
        'items': items,
        'leadership_active': True,
    }
    return render(request, 'finance/leadership_expense_detail.html', context)


@login_required
def dashboard(request):
    # Enhanced dashboard with comprehensive financial overview
    transactions = Transaction.objects.filter(user=request.user)
    
    # Basic financial metrics
    total_income = transactions.filter(type='Income', status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = transactions.filter(type='Expense', status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expenses
    
    # Payroll metrics
    employees = Employee.objects.filter(user=request.user).order_by('-base_salary')
    total_monthly_payroll = employees.aggregate(total=Sum('base_salary'))['total'] or 0
    
    # Recent transactions
    recent_transactions = transactions[:10]
    
    # Current month budget status
    current_month = timezone.now().date().replace(day=1)
    active_budgets = Budget.objects.filter(
        user=request.user, 
        status='ACTIVE',
        start_date__lte=current_month,
        end_date__gte=current_month
    )
    
    # Pending expense reports
    pending_expenses = ExpenseReport.objects.filter(user=request.user, status='PENDING')
    
    # Upcoming payroll
    upcoming_payroll = Payroll.objects.filter(
        user=request.user, 
        status='PENDING',
        pay_period_end__gte=timezone.now().date()
    ).count()
    
    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'recent_transactions': recent_transactions,
        'employees_count': employees.count(),
        'total_monthly_payroll': total_monthly_payroll,
        'active_budgets_count': active_budgets.count(),
        'pending_expenses_count': pending_expenses.count(),
        'upcoming_payroll_count': upcoming_payroll,
        'finance_active': True,
    }
    return render(request, 'finance/enhanced_dashboard.html', context)


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-created_at')
    
    transaction_type = request.GET.get('type')
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')

    if transaction_type:
        transactions = transactions.filter(type=transaction_type)
    
    if status:
        transactions = transactions.filter(status=status)
    
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    
    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(user=request.user)
    
    context = {
        'page_obj': page_obj,
        'transactions': page_obj,
        'categories': categories,
        'finance_active': True,
    }
    return render(request, 'finance/transaction_list.html', context)


@login_required
def add_transaction(request):
    if request.method == 'POST':
        transaction_type = request.POST.get('type')
        category_id = request.POST.get('category')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        status = request.POST.get('status', 'COMPLETED')
        reference_number = request.POST.get('reference_number', '')
        
        category = get_object_or_404(Category, id=category_id, user=request.user)
        
        Transaction.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            category=category,
            type=transaction_type,
            amount=amount,
            description=description,
            date=date,
            status=status,
            reference_number=reference_number
        )
        
        messages.success(request, 'Transaction added successfully!')
        return redirect('transaction_list')
    
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/transaction_form.html', {
        'categories': categories,
        'finance_active': True,
    })


@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        transaction.type = request.POST.get('type')
        transaction.category_id = request.POST.get('category')
        transaction.amount = request.POST.get('amount')
        transaction.description = request.POST.get('description')
        transaction.date = request.POST.get('date')
        transaction.status = request.POST.get('status')
        transaction.reference_number = request.POST.get('reference_number')
        transaction.modified_by = request.user
        transaction.save()
        
        messages.success(request, 'Transaction updated successfully!')
        return redirect('transaction_list')
    
    categories = Category.objects.filter(user=request.user)
    context = {
        'transaction': transaction,
        'categories': categories,
        'finance_active': True,
    }
    return render(request, 'finance/transaction_form.html', context)


@login_required
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    transaction.soft_delete(request.user)
    messages.success(request, 'Transaction deleted successfully!')
    return redirect('transaction_list')


@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/category_list.html', {
        'categories': categories,
        'all_categories': categories,
        'finance_active': True,
    })


@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_type = request.POST.get('type')
        subcategory = request.POST.get('subcategory')
        description = request.POST.get('description')
        budget_code = request.POST.get('budget_code')
        department = request.POST.get('department')
        parent_category_id = request.POST.get('parent_category')
        is_active = request.POST.get('is_active') == 'on'

        if Category.objects.filter(user=request.user, name=name, type=category_type).exists():
            messages.error(request, 'Category with this name and type already exists!')
            return redirect('add_category')

        parent_category = None
        if parent_category_id:
            parent_category = get_object_or_404(Category, pk=parent_category_id, user=request.user)

        Category.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            name=name,
            type=category_type,
            subcategory=subcategory,
            description=description,
            budget_code=budget_code,
            department=department,
            parent_category=parent_category,
            is_active=is_active
        )

        messages.success(request, 'Category added successfully!')
        return redirect('category_list')

    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/category_form.html', {
        'all_categories': categories,
        'finance_active': True,
    })


@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.type = request.POST.get('type')
        category.subcategory = request.POST.get('subcategory')
        category.description = request.POST.get('description')
        category.budget_code = request.POST.get('budget_code')
        category.department = request.POST.get('department')
        parent_category_id = request.POST.get('parent_category')
        category.is_active = request.POST.get('is_active') == 'on'

        if parent_category_id:
            category.parent_category = get_object_or_404(Category, pk=parent_category_id, user=request.user)
        else:
            category.parent_category = None

        category.modified_by = request.user
        category.save()

        messages.success(request, 'Category updated successfully!')
        return redirect('category_list')

    categories = Category.objects.filter(user=request.user).exclude(pk=category.pk)
    return render(request, 'finance/category_form.html', {
        'category': category,
        'all_categories': categories,
        'finance_active': True,
    })


@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)

    if category.transactions.exists():
        messages.error(request, 'Cannot delete category with existing transactions!')
        return redirect('category_list')

    category.delete()
    messages.success(request, 'Category deleted successfully!')
    return redirect('category_list')


# ====== OFFERING MANAGEMENT ======

@login_required
def offering_list(request):
    """List all offerings with filtering"""
    offerings = Offering.objects.filter(user=request.user).order_by('-date', '-created_at')

    # Filter options
    offering_type = request.GET.get('type')
    payment_method = request.GET.get('payment_method')
    member_id = request.GET.get('member')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if offering_type:
        offerings = offerings.filter(offering_type=offering_type)
    if payment_method:
        offerings = offerings.filter(payment_method=payment_method)
    if member_id:
        offerings = offerings.filter(member_id=member_id)
    if start_date:
        offerings = offerings.filter(date__gte=start_date)
    if end_date:
        offerings = offerings.filter(date__lte=end_date)

    # Statistics (before pagination)
    total_amount = offerings.aggregate(total=Sum('amount'))['total'] or 0

    # Type breakdown (before pagination - uses the filtered queryset)
    type_breakdown = offerings.values('offering_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # Handle exports (before pagination)
    export_format = request.GET.get('export')
    if export_format == 'csv':
        from .exports import export_offerings_to_csv
        return export_offerings_to_csv(offerings)
    elif export_format == 'pdf':
        from .exports import export_offerings_to_pdf
        return export_offerings_to_pdf(offerings, {
            'total_amount': total_amount,
            'type_breakdown': type_breakdown,
            'filters': {
                'type': offering_type,
                'payment_method': payment_method,
                'member': member_id,
                'start_date': start_date,
                'end_date': end_date
            }
        })

    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(offerings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get members for filter
    members = Member.objects.filter(offerings__isnull=False).distinct()

    context = {
        'page_obj': page_obj,
        'offerings': page_obj,
        'total_amount': total_amount,
        'type_breakdown': type_breakdown,
        'members': members,
        'offering_types': Offering.OFFERING_TYPE_CHOICES,
        'payment_methods': Offering.PAYMENT_METHOD_CHOICES,
        'offering_list_active': True,
    }
    return render(request, 'finance/offering_list.html', context)


@login_required
def add_offering(request):
    """Add a new offering"""
    if request.method == 'POST':
        offering_type = request.POST.get('offering_type', 'SUNDAY')
        date = request.POST.get('date') or timezone.now().date()
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'CASH')
        donor_name = request.POST.get('donor_name')
        donor_phone = request.POST.get('donor_phone')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        member_id = request.POST.get('member')
        notes = request.POST.get('notes')
        
        member = None
        if member_id:
            member = get_object_or_404(Member, id=member_id)
        
        Offering.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            offering_type=offering_type,
            date=date,
            amount=amount,
            payment_method=payment_method,
            donor_name=donor_name if not is_anonymous else None,
            donor_phone=donor_phone if not is_anonymous else None,
            is_anonymous=is_anonymous,
            member=member,
            notes=notes
        )
        
        messages.success(request, 'Offering recorded successfully!')
        return redirect('offering_list')
    
    members = Member.objects.filter(active=True).order_by('name')
    context = {
        'members': members,
        'offering_types': Offering.OFFERING_TYPE_CHOICES,
        'payment_methods': Offering.PAYMENT_METHOD_CHOICES,
        'offering_list_active': True,
    }
    return render(request, 'finance/offering_form.html', context)


@login_required
def edit_offering(request, pk):
    """Edit an offering"""
    offering = get_object_or_404(Offering, pk=pk, user=request.user)
    
    if request.method == 'POST':
        offering.offering_type = request.POST.get('offering_type', offering.offering_type)
        offering.date = request.POST.get('date') or offering.date
        offering.amount = request.POST.get('amount', offering.amount)
        offering.payment_method = request.POST.get('payment_method', offering.payment_method)
        offering.is_anonymous = request.POST.get('is_anonymous') == 'on'
        offering.donor_name = request.POST.get('donor_name') if not offering.is_anonymous else None
        offering.donor_phone = request.POST.get('donor_phone') if not offering.is_anonymous else None
        offering.notes = request.POST.get('notes', offering.notes)
        offering.modified_by = request.user
        
        member_id = request.POST.get('member')
        if member_id:
            offering.member = get_object_or_404(Member, id=member_id)
        else:
            offering.member = None
        
        offering.save()
        messages.success(request, 'Offering updated successfully!')
        return redirect('offering_list')
    
    members = Member.objects.filter(active=True).order_by('name')
    context = {
        'offering': offering,
        'members': members,
        'offering_types': Offering.OFFERING_TYPE_CHOICES,
        'payment_methods': Offering.PAYMENT_METHOD_CHOICES,
        'offering_list_active': True,
    }
    return render(request, 'finance/offering_form.html', context)


@login_required
def delete_offering(request, pk):
    """Delete an offering (soft delete)"""
    offering = get_object_or_404(Offering, pk=pk, user=request.user)
    offering.soft_delete(request.user)
    messages.success(request, 'Offering deleted successfully!')
    return redirect('offering_list')


# ====== EMPLOYEE MANAGEMENT ======

@login_required
def employee_list(request):
    employees = Employee.objects.filter(user=request.user)
    
    status_filter = request.GET.get('status')
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    context = {
        'employees': employees,
        'finance_active': True,
    }
    return render(request, 'finance/employee_list.html', context)


@login_required
def add_employee(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        employee_id = request.POST.get('employee_id')
        position = request.POST.get('position')
        department = request.POST.get('department')
        base_salary = request.POST.get('base_salary')
        payment_type = request.POST.get('payment_type')
        bank_account = request.POST.get('bank_account')
        bank_name = request.POST.get('bank_name')
        tax_id = request.POST.get('tax_id')
        hire_date = request.POST.get('hire_date')

        Employee.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            name=name,
            employee_id=employee_id,
            position=position,
            department=department,
            base_salary=base_salary,
            payment_type=payment_type,
            bank_account=bank_account,
            bank_name=bank_name,
            tax_id=tax_id,
            hire_date=hire_date
        )

        messages.success(request, 'Employee added successfully!')
        return redirect('employee_list')

    return render(request, 'finance/employee_form.html', {
        'finance_active': True,
    })


@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk, user=request.user)

    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.employee_id = request.POST.get('employee_id')
        employee.position = request.POST.get('position')
        employee.department = request.POST.get('department')
        employee.base_salary = request.POST.get('base_salary')
        employee.payment_type = request.POST.get('payment_type')
        employee.bank_account = request.POST.get('bank_account')
        employee.bank_name = request.POST.get('bank_name')
        employee.tax_id = request.POST.get('tax_id')
        employee.hire_date = request.POST.get('hire_date')
        employee.status = request.POST.get('status')
        employee.modified_by = request.user
        employee.save()

        messages.success(request, 'Employee updated successfully!')
        return redirect('employee_list')

    context = {
        'employee': employee,
        'finance_active': True,
    }
    return render(request, 'finance/employee_form.html', context)


@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk, user=request.user)
    employee.soft_delete(request.user)
    messages.success(request, 'Employee deleted successfully!')
    return redirect('employee_list')


# ====== PAYROLL MANAGEMENT ======

@login_required
def payroll_list(request):
    payrolls = Payroll.objects.filter(user=request.user).select_related('employee').order_by('-created_at')

    status_filter = request.GET.get('status')
    month_filter = request.GET.get('month')

    if status_filter:
        payrolls = payrolls.filter(status=status_filter)

    if month_filter:
        payrolls = payrolls.filter(pay_period_end__month=month_filter)

    # Calculate statistics (before pagination)
    pending_count = payrolls.filter(status='PENDING').count()
    pending_verification_count = payrolls.filter(status='PENDING_VERIFICATION').count()
    verified_count = payrolls.filter(status='VERIFIED').count()
    processed_count = payrolls.filter(status='PROCESSED').count()
    paid_count = payrolls.filter(status='PAID').count()
    total_net_salary = sum(payroll.net_salary for payroll in payrolls)

    # Handle exports (before pagination)
    export_format = request.GET.get('export')
    if export_format == 'csv':
        from .exports import export_payroll_to_csv
        return export_payroll_to_csv(payrolls)
    elif export_format == 'pdf':
        from .exports import export_payroll_to_pdf
        return export_payroll_to_pdf(payrolls, {
            'total_net_salary': total_net_salary,
            'filters': {
                'status': status_filter,
                'month': month_filter
            }
        })

    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(payrolls, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'payrolls': page_obj,
        'pending_count': pending_count,
        'pending_verification_count': pending_verification_count,
        'verified_count': verified_count,
        'processed_count': processed_count,
        'paid_count': paid_count,
        'total_net_salary': total_net_salary,
        'finance_active': True,
    }
    return render(request, 'finance/payroll_list.html', context)


@login_required
def generate_payroll(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        pay_period_start = request.POST.get('pay_period_start')
        pay_period_end = request.POST.get('pay_period_end')
        payment_method = request.POST.get('payment_method', 'CASH')

        employee = get_object_or_404(Employee, pk=employee_id, user=request.user)

        # Check if payroll already exists for this period
        existing = Payroll.objects.filter(
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end
        ).first()

        if existing:
            messages.error(request, 'Payroll already exists for this period!')
            return redirect('generate_payroll')

        # Calculate payroll - no tax deduction for church employees
        basic_salary = employee.base_salary
        gross_salary = basic_salary
        other_deductions = 0
        net_salary = gross_salary - other_deductions

        payroll = Payroll.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            basic_salary=basic_salary,
            gross_salary=gross_salary,
            other_deductions=other_deductions,
            net_salary=net_salary,
            payment_method=payment_method,
            status='PENDING'
        )

        messages.success(request, f'Payroll generated for {employee.name}!')
        return redirect('payroll_list')

    employees = Employee.objects.filter(user=request.user, status='ACTIVE')
    return render(request, 'finance/payroll_form.html', {
        'employees': employees,
        'finance_active': True,
    })


@login_required
def process_payroll(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk, user=request.user)

    if payroll.status == 'VERIFIED':
        payroll.status = 'PROCESSED'
        payroll.payment_date = timezone.now().date()
        payroll.save()

        # Create a transaction record
        category, created = Category.objects.get_or_create(
            user=request.user,
            name='Salary Payment',
            defaults={'type': 'SALARY'}
        )

        Transaction.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            category=category,
            amount=payroll.net_salary,
            description=f'Salary payment to {payroll.employee.name}',
            date=timezone.now().date(),
            type='Expense',
            status='COMPLETED',
            reference_number=f'PAY-{payroll.id}'
        )

        messages.success(request, 'Payroll processed successfully!')
    else:
        messages.error(request, 'Payroll must be verified before processing!')

    return redirect('payroll_list')


@login_required
def submit_payroll_for_verification(request, pk):
    """Allow accounts to submit payroll for verification by priest/chairperson"""
    payroll = get_object_or_404(Payroll, pk=pk, user=request.user)

    if payroll.status == 'PENDING':
        payroll.status = 'PENDING_VERIFICATION'
        payroll.submitted_for_verification = True
        payroll.submitted_for_verification_at = timezone.now()
        payroll.submitted_by = request.user
        payroll.save()

        messages.success(request, f'Payroll for {payroll.employee.name} submitted for verification successfully!')
    else:
        messages.error(request, 'Only pending payrolls can be submitted for verification!')

    return redirect('payroll_list')


@login_required
def verify_payroll(request, pk):
    """Allow priest or chairperson to verify payroll"""
    payroll = get_object_or_404(Payroll, pk=pk)

    # Check if user is priest or chairperson
    user_role = getattr(request.user, 'roles', None)
    if user_role not in ['priest', 'chairperson', 'admin'] and not request.user.is_superuser:
        messages.error(request, 'Only Priest, Chairperson, or Admin can verify payrolls!')
        return redirect('payroll_list')

    if payroll.status == 'PENDING_VERIFICATION':
        payroll.status = 'VERIFIED'
        payroll.verified_by = request.user
        payroll.verified_at = timezone.now()
        payroll.save()

        messages.success(request, f'Payroll for {payroll.employee.name} verified successfully!')
    else:
        messages.error(request, 'Only payrolls pending verification can be verified!')

    return redirect('payroll_list')


@login_required
def reject_payroll(request, pk):
    """Allow priest or chairperson to reject payroll"""
    payroll = get_object_or_404(Payroll, pk=pk)

    # Check if user is priest or chairperson
    user_role = getattr(request.user, 'roles', None)
    if user_role not in ['priest', 'chairperson', 'admin'] and not request.user.is_superuser:
        messages.error(request, 'Only Priest, Chairperson, or Admin can reject payrolls!')
        return redirect('payroll_list')

    if payroll.status in ['PENDING_VERIFICATION', 'PENDING']:
        payroll.status = 'CANCELLED'
        payroll.save()

        messages.warning(request, f'Payroll for {payroll.employee.name} has been rejected.')
    else:
        messages.error(request, 'This payroll cannot be rejected!')

    return redirect('payroll_list')


# ====== BUDGET MANAGEMENT ======

@login_required
def budget_list(request):
    budgets = Budget.objects.filter(user=request.user).prefetch_related('allocations__category')
    
    status_filter = request.GET.get('status')
    budget_type_filter = request.GET.get('budget_type')
    department_filter = request.GET.get('department')
    fiscal_year_filter = request.GET.get('fiscal_year')
    
    if status_filter:
        budgets = budgets.filter(status=status_filter)
    if budget_type_filter:
        budgets = budgets.filter(budget_type=budget_type_filter)
    if department_filter:
        budgets = budgets.filter(department=department_filter)
    if fiscal_year_filter:
        budgets = budgets.filter(fiscal_year=fiscal_year_filter)
    
    # Calculate totals and add usage percentages to budgets
    total_budget_amount = sum(budget.total_amount for budget in budgets)
    total_spent_amount = sum(budget.spent_amount for budget in budgets)
    total_remaining_amount = sum(budget.remaining_amount for budget in budgets)
    total_approved_amount = sum(budget.approved_amount or 0 for budget in budgets)
    
    # Calculate utilization percentage
    utilization_percentage = 0
    if total_budget_amount > 0:
        utilization_percentage = (total_spent_amount / total_budget_amount) * 100
    
    # Note: Budget usage percentage is a calculated property in the model
    # It will be available as budget.usage_percentage in templates
    
    # Get filter options
    budget_types = Budget.TYPE_CHOICES
    departments = Budget.objects.filter(user=request.user).values_list('department', flat=True).distinct()
    departments = [dept for dept in departments if dept]  # Remove None/blank
    fiscal_years = Budget.objects.filter(user=request.user).values_list('fiscal_year', flat=True).distinct()
    fiscal_years = [year for year in fiscal_years if year]  # Remove None/blank
    
    context = {
        'budgets': budgets,
        'total_budget_amount': total_budget_amount,
        'total_spent_amount': total_spent_amount,
        'total_remaining_amount': total_remaining_amount,
        'total_approved_amount': total_approved_amount,
        'utilization_percentage': utilization_percentage,
        'budget_types': budget_types,
        'departments': departments,
        'fiscal_years': fiscal_years,
        'finance_active': True,
    }
    return render(request, 'finance/enhanced_budget_list.html', context)


@login_required
def create_budget(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        budget_type = request.POST.get('budget_type')
        total_amount = request.POST.get('total_amount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        fiscal_year = request.POST.get('fiscal_year')
        fiscal_period = request.POST.get('fiscal_period')
        department = request.POST.get('department')
        variance_threshold = request.POST.get('variance_threshold', 10.0)
        requires_monthly_review = request.POST.get('requires_monthly_review') == 'on'
        auto_carry_forward = request.POST.get('auto_carry_forward') == 'on'
        
        budget = Budget.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            name=name,
            description=description,
            budget_type=budget_type,
            total_amount=total_amount,
            start_date=start_date,
            end_date=end_date,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            department=department,
            variance_threshold=variance_threshold,
            requires_monthly_review=requires_monthly_review,
            auto_carry_forward=auto_carry_forward
        )
        
        messages.success(request, 'Budget created successfully! You can now add allocations.')
        return redirect('budget_detail', pk=budget.pk)
    
    context = {
        'budget_types': Budget.TYPE_CHOICES,
        'fiscal_periods': Budget.FISCAL_YEAR_CHOICES,
        'finance_active': True,
    }
    return render(request, 'finance/enhanced_budget_form.html', context)


@login_required
def edit_budget(request, pk):
    """Edit a budget - only allowed if not approved"""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    # Prevent editing if budget is approved or beyond
    if budget.status in ['ACTIVE', 'COMPLETED']:
        messages.error(request, 'Budget cannot be edited once it has been approved.')
        return redirect('budget_detail', pk=pk)
    
    if request.method == 'POST':
        budget.name = request.POST.get('name', budget.name)
        budget.description = request.POST.get('description', budget.description)
        budget.budget_type = request.POST.get('budget_type', budget.budget_type)
        budget.total_amount = request.POST.get('total_amount', budget.total_amount)
        budget.start_date = request.POST.get('start_date', budget.start_date)
        budget.end_date = request.POST.get('end_date', budget.end_date)
        budget.fiscal_year = request.POST.get('fiscal_year', budget.fiscal_year)
        budget.fiscal_period = request.POST.get('fiscal_period', budget.fiscal_period)
        budget.department = request.POST.get('department', budget.department)
        budget.variance_threshold = request.POST.get('variance_threshold', budget.variance_threshold)
        budget.requires_monthly_review = request.POST.get('requires_monthly_review') == 'on'
        budget.auto_carry_forward = request.POST.get('auto_carry_forward') == 'on'
        budget.modified_by = request.user
        
        budget.save()
        messages.success(request, 'Budget updated successfully!')
        return redirect('budget_detail', pk=pk)
    
    context = {
        'budget': budget,
        'budget_types': Budget.TYPE_CHOICES,
        'fiscal_periods': Budget.FISCAL_YEAR_CHOICES,
        'finance_active': True,
    }
    return render(request, 'finance/enhanced_budget_form.html', context)


@login_required
def budget_detail(request, pk):
    try:
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        allocations = budget.allocations.all().select_related('category')
        
        # Calculate totals safely
        total_allocated = 0
        total_spent = 0
        total_committed = 0
        total_remaining = 0
        
        for allocation in allocations:
            try:
                total_allocated += float(allocation.allocated_amount or 0)
                total_spent += float(allocation.spent_amount or 0)
                total_committed += float(allocation.committed_amount or 0)
                total_remaining += float(allocation.remaining_amount or 0)
            except (AttributeError, TypeError):
                # Skip if fields don't exist or have wrong types
                continue
        
    except Exception as e:
        # Handle any database schema issues gracefully
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        allocations = []
        total_allocated = 0
        total_spent = 0
        total_committed = 0
        total_remaining = 0

    # Note: Budget and Allocation usage percentages are calculated properties in the model
    # They will be available as budget.usage_percentage, allocation.usage_percentage, etc. in templates

    # Get related data
    variances = budget.variances.all().order_by('-detected_date')[:5]
    alerts = budget.alerts.filter(is_active=True).order_by('-created_at')[:5]
    transfers_out = budget.transfer_outs.filter(status='PENDING').order_by('-created_at')[:3]
    transfers_in = budget.transfer_ins.filter(status='PENDING').order_by('-created_at')[:3]
    periods = budget.periods.all().order_by('-start_date')[:4]

    # Get available categories for allocation
    allocated_category_ids = [alloc.category_id for alloc in allocations]
    available_categories = Category.objects.filter(
        user=request.user,
        is_active=True
    ).exclude(id__in=allocated_category_ids)

    context = {
        'budget': budget,
        'allocations': allocations,
        'total_allocated': total_allocated,
        'total_spent': total_spent,
        'total_committed': total_committed,
        'total_remaining': total_remaining,
        'variances': variances,
        'alerts': alerts,
        'transfers_out': transfers_out,
        'transfers_in': transfers_in,
        'periods': periods,
        'available_categories': available_categories,
        'finance_active': True,
    }
    return render(request, 'finance/budget_detail.html', context)


@login_required
def submit_budget_for_approval(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if budget.status == 'DRAFT':
        success = budget.submit_for_approval(request.user)
        if success:
            messages.success(request, f'Budget "{budget.name}" submitted for approval!')
            
            # Create alert for approval needed
            BudgetAlert.objects.create(
                budget=budget,
                alert_type='APPROVAL_NEEDED',
                priority='HIGH',
                title=f'Budget Approval Required: {budget.name}',
                message=f'Budget "{budget.name}" of ${budget.total_amount} is pending approval.',
                current_value=budget.total_amount
            )
        else:
            messages.error(request, 'Budget cannot be submitted for approval in current status.')
    else:
        messages.error(request, 'Only draft budgets can be submitted for approval.')
    
    return redirect('budget_detail', pk=pk)


@login_required
def approve_budget(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if budget.status == 'PENDING_APPROVAL':
        if request.method == 'POST':
            approved_amount = request.POST.get('approved_amount')
            if approved_amount:
                approved_amount = Decimal(approved_amount)
            else:
                approved_amount = budget.total_amount
            
            success = budget.approve(request.user, approved_amount)
            if success:
                messages.success(request, f'Budget "{budget.name}" approved successfully!')
                
                # Create approval alert
                BudgetAlert.objects.create(
                    budget=budget,
                    alert_type='APPROVAL_NEEDED',
                    priority='LOW',
                    title=f'Budget Approved: {budget.name}',
                    message=f'Budget "{budget.name}" has been approved for ${approved_amount}.',
                    current_value=approved_amount,
                    is_acknowledged=True,
                    acknowledged_by=request.user,
                    acknowledged_at=timezone.now()
                )
            else:
                messages.error(request, 'Budget cannot be approved in current status.')
            
            return redirect('budget_detail', pk=pk)
        else:
            context = {
                'budget': budget,
                'finance_active': True,
            }
            return render(request, 'finance/approve_budget.html', context)
    else:
        messages.error(request, 'Only budgets pending approval can be approved.')
        return redirect('budget_detail', pk=pk)


@login_required
def reject_budget(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if budget.status == 'PENDING_APPROVAL':
        if request.method == 'POST':
            rejection_reason = request.POST.get('rejection_reason')
            if not rejection_reason:
                messages.error(request, 'Please provide a reason for rejection.')
                return redirect('budget_detail', pk=pk)
            
            success = budget.reject(request.user, rejection_reason)
            if success:
                messages.success(request, f'Budget "{budget.name}" has been rejected.')
                
                # Create rejection alert
                BudgetAlert.objects.create(
                    budget=budget,
                    alert_type='APPROVAL_NEEDED',
                    priority='MEDIUM',
                    title=f'Budget Rejected: {budget.name}',
                    message=f'Budget "{budget.name}" has been rejected. Reason: {rejection_reason}',
                    is_acknowledged=True,
                    acknowledged_by=request.user,
                    acknowledged_at=timezone.now()
                )
            else:
                messages.error(request, 'Budget cannot be rejected in current status.')
        else:
            context = {
                'budget': budget,
                'finance_active': True,
            }
            return render(request, 'finance/reject_budget.html', context)
    else:
        messages.error(request, 'Only budgets pending approval can be rejected.')
    
    return redirect('budget_detail', pk=pk)


@login_required
def add_budget_allocation(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    
    if budget.status not in ['DRAFT', 'ACTIVE']:
        error_msg = 'Allocations can only be added to draft or active budgets.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('budget_detail', pk=pk)
    
    if request.method == 'POST':
        import json
        allocations_data = request.POST.get('allocations')
        
        if not allocations_data:
            error_msg = 'No allocations provided.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('budget_detail', pk=pk)
        
        try:
            allocations = json.loads(allocations_data)
            created_count = 0
            skipped_count = 0
            errors = []
            
            for alloc_data in allocations:
                category_name = alloc_data.get('category_name')
                allocated_amount = alloc_data.get('allocated_amount')
                category_type = alloc_data.get('category_type')
                
                if not category_name or not allocated_amount or not category_type:
                    errors.append(f'Invalid data for allocation: {category_name}')
                    continue
                
                try:
                    allocated_amount = Decimal(allocated_amount)
                    if allocated_amount <= 0:
                        errors.append(f'Invalid amount for {category_name}')
                        continue
                except:
                    errors.append(f'Invalid amount format for {category_name}')
                    continue
                
                # Get or create category
                category, created = Category.objects.get_or_create(
                    user=request.user,
                    name=category_name,
                    type=category_type,
                    defaults={
                        'created_by': request.user,
                        'modified_by': request.user,
                        'is_active': True
                    }
                )
                
                # Check if allocation already exists
                existing_allocation = BudgetAllocation.objects.filter(budget=budget, category=category).first()
                if existing_allocation:
                    skipped_count += 1
                    errors.append(f'Allocation for {category.name} already exists (skipped)')
                    continue
                
                # Create allocation
                BudgetAllocation.objects.create(
                    budget=budget,
                    category=category,
                    allocated_amount=allocated_amount,
                    original_allocation=allocated_amount,
                    period_start=budget.start_date,
                    period_end=budget.end_date,
                    created_by=request.user,
                    modified_by=request.user
                )
                created_count += 1
            
            # Prepare response message
            if created_count > 0:
                success_msg = f'Successfully added {created_count} allocation(s).'
                if skipped_count > 0:
                    success_msg += f' Skipped {skipped_count} duplicate(s).'
                if errors:
                    success_msg += f' Some errors occurred: {"; ".join(errors[:3])}'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': success_msg})
                messages.success(request, success_msg)
            else:
                error_msg = f'No allocations created. {"; ".join(errors)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                
        except json.JSONDecodeError:
            error_msg = 'Invalid data format.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f'Error adding allocation: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    return redirect('budget_detail', pk=pk)


@login_required
def edit_budget_allocation(request, pk, allocation_id):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    allocation = get_object_or_404(BudgetAllocation, id=allocation_id, budget=budget)
    
    if budget.status not in ['DRAFT', 'ACTIVE']:
        error_msg = 'Allocations can only be edited in draft or active budgets.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('budget_detail', pk=pk)
    
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        allocated_amount = request.POST.get('allocated_amount')
        category_type = request.POST.get('category_type')
        variance_reason = request.POST.get('variance_reason', '')
        
        try:
            allocated_amount = Decimal(allocated_amount)
            if allocated_amount <= 0:
                error_msg = 'Allocated amount must be greater than 0.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('budget_detail', pk=pk)
            
            old_amount = allocation.allocated_amount
            
            # Get or create category if name changed
            if category_name and category_name != allocation.category.name:
                category, created = Category.objects.get_or_create(
                    user=request.user,
                    name=category_name,
                    type=category_type,
                    defaults={
                        'created_by': request.user,
                        'modified_by': request.user,
                        'is_active': True
                    }
                )
                
                # Check if new category already has an allocation
                existing_allocation = BudgetAllocation.objects.filter(budget=budget, category=category).first()
                if existing_allocation and existing_allocation.id != allocation.id:
                    error_msg = f'Allocation for {category.name} already exists.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_msg})
                    messages.error(request, error_msg)
                    return redirect('budget_detail', pk=pk)
                
                allocation.category = category
            
            # Update allocation amount
            allocation.allocated_amount = allocated_amount
            allocation.variance_reason = variance_reason
            allocation.modified_by = request.user
            allocation.save()
            
            # Create variance record if significant change
            if abs(allocated_amount - old_amount) > (old_amount * Decimal('0.1')):  # 10% threshold
                BudgetVariance.objects.create(
                    budget=budget,
                    allocation=allocation,
                    variance_type='ALLOCATION_VARIANCE',
                    severity='MEDIUM' if abs(allocated_amount - old_amount) / old_amount < 0.2 else 'HIGH',
                    budget_amount=old_amount,
                    actual_amount=allocated_amount,
                    variance_amount=allocated_amount - old_amount,
                    variance_percentage=abs((allocated_amount - old_amount) / old_amount) * 100,
                    description=f'Allocation changed from {old_amount} to {allocated_amount}',
                    causes=variance_reason,
                    period_start=budget.start_date,
                    period_end=budget.end_date,
                    reported_by=request.user
                )
            
            success_msg = f'Allocation for {allocation.category.name} updated successfully!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': success_msg})
            messages.success(request, success_msg)

        except Exception as e:
            error_msg = f'Error updating allocation: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
    
    return redirect('budget_detail', pk=pk)


@login_required
def delete_budget_allocation(request, pk, allocation_id):
    """Delete a budget allocation"""
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    allocation = get_object_or_404(BudgetAllocation, pk=allocation_id, budget=budget)

    # Only allow deletion in DRAFT or ACTIVE budgets
    if budget.status not in ['DRAFT', 'ACTIVE']:
        error_msg = 'Allocations can only be deleted in draft or active budgets.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('budget_detail', pk=pk)

    # Check if allocation has spending
    if allocation.spent_amount > 0:
        error_msg = f'Cannot delete allocation for {allocation.category.name} - it has recorded spending.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('budget_detail', pk=pk)

    category_name = allocation.category.name
    allocation.delete()

    success_msg = f'Allocation for {category_name} deleted successfully!'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': success_msg})
    messages.success(request, success_msg)
    return redirect('budget_detail', pk=pk)


@login_required
def budget_reports(request):
    """Comprehensive budget reporting and analytics"""
    budgets = Budget.objects.filter(user=request.user).prefetch_related('allocations__category', 'variances', 'periods')
    
    # Budget summary by type
    budget_summary = {}
    for budget_type, _ in Budget.TYPE_CHOICES:
        type_budgets = budgets.filter(budget_type=budget_type)
        budget_summary[budget_type] = {
            'count': type_budgets.count(),
            'total_budgeted': sum(b.total_amount for b in type_budgets),
            'total_spent': sum(b.spent_amount for b in type_budgets),
            'total_remaining': sum(b.remaining_amount for b in type_budgets),
        }
    
    # Monthly trend data
    current_year = timezone.now().year
    monthly_data = []
    for month in range(1, 13):
        month_start = date(current_year, month, 1)
        if month == 12:
            month_end = date(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(current_year, month + 1, 1) - timedelta(days=1)
        
        month_budgets = budgets.filter(
            start_date__lte=month_end,
            end_date__gte=month_start
        )
        
        monthly_data.append({
            'month': month_start.strftime('%B'),
            'budgeted': sum(b.total_amount for b in month_budgets),
            'spent': sum(b.spent_amount for b in month_budgets),
        })
    
    # Top variances
    top_variances = BudgetVariance.objects.filter(
        budget__user=request.user,
        is_resolved=False
    ).order_by('-variance_percentage')[:10]
    
    # Active alerts
    active_alerts = BudgetAlert.objects.filter(
        budget__user=request.user,
        is_active=True,
        is_acknowledged=False
    ).order_by('-priority', '-created_at')
    
    context = {
        'budget_summary': budget_summary,
        'monthly_data': monthly_data,
        'top_variances': top_variances,
        'active_alerts': active_alerts,
        'finance_active': True,
    }
    return render(request, 'finance/budget_reports.html', context)


@login_required
def budget_transfer_request(request):
    """Create a budget transfer request"""
    if request.method == 'POST':
        source_budget_id = request.POST.get('source_budget')
        target_budget_id = request.POST.get('target_budget')
        transfer_type = request.POST.get('transfer_type')
        amount = request.POST.get('amount')
        reason = request.POST.get('reason')
        source_allocation_id = request.POST.get('source_allocation')
        target_allocation_id = request.POST.get('target_allocation')
        
        try:
            source_budget = Budget.objects.get(id=source_budget_id, user=request.user)
            target_budget = Budget.objects.get(id=target_budget_id, user=request.user)
            amount = Decimal(amount)
            
            # Validate transfer
            if source_budget == target_budget:
                messages.error(request, 'Source and target budgets cannot be the same.')
            elif amount <= 0:
                messages.error(request, 'Transfer amount must be greater than 0.')
            elif source_budget.remaining_amount < amount:
                messages.error(request, 'Insufficient funds in source budget.')
            else:
                transfer = BudgetTransfer.objects.create(
                    source_budget=source_budget,
                    target_budget=target_budget,
                    transfer_type=transfer_type,
                    amount=amount,
                    reason=reason,
                    requested_by=request.user
                )
                
                # Add allocation details if provided
                if source_allocation_id:
                    transfer.source_allocation = BudgetAllocation.objects.get(id=source_allocation_id)
                if target_allocation_id:
                    transfer.target_allocation = BudgetAllocation.objects.get(id=target_allocation_id)
                transfer.save()
                
                # Create alert
                BudgetAlert.objects.create(
                    budget=source_budget,
                    alert_type='OVER_BUDGET',
                    priority='MEDIUM',
                    title=f'Budget Transfer Request: {amount}',
                    message=f'Transfer request of TSH {amount} from {source_budget.name} to {target_budget.name}',
                    current_value=amount
                )
                
                messages.success(request, f'Budget transfer request of TSH {amount} submitted successfully!')
                return redirect('budget_detail', pk=source_budget.pk)
                
        except Budget.DoesNotExist:
            messages.error(request, 'Invalid budget selected.')
        except Exception as e:
            messages.error(request, f'Error creating transfer request: {str(e)}')
    
    # Get user's budgets for dropdown
    budgets = Budget.objects.filter(user=request.user, status='ACTIVE')
    context = {
        'budgets': budgets,
        'transfer_types': BudgetTransfer.TRANSFER_TYPES,
        'finance_active': True,
    }
    return render(request, 'finance/budget_transfer_form.html', context)


@login_required
def approve_budget_transfer(request, pk):
    """Approve a budget transfer request"""
    transfer = get_object_or_404(BudgetTransfer, pk=pk, source_budget__user=request.user)
    
    if transfer.status != 'PENDING':
        messages.error(request, 'This transfer has already been processed.')
        return redirect('budget_detail', pk=transfer.source_budget.pk)
    
    if request.method == 'POST':
        # Execute the transfer
        if transfer.source_budget.remaining_amount >= transfer.amount:
            # Update source budget
            transfer.source_budget.total_amount -= transfer.amount
            transfer.source_budget.save()
            
            # Update target budget
            transfer.target_budget.total_amount += transfer.amount
            transfer.target_budget.save()
            
            # Update allocations if specified
            if transfer.source_allocation:
                transfer.source_allocation.allocated_amount -= transfer.amount
                transfer.source_allocation.save()
            
            if transfer.target_allocation:
                transfer.target_allocation.allocated_amount += transfer.amount
                transfer.target_allocation.save()
            
            # Update transfer status
            transfer.status = 'COMPLETED'
            transfer.approved_by = request.user
            transfer.approved_at = timezone.now()
            transfer.executed_by = request.user
            transfer.executed_at = timezone.now()
            transfer.save()
            
            # Create variance records
            BudgetVariance.objects.create(
                budget=transfer.source_budget,
                variance_type='ALLOCATION_VARIANCE',
                severity='MEDIUM',
                budget_amount=transfer.source_budget.total_amount + transfer.amount,
                actual_amount=transfer.source_budget.total_amount,
                variance_amount=-transfer.amount,
                variance_percentage=(transfer.amount / (transfer.source_budget.total_amount + transfer.amount)) * 100,
                description=f'Budget transfer out: {transfer.amount}',
                causes=transfer.reason,
                period_start=transfer.source_budget.start_date,
                period_end=transfer.source_budget.end_date,
                reported_by=request.user
            )
            
            BudgetVariance.objects.create(
                budget=transfer.target_budget,
                variance_type='ALLOCATION_VARIANCE',
                severity='LOW',
                budget_amount=transfer.target_budget.total_amount - transfer.amount,
                actual_amount=transfer.target_budget.total_amount,
                variance_amount=transfer.amount,
                variance_percentage=(transfer.amount / (transfer.target_budget.total_amount - transfer.amount)) * 100,
                description=f'Budget transfer in: {transfer.amount}',
                causes=transfer.reason,
                period_start=transfer.target_budget.start_date,
                period_end=transfer.target_budget.end_date,
                reported_by=request.user
            )
            
            messages.success(request, f'Budget transfer of TSH {transfer.amount} completed successfully!')
        else:
            messages.error(request, 'Insufficient funds in source budget.')
    
    context = {
        'transfer': transfer,
        'finance_active': True,
    }
    return render(request, 'finance/approve_transfer.html', context)


@login_required
def reject_budget_transfer(request, pk):
    """Reject a budget transfer request"""
    transfer = get_object_or_404(BudgetTransfer, pk=pk, source_budget__user=request.user)
    
    if transfer.status != 'PENDING':
        messages.error(request, 'This transfer has already been processed.')
        return redirect('budget_detail', pk=transfer.source_budget.pk)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason')
        if not rejection_reason:
            messages.error(request, 'Please provide a reason for rejection.')
        else:
            transfer.status = 'REJECTED'
            transfer.approved_by = request.user
            transfer.approved_at = timezone.now()
            transfer.rejection_reason = rejection_reason
            transfer.save()
            
            messages.success(request, 'Budget transfer request rejected.')
    
    context = {
        'transfer': transfer,
        'finance_active': True,
    }
    return render(request, 'finance/reject_transfer.html', context)


@login_required
def budget_variances(request):
    """View and manage budget variances"""
    try:
        # Use only() to select only the fields we know exist in the database
        variances = BudgetVariance.objects.filter(
            budget__user=request.user
        ).only(
            'id', 'budget', 'allocation', 'variance_type', 'severity',
            'budget_amount', 'actual_amount', 'variance_amount', 'variance_percentage',
            'description', 'period_start', 'period_end', 'detected_date', 
            'resolved_date', 'is_resolved'
        ).select_related('budget', 'allocation__category').order_by('-detected_date')
        
        # Filter options
        variance_type_filter = request.GET.get('variance_type')
        severity_filter = request.GET.get('severity')
        resolved_filter = request.GET.get('resolved')
        
        if variance_type_filter:
            variances = variances.filter(variance_type=variance_type_filter)
        if severity_filter:
            variances = variances.filter(severity=severity_filter)
        if resolved_filter == 'resolved':
            variances = variances.filter(is_resolved=True)
        elif resolved_filter == 'unresolved':
            variances = variances.filter(is_resolved=False)
        
        context = {
            'variances': variances,
            'variance_types': BudgetVariance.VARIANCE_TYPES,
            'severity_levels': BudgetVariance.SEVERITY_LEVELS,
            'finance_active': True,
        }
        return render(request, 'finance/budget_variances_list.html', context)
    except Exception as e:
        # If there's a database schema issue, return empty queryset
        context = {
            'variances': BudgetVariance.objects.none(),
            'variance_types': BudgetVariance.VARIANCE_TYPES,
            'severity_levels': BudgetVariance.SEVERITY_LEVELS,
            'finance_active': True,
            'error': f"Database schema issue: {str(e)}"
        }
        return render(request, 'finance/budget_variances_list.html', context)


@login_required
def acknowledge_budget_alert(request, pk):
    """Acknowledge a budget alert"""
    alert = get_object_or_404(BudgetAlert, pk=pk, budget__user=request.user)
    
    if not alert.is_acknowledged:
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        messages.success(request, f'Alert "{alert.title}" acknowledged.')
    
    return redirect('budget_detail', pk=alert.budget.pk)


@login_required
def export_budgets(request):
    """Export budgets to CSV"""
    from .exports import export_budgets_to_csv
    from .models import Budget
    
    # Get filtered queryset
    budgets = Budget.objects.all()
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        budgets = budgets.filter(status=status_filter)
    
    year_filter = request.GET.get('year')
    if year_filter:
        budgets = budgets.filter(start_date__year=year_filter)
    
    return export_budgets_to_csv(budgets)


@login_required
def export_budget_allocations(request, pk):
    """Export budget allocations to CSV"""
    from .exports import export_budget_allocations_to_csv
    from .models import Budget, BudgetAllocation
    
    budget = get_object_or_404(Budget, pk=pk)
    allocations = BudgetAllocation.objects.filter(budget=budget)
    
    return export_budget_allocations_to_csv(allocations)


@login_required
def export_budget_reports(request):
    """Export budget reports to CSV"""
    from .exports import export_budget_reports_to_csv
    from .models import Budget
    
    budgets = Budget.objects.filter(user=request.user).prefetch_related('allocations__category', 'variances', 'periods')
    
    # Budget summary by type
    budget_summary = {}
    for budget_type, _ in Budget.TYPE_CHOICES:
        type_budgets = budgets.filter(budget_type=budget_type)
        budget_summary[budget_type] = {
            'count': type_budgets.count(),
            'total_budgeted': sum(b.total_amount for b in type_budgets),
            'total_spent': sum(b.spent_amount for b in type_budgets),
            'total_remaining': sum(b.remaining_amount for b in type_budgets),
        }
    
    # Monthly trend data
    current_year = timezone.now().year
    monthly_data = []
    for month in range(1, 13):
        month_start = date(current_year, month, 1)
        if month == 12:
            month_end = date(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(current_year, month + 1, 1) - timedelta(days=1)
        
        month_budgets = budgets.filter(
            start_date__lte=month_end,
            end_date__gte=month_start
        )
        
        monthly_data.append({
            'month': month_start.strftime('%B'),
            'budgeted': sum(b.total_amount for b in month_budgets),
            'spent': sum(b.spent_amount for b in month_budgets),
        })
    
    report_data = {
        'budget_summary': budget_summary,
        'monthly_data': monthly_data,
    }
    
    return export_budget_reports_to_csv(report_data)


@login_required
def print_budget(request, pk):
    """Print budget details"""
    from .models import Budget
    
    budget = get_object_or_404(Budget, pk=pk)
    
    context = {
        'budget': budget,
        'generated_at': timezone.now(),
        'generated_by': request.user,
    }
    
    return render(request, 'finance/print/budget.html', context)


@login_required
def print_budget_allocations(request, pk):
    """Print budget allocations"""
    from .models import Budget, BudgetAllocation
    
    budget = get_object_or_404(Budget, pk=pk)
    allocations = BudgetAllocation.objects.filter(budget=budget).select_related('category')
    
    context = {
        'budget': budget,
        'allocations': allocations,
        'generated_at': timezone.now(),
        'generated_by': request.user,
    }
    
    return render(request, 'finance/print/budget_allocations.html', context)


# ====== EXPENSE REPORTS ======

@login_required
def expense_report_list(request):
    expense_reports = ExpenseReport.objects.filter(user=request.user).select_related('employee')

    status_filter = request.GET.get('status')
    if status_filter:
        expense_reports = expense_reports.filter(status=status_filter)

    # Calculate total amount
    total_expense_amount = sum(report.total_amount for report in expense_reports)

    # Handle exports
    export_format = request.GET.get('export')
    if export_format == 'csv':
        from .exports import export_expense_reports_to_csv
        return export_expense_reports_to_csv(expense_reports)
    elif export_format == 'pdf':
        from .exports import export_expense_reports_to_pdf
        return export_expense_reports_to_pdf(expense_reports, {
            'total_amount': total_expense_amount,
            'filters': {'status': status_filter}
        })

    context = {
        'expense_reports': expense_reports,
        'total_expense_amount': total_expense_amount,
        'finance_active': True,
    }
    return render(request, 'finance/expense_report_list.html', context)


@login_required
def create_expense_report(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        employee_id = request.POST.get('employee')

        employee = None
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id, user=request.user)

        # Create expense report
        expense_report = ExpenseReport.objects.create(
            user=request.user,
            created_by=request.user,
            modified_by=request.user,
            employee=employee,
            title=title,
            description=description,
            total_amount=0  # Will be calculated from items
        )

        # Process expense items
        item_dates = request.POST.getlist('item_date[]')
        item_categories = request.POST.getlist('item_category[]')
        item_descriptions = request.POST.getlist('item_description[]')
        item_amounts = request.POST.getlist('item_amount[]')
        item_receipts = request.POST.getlist('item_receipt[]')

        total_amount = 0
        for i in range(len(item_descriptions)):
            if item_descriptions[i].strip():  # Only create if description is provided
                amount = Decimal(item_amounts[i]) if item_amounts[i] else Decimal('0')
                category = get_object_or_404(Category, pk=item_categories[i], user=request.user)

                ExpenseItem.objects.create(
                    user=request.user,
                    created_by=request.user,
                    modified_by=request.user,
                    expense_report=expense_report,
                    category=category,
                    description=item_descriptions[i].strip(),
                    amount=amount,
                    date_incurred=item_dates[i] or timezone.now().date(),
                    receipt_number=item_receipts[i].strip() if item_receipts[i] else None
                )
                total_amount += amount

        # Update total amount
        expense_report.total_amount = total_amount
        expense_report.save()

        messages.success(request, f'Expense report created with {len(item_descriptions)} items totaling TSH {total_amount:,.2f}!')
        return redirect('expense_report_detail', pk=expense_report.pk)

    employees = Employee.objects.filter(user=request.user, status='ACTIVE')
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/expense_report_form.html', {
        'employees': employees,
        'categories': categories,
        'finance_active': True,
    })


# ====== RECEIPT MANAGEMENT ======

@login_required
def receipt_list(request):
    receipts = TitheReceipt.objects.filter(user=request.user).select_related('member')
    
    # Filter options
    member_filter = request.GET.get('member')
    payment_method = request.GET.get('payment_method')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if member_filter:
        receipts = receipts.filter(member_id=member_filter)
    
    if payment_method:
        receipts = receipts.filter(payment_method=payment_method)
    
    if start_date:
        receipts = receipts.filter(date__date__gte=start_date)
    
    if end_date:
        receipts = receipts.filter(date__date__lte=end_date)
    
    # Get statistics
    total_amount = receipts.aggregate(total=Sum('amount'))['total'] or 0
    total_count = receipts.count()
    average_amount = total_amount / total_count if total_count > 0 else 0
    
    # Get members for filter
    members = Member.objects.filter(active=True).order_by('name')
    
    context = {
        'receipts': receipts,
        'total_amount': total_amount,
        'total_count': total_count,
        'average_amount': average_amount,
        'members': members,
        'finance_active': True,
    }
    return render(request, 'finance/receipt_list.html', context)


@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(TitheReceipt, pk=pk, user=request.user)
    
    context = {
        'receipt': receipt,
        'finance_active': True,
    }
    return render(request, 'finance/receipt_detail.html', context)


@login_required
def download_receipt(request, pk):
    receipt = get_object_or_404(TitheReceipt, pk=pk, user=request.user)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.receipt_number}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Receipt Information'])
    writer.writerow(['Receipt Number', receipt.receipt_number])
    writer.writerow(['Member Name', receipt.member.name])
    writer.writerow(['Amount', f'${receipt.amount}'])
    writer.writerow(['Payment Method', receipt.get_payment_method_display()])
    writer.writerow(['Date', receipt.date.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Notes', receipt.notes or 'N/A'])
    
    return response


# ====== API ENDPOINTS ======

@login_required
def financial_summary_api(request):
    """API endpoint for financial summary data"""
    transactions = Transaction.objects.filter(user=request.user, status='COMPLETED')
    
    # Last 6 months data
    six_months_ago = timezone.now().date() - timedelta(days=180)
    recent_transactions = transactions.filter(date__gte=six_months_ago)
    
    monthly_data = []
    for i in range(6):
        month_date = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_transactions = recent_transactions.filter(date__month=month_date.month, date__year=month_date.year)
        
        income = month_transactions.filter(type='Income').aggregate(total=Sum('amount'))['total'] or 0
        expenses = month_transactions.filter(type='Expense').aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_data.append({
            'month': month_date.strftime('%b %Y'),
            'income': float(income),
            'expenses': float(expenses),
            'net': float(income - expenses)
        })
    
    return JsonResponse({
        'monthly_data': monthly_data[::-1],  # Reverse to show oldest to newest
        'total_income': float(transactions.filter(type='Income').aggregate(total=Sum('amount'))['total'] or 0),
        'total_expenses': float(transactions.filter(type='Expense').aggregate(total=Sum('amount'))['total'] or 0),
        'balance': float(transactions.filter(type='Income').aggregate(total=Sum('amount'))['total'] or 0 - 
                      transactions.filter(type='Expense').aggregate(total=Sum('amount'))['total'] or 0)
    })


# ====== PLEDGE VIEWS ======

@login_required
def pledge_list(request):
    """List all event pledges with filtering"""
    
    # Filter parameters
    status = request.GET.get('status')
    event_id = request.GET.get('event')
    member_id = request.GET.get('member')
    overdue_only = request.GET.get('overdue') == '1'
    
    # Base query
    pledges = EventPledge.objects.select_related('event', 'member').order_by('-created_at')
    
    # Apply filters
    if status and status.strip():
        pledges = pledges.filter(status=status)
    if event_id and event_id.strip():
        pledges = pledges.filter(event_id=event_id)
    if member_id and member_id.strip():
        pledges = pledges.filter(member_id=member_id)
    if overdue_only:
        from django.utils import timezone
        pledges = pledges.filter(status='OVERDUE') | pledges.filter(
            due_date__lt=timezone.now().date(),
            status__in=['PENDING', 'PARTIAL']
        )
    
    # Statistics (before pagination)
    total_promised = pledges.aggregate(total=Sum('promised_amount'))['total'] or 0
    total_paid = pledges.aggregate(total=Sum('paid_amount'))['total'] or 0
    total_remaining = total_promised - total_paid
    
    # Status counts (global counts)
    status_counts = {
        'PENDING': EventPledge.objects.filter(status='PENDING').count(),
        'PARTIAL': EventPledge.objects.filter(status='PARTIAL').count(),
        'COMPLETED': EventPledge.objects.filter(status='COMPLETED').count(),
        'OVERDUE': EventPledge.objects.filter(status='OVERDUE').count(),
    }
    
    # Pagination - 20 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(pledges, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get events and members for filter dropdowns
    events = Event.objects.filter(pledges__isnull=False).distinct()
    members = Member.objects.filter(pledges__isnull=False).distinct()
    
    context = {
        'page_obj': page_obj,
        'pledges': page_obj,
        'total_promised': total_promised,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'status_counts': status_counts,
        'events': events,
        'members': members,
        'selected_status': status,
        'selected_event': event_id,
        'selected_member': member_id,
        'overdue_only': overdue_only,
    }
    return render(request, 'finance/pledge_list.html', context)


@login_required
def pledge_detail(request, pk):
    """View pledge details and payment history """
    from django.db.models import Sum
    
    pledge = get_object_or_404(EventPledge.objects.select_related('event', 'member', 'user'), pk=pk)
    payments = pledge.payments.select_related('received_by').order_by('-payment_date')
    
    context = {
        'pledge': pledge,
        'payments': payments,
        'remaining': pledge.remaining_amount,
        'progress': pledge.progress_percentage,
    }
    return render(request, 'finance/pledge_detail.html', context)


@login_required
def pledge_create(request):
    """Create new pledge(s) - supports bulk creation with individual amounts and external pledgers"""
    
    if request.method == 'POST':
        event_id = request.POST.get('event')
        due_date = request.POST.get('due_date') or None
        
        # Get arrays of data
        member_ids = request.POST.getlist('member_ids[]')
        amounts = request.POST.getlist('amounts[]')
        external_names = request.POST.getlist('external_names[]')
        external_phones = request.POST.getlist('external_phones[]')
        entry_notes = request.POST.getlist('entry_notes[]')
        
        created_count = 0
        skipped_count = 0
        error_messages = []
        
        # Process each pledge entry
        for i in range(len(amounts)):
            amount = amounts[i] if i < len(amounts) else None
            if not amount or float(amount) <= 0:
                continue
            
            member_id = member_ids[i] if i < len(member_ids) else ''
            external_name = external_names[i].strip() if i < len(external_names) else ''
            external_phone = external_phones[i].strip() if i < len(external_phones) else ''
            notes = entry_notes[i] if i < len(entry_notes) else ''
            
            # Check if pledge already exists
            if member_id:
                if EventPledge.objects.filter(event_id=event_id, member_id=member_id).exists():
                    skipped_count += 1
                    continue
            elif external_name:
                if EventPledge.objects.filter(
                    event_id=event_id, 
                    member__isnull=True,
                    external_name__iexact=external_name,
                    external_phone=external_phone
                ).exists():
                    skipped_count += 1
                    continue
            else:
                error_messages.append(f'Entry #{i+1}: Must have member or external name')
                continue
            
            try:
                EventPledge.objects.create(
                    user=request.user,
                    created_by=request.user,
                    modified_by=request.user,
                    event_id=event_id,
                    member_id=member_id if member_id else None,
                    external_name=external_name if not member_id else None,
                    external_phone=external_phone if not member_id else None,
                    promised_amount=amount,
                    due_date=due_date,
                    notes=notes,
                    status='PENDING'
                )
                created_count += 1
            except Exception as e:
                error_messages.append(f'Entry #{i+1}: {str(e)}')
        
        if created_count > 0:
            messages.success(request, f'Ahadi {created_count} zimeundwa kwa mafanikio!')
        if skipped_count > 0:
            messages.warning(request, f'Ahadi {skipped_count} zimepitiwa (zipo tayari)')
        if error_messages:
            for msg in error_messages[:5]:  # Show first 5 errors
                messages.error(request, msg)
        
        return redirect('pledge_list')
    
    # Get available events

    events = Event.objects.filter(
        status__in=['PUBLISHED', 'COMPLETED'],
        start_date__gte=timezone.now().date() - timedelta(days=30)
    ).order_by('-start_date')
    
    context = {
        'events': events,
    }
    return render(request, 'finance/pledge_create_multi.html', context)


@csrf_exempt
@login_required
def member_search_api(request):
    """API endpoint for member search autocomplete"""

    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse([], safe=False)

    try:
        members = Member.objects.filter(
            Q(name__icontains=query) |
            Q(telephone__icontains=query)
        ).order_by('name')[:10]

        # Serialize member data to JSON
        member_data = []
        for member in members:
            member_data.append({
                'id': member.id,
                'name': member.name,
                'telephone': str(member.telephone) if member.telephone else '',
                'active': member.active
            })

        return JsonResponse(member_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def pledge_edit(request, pk):
    """Edit an existing pledge"""
    from .models import EventPledge
    from events.models import Event
    from member.models import Member
    
    pledge = get_object_or_404(EventPledge, pk=pk)
    
    if request.method == 'POST':
        pledge.promised_amount = request.POST.get('promised_amount')
        pledge.due_date = request.POST.get('due_date') or None
        pledge.notes = request.POST.get('notes')
        pledge.status = request.POST.get('status', pledge.status)
        pledge.modified_by = request.user
        pledge.save()
        
        messages.success(request, 'Ahadi imesasishwa kwa mafanikio!')
        return redirect('pledge_detail', pk=pledge.pk)
    
    events = Event.objects.filter(status__in=['PUBLISHED', 'COMPLETED'])
    members = Member.objects.filter(active=True)
    
    context = {
        'pledge': pledge,
        'events': events,
        'members': members,
    }
    return render(request, 'finance/pledge_form.html', context)


@login_required
def pledge_delete(request, pk):
    """Delete a pledge"""
    from .models import EventPledge
    
    pledge = get_object_or_404(EventPledge, pk=pk, user=request.user)
    
    if request.method == 'POST':
        pledge.soft_delete(request.user)
        messages.success(request, 'Ahadi imefutwa kwa mafanikio!')
        return redirect('pledge_list')
    
    context = {'pledge': pledge}
    return render(request, 'finance/pledge_delete.html', context)


@login_required
def pledge_payment_add(request, pledge_pk):
    """Add a payment to a pledge"""
    from .models import EventPledge, PledgePayment
    
    pledge = get_object_or_404(EventPledge, pk=pledge_pk)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'CASH')
        payment_date = request.POST.get('payment_date')
        notes = request.POST.get('notes')
        
        payment = PledgePayment.objects.create(
            pledge=pledge,
            created_by=request.user,
            modified_by=request.user,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            received_by=request.user,
            notes=notes
        )
        
        messages.success(request, f'Malipo ya {amount} yamerekodiwa kwa mafanikio! Ujumbe wa SMS umetumwa.')
        return redirect('pledge_detail', pk=pledge.pk)
    
    context = {
        'pledge': pledge,
        'remaining': pledge.remaining_amount,
    }
    return render(request, 'finance/pledge_payment_form.html', context)


@login_required
def pledge_payment_delete(request, pk):
    """Delete a pledge payment"""
    
    payment = get_object_or_404(PledgePayment, pk=pk)
    pledge_pk = payment.pledge.pk
    
    if request.method == 'POST':
        # Recalculate pledge paid amount
        pledge = payment.pledge
        pledge_pk = pledge.pk
        payment.soft_delete(request.user)
        pledge.paid_amount = pledge.payments.aggregate(total=Sum('amount'))['total'] or 0
        pledge.update_status()
        
        messages.success(request, 'Malipo yamefutwa kwa mafanikio!')
        return redirect('pledge_detail', pk=pledge_pk)
    
    context = {'payment': payment}
    return render(request, 'finance/pledge_payment_delete.html', context)


@login_required
def pledge_send_reminder(request, pk):
    """Send SMS reminder for a pledge"""
    
    pledge = get_object_or_404(EventPledge, pk=pk)
    
    if pledge.remaining_amount <= 0:
        messages.warning(request, 'Ahadi hii imeshalipwa kamili!')
        return redirect('pledge_detail', pk=pk)
    
    success = pledge.send_reminder_sms()
    
    if success:
        messages.success(request, f'Ujumbe wa kikumbusho umetumwa kwa {pledge.pledger_name}!')
    else:
        messages.error(request, 'Imeshindwa kutuma ujumbe wa SMS. Angalia kama mtoa ahadi ana namba ya simu sahihi.')
    
    return redirect('pledge_detail', pk=pk)


@login_required
def pledge_bulk_reminder(request):
    """Send reminders to all members with overdue or pending pledges"""
    
    if request.method == 'POST':
        # Get overdue and pending pledges
        pledges = EventPledge.objects.filter(
            Q(status='OVERDUE') | 
            Q(status='PENDING', due_date__lt=timezone.now().date()) |
            Q(status='PARTIAL'),
            paid_amount__lt=F('promised_amount')
        )
        
        sent_count = 0
        failed_count = 0
        
        for pledge in pledges:
            success = pledge.send_reminder_sms()
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        messages.success(request, f'Vikumbusho vimetumwa: {sent_count} vimefanikiwa, {failed_count} vimeshindwa.')
        return redirect('pledge_list')
    
    return redirect('pledge_list')

