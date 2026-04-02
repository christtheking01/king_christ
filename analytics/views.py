from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncWeek, ExtractYear
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from tithe.models import TithePayment
from finance.models import Transaction, Category, Budget, Payroll, ExpenseReport
from member.models import Member, Ministry, Community
from users.models import User
from .models import AnalyticsCache


def get_date_range(request):
    """Get date range from request parameters"""
    period = request.GET.get('period', 'year')
    
    end_date = timezone.now()
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - relativedelta(months=1)
    elif period == 'quarter':
        start_date = end_date - relativedelta(months=3)
    elif period == 'year':
        start_date = end_date - relativedelta(years=1)
    else:
        # Custom date range
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
        else:
            start_date = end_date - relativedelta(years=1)
    
    return start_date, end_date


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    start_date, end_date = get_date_range(request)
    
    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'active_page': 'analytics',
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
def tithe_analytics_api(request):
    """ API endpoint for tithe analytics data """
    try:
        start_date, end_date = get_date_range(request)
        
        cache_key = f'tithe_analytics_{start_date.date()}_{end_date.date()}'
        
        def generate_data():
            # Monthly tithe trends
            monthly_data = TithePayment.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).annotate(
                month=TruncMonth('date')
            ).values('month').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('month')
            
            months = []
            amounts = []
            counts = []
            
            for entry in monthly_data:
                months.append(entry['month'].strftime('%b %Y'))
                amounts.append(float(entry['total'] or 0))
                counts.append(entry['count'])
            
            # Top contributors
            top_contributors = TithePayment.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).values('name__name').annotate(
                total=Sum('amount'),
                payments=Count('id')
            ).order_by('-total')[:10]
            
            # Summary statistics
            total_tithes = TithePayment.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_payments = TithePayment.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).count()
            
            avg_tithe = TithePayment.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(avg=Avg('amount'))['avg'] or 0
            
            # Year-over-year comparison
            previous_start = start_date - relativedelta(years=1)
            previous_end = end_date - relativedelta(years=1)
            
            previous_total = TithePayment.objects.filter(
                date__gte=previous_start,
                date__lte=previous_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            yoy_change = 0
            if previous_total > 0:
                yoy_change = ((total_tithes - previous_total) / previous_total) * 100
            
            return {
                'monthly_labels': months,
                'monthly_amounts': amounts,
                'monthly_counts': counts,
                'top_contributors': list(top_contributors),
                'summary': {
                    'total_tithes': float(total_tithes),
                    'total_payments': total_payments,
                    'average_tithe': float(avg_tithe),
                    'yoy_change': round(yoy_change, 2)
                }
            }
        
        data = AnalyticsCache.get_or_create(cache_key, generate_data, ttl_hours=1)
        return JsonResponse(data)
    except Exception as e:
        import traceback
        print(f"Tithe Analytics Error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'monthly_labels': [],
            'monthly_amounts': [],
            'monthly_counts': [],
            'top_contributors': [],
            'summary': {
                'total_tithes': 0,
                'total_payments': 0,
                'average_tithe': 0,
                'yoy_change': 0
            }
        }, status=200)


@login_required
def finance_analytics_api(request):
    """API endpoint for finance analytics data"""
    try:
        start_date, end_date = get_date_range(request)
        
        cache_key = f'finance_analytics_{start_date.date()}_{end_date.date()}'
        
        def generate_data():
            # Income vs Expense
            income = Transaction.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                type='Income',
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            expense = Transaction.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                type='Expense',
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Category breakdown
            category_data = Transaction.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                status='COMPLETED'
            ).values('category__name', 'type').annotate(
                total=Sum('amount')
            ).order_by('-total')
            
            categories = {}
            for entry in category_data:
                cat_name = entry['category__name']
                if cat_name not in categories:
                    categories[cat_name] = {'income': 0, 'expense': 0}
                if entry['type'] == 'Income':
                    categories[cat_name]['income'] = float(entry['total'])
                else:
                    categories[cat_name]['expense'] = float(entry['total'])
            
            # Monthly trends
            monthly_finance = Transaction.objects.filter(
                date__gte=start_date,
                date__lte=end_date,
                status='COMPLETED'
            ).annotate(
                month=TruncMonth('date')
            ).values('month', 'type').annotate(
                total=Sum('amount')
            ).order_by('month')
            
            months = []
            income_data = []
            expense_data = []
            
            current_month = start_date
            while current_month <= end_date:
                month_str = current_month.strftime('%b %Y')
                months.append(month_str)
                
                month_income = next(
                    (float(m['total']) for m in monthly_finance 
                     if m['month'].strftime('%b %Y') == month_str and m['type'] == 'Income'),
                    0
                )
                month_expense = next(
                    (float(m['total']) for m in monthly_finance 
                     if m['month'].strftime('%b %Y') == month_str and m['type'] == 'Expense'),
                    0
                )
                
                income_data.append(month_income)
                expense_data.append(month_expense)
                
                current_month += relativedelta(months=1)
            
            # Budget utilization
            active_budgets = Budget.objects.filter(
                status='ACTIVE',
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            budget_data = []
            for budget in active_budgets:
                budget_data.append({
                    'name': budget.name,
                    'total': float(budget.total_amount),
                    'spent': float(budget.spent_amount),
                    'remaining': float(budget.remaining_amount),
                    'utilization': round((budget.spent_amount / budget.total_amount * 100), 2) if budget.total_amount > 0 else 0
                })
            
            return {
                'summary': {
                    'total_income': float(income),
                    'total_expense': float(expense),
                    'net': float(income - expense)
                },
                'category_breakdown': categories,
                'monthly_labels': months,
                'monthly_income': income_data,
                'monthly_expense': expense_data,
                'budget_utilization': budget_data
            }
        
        data = AnalyticsCache.get_or_create(cache_key, generate_data, ttl_hours=1)
        return JsonResponse(data)
    except Exception as e:
        import traceback
        print(f"Finance Analytics Error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'summary': {
                'total_income': 0,
                'total_expense': 0,
                'net': 0
            },
            'category_breakdown': {},
            'monthly_labels': [],
            'monthly_income': [],
            'monthly_expense': [],
            'budget_utilization': []
        }, status=200)


