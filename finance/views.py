from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import Category, Transaction, TitheReceipt, Employee, Payroll, Budget, BudgetAllocation, ExpenseReport, ExpenseItem
from member.models import Member
from django.db.models import ExpressionWrapper, FloatField,F
import csv


@login_required
def dashboard(request):
    # Enhanced dashboard with comprehensive financial overview
    transactions = Transaction.objects.filter(user=request.user)
    
    # Basic financial metrics
    total_income = transactions.filter(type='Income', status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = transactions.filter(type='Expense', status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expenses
    
    # Payroll metrics
   # employees = Employee.objects.filter(user=request.user) 
    employees = Employee.objects.annotate(total_salary=ExpressionWrapper(F('base_salary') + F('housing_allowance') + F('transport_allowance') + F('other_allowances'),
                                                                          output_field=FloatField())).order_by('-total_salary')
    total_monthly_payroll = employees.aggregate(total=Sum('total_salary'))['total'] or 0
    
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
    return render(request, 'finance/dashboard.html', context)


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)
    
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
    
    categories = Category.objects.filter(user=request.user)
    
    context = {
        'transactions': transactions,
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
    transaction.delete()
    messages.success(request, 'Transaction deleted successfully!')
    return redirect('transaction_list')


@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/category_list.html', {
        'categories': categories,
        'finance_active': True,
    })


@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_type = request.POST.get('type')
        
        if Category.objects.filter(user=request.user, name=name).exists():
            messages.error(request, 'Category with this name already exists!')
            return redirect('add_category')
        
        Category.objects.create(
            user=request.user,
            name=name,
            type=category_type
        )
        
        messages.success(request, 'Category added successfully!')
        return redirect('category_list')
    
    return render(request, 'finance/category_form.html', {'finance_active': True})


@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    if category.transactions.exists():
        messages.error(request, 'Cannot delete category with existing transactions!')
        return redirect('category_list')
    
    category.delete()
    messages.success(request, 'Category deleted successfully!')
    return redirect('category_list')


# ====== EMPLOYEE MANAGEMENT ======

@login_required
def employee_list(request):
    employees = Employee.objects.filter(user=request.user).select_related('member')
    
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
        member_id = request.POST.get('member')
        employee_id = request.POST.get('employee_id')
        position = request.POST.get('position')
        department = request.POST.get('department')
        base_salary = request.POST.get('base_salary')
        housing_allowance = request.POST.get('housing_allowance', 0)
        transport_allowance = request.POST.get('transport_allowance', 0)
        other_allowances = request.POST.get('other_allowances', 0)
        payment_type = request.POST.get('payment_type')
        bank_account = request.POST.get('bank_account')
        bank_name = request.POST.get('bank_name')
        tax_id = request.POST.get('tax_id')
        hire_date = request.POST.get('hire_date')
        
        member = get_object_or_404(Member, id=member_id)
        
        Employee.objects.create(
            user=request.user,
            member=member,
            employee_id=employee_id,
            position=position,
            department=department,
            base_salary=base_salary,
            housing_allowance=housing_allowance,
            transport_allowance=transport_allowance,
            other_allowances=other_allowances,
            payment_type=payment_type,
            bank_account=bank_account,
            bank_name=bank_name,
            tax_id=tax_id,
            hire_date=hire_date
        )
        
        messages.success(request, 'Employee added successfully!')
        return redirect('employee_list')
    
    members = Member.objects.filter(active=True).order_by('name')
    return render(request, 'finance/employee_form.html', {
        'members': members,
        'finance_active': True,
    })


@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk, user=request.user)
    
    if request.method == 'POST':
        employee.position = request.POST.get('position')
        employee.department = request.POST.get('department')
        employee.base_salary = request.POST.get('base_salary')
        employee.housing_allowance = request.POST.get('housing_allowance', 0)
        employee.transport_allowance = request.POST.get('transport_allowance', 0)
        employee.other_allowances = request.POST.get('other_allowances', 0)
        employee.payment_type = request.POST.get('payment_type')
        employee.bank_account = request.POST.get('bank_account')
        employee.bank_name = request.POST.get('bank_name')
        employee.tax_id = request.POST.get('tax_id')
        employee.status = request.POST.get('status')
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
    employee.delete()
    messages.success(request, 'Employee deleted successfully!')
    return redirect('employee_list')


# ====== PAYROLL MANAGEMENT ======

