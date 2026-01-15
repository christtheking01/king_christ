from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime
from .models import Category, Transaction


@login_required
def dashboard(request):
    transactions = Transaction.objects.filter(user=request.user)
    
    total_income = transactions.filter(type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses = transactions.filter(type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expenses
    
    recent_transactions = transactions[:5]
    
    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'finance/dashboard.html', context)


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)
    
    transaction_type = request.GET.get('type')
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if transaction_type:
        transactions = transactions.filter(type=transaction_type)
    
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
    }
    return render(request, 'finance/transaction_list.html', context)



def add_transaction(request):
    if request.method == 'POST':
        transaction_type = request.POST.get('type')
        category_id = request.POST.get('category')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        
        category = get_object_or_404(Category, id=category_id, user=request.user)
        
        Transaction.objects.create(
            user=request.user,
            category=category,
            type=transaction_type,
            amount=amount,
            description=description,
            date=date
        )
        
        messages.success(request, 'Transaction added successfully!')
        return redirect('transaction_list')
    
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finance/transaction_form.html', {'categories': categories})


@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        transaction.type = request.POST.get('type')
        transaction.category_id = request.POST.get('category')
        transaction.amount = request.POST.get('amount')
        transaction.description = request.POST.get('description')
        transaction.date = request.POST.get('date')
        transaction.save()
        
        messages.success(request, 'Transaction updated successfully!')
        return redirect('transaction_list')
    
    categories = Category.objects.filter(user=request.user)
    context = {
        'transaction': transaction,
        'categories': categories,
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
    return render(request, 'finance/category_list.html', {'categories': categories})


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
    
    return render(request, 'finance/category_form.html')


@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    if category.transactions.exists():
        messages.error(request, 'Cannot delete category with existing transactions!')
        return redirect('category_list')
    
    category.delete()
    messages.success(request, 'Category deleted successfully!')
    return redirect('category_list')