@login_required
def member_analytics_api(request):
    """API endpoint for member analytics data"""
    try:
        cache_key = 'member_analytics'
        
        def generate_data():
            # Total members
            total_members = Member.objects.count()
            active_members = Member.objects.filter(is_active=True).count()
            
            # Ministry distribution
            ministry_data = Ministry.objects.annotate(
                member_count=Count('members', filter=Q(members__is_active=True))
            ).values('name', 'member_count').order_by('-member_count')
            
            # Community distribution
            community_data = Community.objects.annotate(
                member_count=Count('members', filter=Q(members__is_active=True))
            ).values('name', 'member_count').order_by('-member_count')
            
            # Gender distribution (if gender field exists)
            gender_data = Member.objects.filter(
                is_active=True
            ).values('gender').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Age groups (if birth_date field exists)
            from django.utils import timezone
            from datetime import date
            
            age_groups = {
                '18-25': 0,
                '26-35': 0,
                '36-45': 0,
                '46-60': 0,
                '60+': 0
            }
            
            current_year = timezone.now().year
            for member in Member.objects.filter(is_active=True, birth_date__isnull=False):
                age = current_year - member.birth_date.year
                if 18 <= age <= 25:
                    age_groups['18-25'] += 1
                elif 26 <= age <= 35:
                    age_groups['26-35'] += 1
                elif 36 <= age <= 45:
                    age_groups['36-45'] += 1
                elif 46 <= age <= 60:
                    age_groups['46-60'] += 1
                elif age > 60:
                    age_groups['60+'] += 1
            
            # Membership growth (members joined by month)
            growth_data = Member.objects.filter(
                created_at__gte=timezone.now() - relativedelta(years=1)
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            growth_months = []
            growth_counts = []
            
            for entry in growth_data:
                growth_months.append(entry['month'].strftime('%b %Y'))
                growth_counts.append(entry['count'])
            
            return {
                'summary': {
                    'total_members': total_members,
                    'active_members': active_members,
                    'inactive_members': total_members - active_members
                },
                'ministry_distribution': list(ministry_data),
                'community_distribution': list(community_data),
                'gender_distribution': list(gender_data),
                'age_groups': age_groups,
                'growth': {
                    'months': growth_months,
                    'counts': growth_counts
                }
            }
        
        data = AnalyticsCache.get_or_create(cache_key, generate_data, ttl_hours=6)
        return JsonResponse(data)
    except Exception as e:
        import traceback
        print(f"Member Analytics Error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'summary': {
                'total_members': 0,
                'active_members': 0,
                'inactive_members': 0
            },
            'ministry_distribution': [],
            'community_distribution': [],
            'gender_distribution': [],
            'age_groups': {},
            'growth': {
                'months': [],
                'counts': []
            }
        }, status=200)


@login_required
def tithing_report(request):
    """Generate detailed tithing report"""
    start_date, end_date = get_date_range(request)
    
    # Get all tithes in date range
    tithes = TithePayment.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).select_related('name').order_by('-date')
    
    # Summary
    summary = tithes.aggregate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount')
    )
    
    # Monthly breakdown
    monthly = tithes.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')
    
    # Payment method breakdown
    by_method = tithes.values('status').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    context = {
        'tithes': tithes,
        'summary': summary,
        'monthly_data': monthly,
        'by_method': by_method,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'analytics/tithing_report.html', context)


@login_required
def financial_report(request):
    """Generate detailed financial report"""
    start_date, end_date = get_date_range(request)
    
    transactions = Transaction.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).select_related('category').order_by('-date')
    
    # Calculate summary
    total_income = transactions.filter(type='Income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = transactions.filter(type='Expense').aggregate(total=Sum('amount'))['total'] or 0
    net = total_income - total_expense
    
    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net': net,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'analytics/financial_report.html', context)