@login_required
def payroll_list(request):
    payrolls = Payroll.objects.filter(user=request.user).select_related('employee__member')
    
    status_filter = request.GET.get('status')
    month_filter = request.GET.get('month')
    
    if status_filter:
        payrolls = payrolls.filter(status=status_filter)
    
    if month_filter:
        payrolls = payrolls.filter(pay_period_end__month=month_filter)
    
    # Calculate statistics
    pending_count = payrolls.filter(status='PENDING').count()
    processed_count = payrolls.filter(status='PROCESSED').count()
    paid_count = payrolls.filter(status='PAID').count()
    total_net_salary = sum(payroll.net_salary for payroll in payrolls)
    
    context = {
        'payrolls': payrolls,
        'pending_count': pending_count,
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
        
        # Calculate payroll
        basic_salary = employee.base_salary
        housing_allowance = employee.housing_allowance
        transport_allowance = employee.transport_allowance
        other_allowances = employee.other_allowances
        gross_salary = basic_salary + housing_allowance + transport_allowance + other_allowances
        
        # Simple tax calculation (you can make this more sophisticated)
        tax_deduction = gross_salary * 0.1  # 10% tax
        other_deductions = 0
        net_salary = gross_salary - tax_deduction - other_deductions
        
        payroll = Payroll.objects.create(
            user=request.user,
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            basic_salary=basic_salary,
            housing_allowance=housing_allowance,
            transport_allowance=transport_allowance,
            other_allowances=other_allowances,
            gross_salary=gross_salary,
            tax_deduction=tax_deduction,
            other_deductions=other_deductions,
            net_salary=net_salary,
            status='PENDING'
        )
        
        messages.success(request, f'Payroll generated for {employee.member.name}!')
        return redirect('payroll_list')
    
    employees = Employee.objects.filter(user=request.user, status='ACTIVE')
    return render(request, 'finance/payroll_form.html', {
        'employees': employees,
        'finance_active': True,
    })


@login_required
def process_payroll(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk, user=request.user)
    
    if payroll.status == 'PENDING':
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
            category=category,
            amount=payroll.net_salary,
            description=f'Salary payment to {payroll.employee.member.name}',
            date=timezone.now().date(),
            type='Expense',
            status='COMPLETED',
            reference_number=f'PAY-{payroll.id}'
        )
        
        messages.success(request, 'Payroll processed successfully!')
    else:
        messages.error(request, 'Payroll cannot be processed!')
    
    return redirect('payroll_list')


# ====== BUDGET MANAGEMENT ======

@login_required
def budget_list(request):
    budgets = Budget.objects.filter(user=request.user).prefetch_related('allocations__category')
    
    status_filter = request.GET.get('status')
    if status_filter:
        budgets = budgets.filter(status=status_filter)
    
    # Calculate totals and add usage percentages to budgets
    total_budget_amount = sum(budget.total_amount for budget in budgets)
    total_spent_amount = sum(budget.spent_amount for budget in budgets)
    total_remaining_amount = sum(budget.remaining_amount for budget in budgets)
    
    # Add usage percentage to each budget for template
    for budget in budgets:
        if budget.total_amount > 0:
            budget.usage_percentage = (budget.spent_amount / budget.total_amount) * 100
        else:
            budget.usage_percentage = 0
    
    context = {
        'budgets': budgets,
        'total_budget_amount': total_budget_amount,
        'total_spent_amount': total_spent_amount,
        'total_remaining_amount': total_remaining_amount,
        'finance_active': True,
    }
    return render(request, 'finance/budget_list.html', context)


@login_required
def create_budget(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        total_amount = request.POST.get('total_amount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        budget = Budget.objects.create(
            user=request.user,
            name=name,
            description=description,
            total_amount=total_amount,
            start_date=start_date,
            end_date=end_date
        )
        
        messages.success(request, 'Budget created successfully!')
        return redirect('budget_detail', pk=budget.pk)
    
    return render(request, 'finance/budget_form.html', {'finance_active': True})


@login_required
def budget_detail(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    allocations = budget.allocations.all().select_related('category')
    
    # Calculate totals
    total_allocated = sum(allocation.allocated_amount for allocation in allocations)
    total_spent = sum(allocation.spent_amount for allocation in allocations)
    total_remaining = sum(allocation.remaining_amount for allocation in allocations)
    
    # Calculate budget usage percentage
    if budget.total_amount > 0:
        budget.usage_percentage = (budget.spent_amount / budget.total_amount) * 100
    else:
        budget.usage_percentage = 0
    
    # Add usage percentage to each allocation
    for allocation in allocations:
        if allocation.allocated_amount > 0:
            allocation.usage_percentage = (allocation.spent_amount / allocation.allocated_amount) * 100
        else:
            allocation.usage_percentage = 0
    
    context = {
        'budget': budget,
        'allocations': allocations,
        'total_allocated': total_allocated,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
        'finance_active': True,
    }
    return render(request, 'finance/budget_detail.html', context)


# ====== EXPENSE REPORTS ======

@login_required
def expense_report_list(request):
    expense_reports = ExpenseReport.objects.filter(user=request.user).select_related('employee__member')
    
    status_filter = request.GET.get('status')
    if status_filter:
        expense_reports = expense_reports.filter(status=status_filter)
    
    # Calculate total amount
    total_expense_amount = sum(report.total_amount for report in expense_reports)
    
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
        
        expense_report = ExpenseReport.objects.create(
            user=request.user,
            employee=employee,
            title=title,
            description=description,
            total_amount=0  # Will be calculated from items
        )
        
        messages.success(request, 'Expense report created successfully!')
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
    
    # Get members for filter
    members = Member.objects.filter(active=True).order_by('name')
    
    context = {
        'receipts': receipts,
        'total_amount': total_amount,
        'total_count': total_count,
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