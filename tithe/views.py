from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import csv
import json
import hashlib
import hmac
import time

from .models import TithePayment, TitheReceipt
from .forms import TithePaymentForm
from member.models import Member


class TithePaymentListView(LoginRequiredMixin, ListView):
    model = TithePayment
    template_name = 'tithepayment/list.html'
    context_object_name = 'payments'
    paginate_by = 25
    ordering = ['-date']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality - using 'name' field
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__name__icontains=search_query) |
                Q(contact_number__icontains=search_query) |
                Q(amount__icontains=search_query)
            )
        
        # Filter by payment method
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    date__date__range=[start_date_obj, end_date_obj]
                )
            except ValueError:
                pass
        
        # Filter by member
        member_id = self.request.GET.get('member')
        if member_id:
            queryset = queryset.filter(name_id=member_id)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add summary statistics
        queryset = self.get_queryset()
        context['total_amount'] = queryset.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        context['total_payments'] = queryset.count()
        
        # Payment method counts
        context['cash_payments'] = queryset.filter(status='cash').count()
        context['bank_payments'] = queryset.filter(status='bank').count()
        
        # Add filter options
        context['members'] = Member.objects.all().order_by('name')
        context['status_choices'] = TithePayment.PAYMENT_STATUS_CHOICES
        
        # Preserve filter parameters
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'member': self.request.GET.get('member', ''),
        }
        
        # Get member payment history (April to December of selected year)
        from django.db.models.functions import TruncMonth
        import calendar
        
        # Get available years from payments
        available_years = TithePayment.objects.dates('date', 'year', order='DESC')
        available_years_list = [year.year for year in available_years]
        
        # Determine selected year
        selected_year = self.request.GET.get('history_year')
        if selected_year:
            try:
                selected_year = int(selected_year)
            except ValueError:
                selected_year = None
        else:
            # Auto-select appropriate default year
            current_month = timezone.now().month
            if current_month >= 4:  # April onwards
                selected_year = timezone.now().year
            else:  # Jan-March, show previous year
                selected_year = timezone.now().year - 1
        
        # If no payments exist, default to current year
        if not available_years_list:
            selected_year = timezone.now().year
        # Ensure selected year is in available years, default to most recent if not
        elif selected_year not in available_years_list and available_years_list:
            selected_year = available_years_list[0]
        
        # Get filter parameters
        history_search = self.request.GET.get('history_search', '')
        history_community = self.request.GET.get('history_community', '')
        
        # Get all members who have made payments in selected year
        members_with_payments = Member.objects.filter(
            tithepayment__date__year=selected_year
        ).distinct().order_by('name')
        
        # Apply search filter
        if history_search:
            members_with_payments = members_with_payments.filter(
                name__icontains=history_search
            )
        
        # Apply community filter
        if history_community:
            members_with_payments = members_with_payments.filter(
                shepherd_id=history_community
            )
        
        # Pagination for member history
        from django.core.paginator import Paginator
        paginator = Paginator(members_with_payments, 20)  # 20 members per page
        history_page = self.request.GET.get('history_page', 1)
        try:
            members_page = paginator.page(history_page)
        except:
            members_page = paginator.page(1)
        
        member_payment_history = []
        for member in members_page:
            # Get payments from April to December for this member
            member_payments = TithePayment.objects.filter(
                name=member,
                date__year=selected_year,
                date__month__gte=4  # April onwards
            ).order_by('date')
            
            # Calculate total
            total_amount = member_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            # Group by month
            monthly_data = {}
            for month_num in range(4, 13):  # April to December
                month_name = calendar.month_name[month_num]
                month_payments = member_payments.filter(date__month=month_num)
                month_total = month_payments.aggregate(total=Sum('amount'))['total'] or 0
                monthly_data[month_name] = month_total
            
            member_payment_history.append({
                'member': member,
                'total_amount': total_amount,
                'payment_count': member_payments.count(),
                'monthly_data': monthly_data,
            })
        
        # Group by community
        from member.models import Community
        communities_data = []
        for community in Community.objects.all():
            community_members = [m for m in member_payment_history if m['member'].shepherd_id == community.id]
            if community_members:
                community_total = sum(m['total_amount'] for m in community_members)
                community_monthly_totals = {}
                for month in [calendar.month_name[m] for m in range(4, 13)]:
                    community_monthly_totals[month] = sum(m['monthly_data'].get(month, 0) for m in community_members)
                
                communities_data.append({
                    'community': community,
                    'members': community_members,
                    'total_amount': community_total,
                    'monthly_totals': community_monthly_totals,
                })
        
        context['member_payment_history'] = member_payment_history
        context['communities_data'] = communities_data
        context['months'] = [calendar.month_name[m] for m in range(4, 13)]  # April to December
        context['members_page'] = members_page
        context['history_search'] = history_search
        context['history_community'] = history_community
        context['communities'] = Community.objects.all()
        context['selected_year'] = selected_year
        context['available_years'] = available_years_list
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_list'] = True
        
        return context


class TithePaymentDetailView(LoginRequiredMixin, DetailView):
    model = TithePayment
    template_name = 'tithepayment/detail.html'
    context_object_name = 'payment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related payments from the same member
        context['related_payments'] = TithePayment.objects.filter(
            name=self.object.name
        ).exclude(id=self.object.id).order_by('-date')[:10]
        
        # Add member's total contributions
        context['member_total_contributions'] = TithePayment.objects.filter(
            name=self.object.name
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['member_payment_count'] = TithePayment.objects.filter(
            name=self.object.name
        ).count()
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_list'] = True
        
        return context


class TithePaymentCreateView(LoginRequiredMixin, CreateView):
    model = TithePayment
    form_class = TithePaymentForm
    template_name = 'tithepayment/create.html'
    success_url = reverse_lazy('tithepayment:tithepayment_list')

    def get_initial(self):
        initial = super().get_initial()
        # Set default date to today
        initial['date'] = timezone.now()
        
        # Pre-fill member if provided in URL
        member_id = self.request.GET.get('member')
        if member_id:
            try:
                member = Member.objects.get(id=member_id)
                initial['name'] = member
            except Member.DoesNotExist:
                pass
        
        return initial

    def form_valid(self, form):
        # Auto-populate contact number from selected member
        member = form.cleaned_data['name']
        tithe_payment = form.save(commit=False)
        tithe_payment.contact_number = str(member.telephone) if member.telephone else ''
        tithe_payment.save()  # Save the payment first
        
        # Set self.object so get_success_url() works properly
        self.object = tithe_payment
        
        # Auto-generate receipt if enabled
        if getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True):
            # Safely get user name
            user = self.request.user
            if user:
                full_name = user.get_full_name() if hasattr(user, 'get_full_name') else None
                username = user.username if hasattr(user, 'username') else 'System'
                generated_by = full_name if full_name else username
            else:
                generated_by = 'System'
            
            receipt, created = TitheReceipt.objects.get_or_create(
                tithe_payment=tithe_payment,
                defaults={
                    'generated_by': generated_by,
                    'church_name': settings.CHURCH_NAME,
                    'church_address': settings.CHURCH_ADDRESS,
                    'church_phone': settings.CHURCH_PHONE,
                }
            )
            
            # Auto-print if enabled
            if created and getattr(settings, 'TITHE_AUTO_PRINT_RECEIPT', False):
                receipt.mark_printed()
                messages.info(
                    self.request,
                    f'Receipt {receipt.receipt_number} generated and marked as printed.'
                )
            elif created:
                messages.info(
                    self.request,
                    f'Receipt {receipt.receipt_number} generated. Ready to print.'
                )
        
        messages.success(
            self.request, 
            f'Tithe payment of Tsh {form.cleaned_data["amount"]} for {member.name} created successfully!'
        )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Tithe Payment'
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_create'] = True
        
        return context


class TithePaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = TithePayment
    form_class = TithePaymentForm
    template_name = 'tithepayment/create.html'
    context_object_name = 'payment'

    def form_valid(self, form):
        # Auto-populate contact number if member is changed
        member = form.cleaned_data['name']
        tithe_payment = form.save(commit=False)
        tithe_payment.contact_number = str(member.telephone) if member.telephone else ''
        
        messages.success(
            self.request, 
            f'Tithe payment for {member.name} updated successfully!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('tithepayment:tithepayment_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Tithe Payment - {self.object.name.name}'
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_list'] = True
        
        return context


class TithePaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = TithePayment
    template_name = 'tithepayment/delete.html'
    success_url = reverse_lazy('tithepayment:tithepayment_list')
    context_object_name = 'payment'

    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        member_name = payment.name.name
        amount = payment.amount
        messages.success(
            request, 
            f'Tithe payment of ${amount} for {member_name} deleted successfully!'
        )
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Delete Tithe Payment - {self.object.name.name}'
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_list'] = True
        
        return context


class TithePaymentSummaryView(LoginRequiredMixin, TemplateView):
    template_name = 'tithepayment/summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Overall statistics
        payments = TithePayment.objects.all()
        
        context['total_collected'] = payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        context['total_transactions'] = payments.count()
        context['average_payment'] = context['total_collected'] / context['total_transactions'] if context['total_transactions'] > 0 else 0
        
        # Payments by status
        context['payments_by_status'] = payments.values(
            'status'
        ).annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_payments = payments.filter(date__gte=thirty_days_ago)
        
        context['recent_total'] = recent_payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        context['recent_count'] = recent_payments.count()
        
        # Top contributors
        context['top_contributors'] = payments.values(
            'name__id', 'name__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        # Recent payments
        context['recent_payments'] = payments.order_by('-date')[:10]
        
        # Monthly breakdown (last 6 months)
        monthly_data = []
        for i in range(5, -1, -1):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_payments = payments.filter(
                date__date__range=[month_start.date(), month_end.date()]
            )
            
            monthly_data.append({
                'month': month_start.strftime('%b %Y'),
                'total': month_payments.aggregate(total=Sum('amount'))['total'] or 0,
                'count': month_payments.count()
            })
        
        context['monthly_breakdown'] = monthly_data
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_summary'] = True
        
        return context

@login_required
def search_members(request):
    """Search members by name or telephone"""
    search_term = request.GET.get('q', request.GET.get('search', '')).strip()
    
    if len(search_term) < 2:
        return JsonResponse([])
    
    try:
        members = Member.objects.filter(
            Q(name__icontains=search_term) | 
            Q(telephone__icontains=search_term) |
            Q(code__icontains=search_term)
        ).order_by('name')[:10]
        
        members_data = []
        for member in members:
            members_data.append({
                'id': member.id,
                'name': member.name,
                'telephone': str(member.telephone) if member.telephone else '',
                'code': member.code or '',
            })
        
        return JsonResponse({'members': members_data}, safe=False)
        
    except Exception as e:
        return JsonResponse([], safe=False)

@login_required
def get_member_details(request, member_id):
    """Get member details for AJAX requests - requires authentication"""
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        member = Member.objects.get(id=member_id)
        return JsonResponse({
            'id': member.id,
            'name': member.name,
            'telephone': str(member.telephone) if member.telephone else '',
            'full_name': member.name,
        })
    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def quick_add_tithe_payment(request):
    """Quick add tithe payment via AJAX - requires authentication"""
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'cash')
        
        # Validate required fields
        if not member_id or not amount:
            return JsonResponse({
                'success': False,
                'error': 'Member and amount are required'
            }, status=400)
        
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Member not found'
            }, status=404)
        
        # Create tithe payment
        tithe_payment = TithePayment(
            name=member,
            contact_number=str(member.telephone) if member.telephone else '',
            amount=amount,
            status=payment_method,
            date=timezone.now()
        )
        tithe_payment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Tithe payment of ${amount} for {member.name} added successfully!',
            'payment_id': tithe_payment.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def export_tithe_payments(request):
    """Export tithe payments to CSV - requires authentication"""
    try:
        # Get filtered queryset
        queryset = TithePayment.objects.all().order_by('-date')
        
        # Apply same filters as list view
        search_query = request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__name__icontains=search_query) |
                Q(contact_number__icontains=search_query)
            )
        
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Create HTTP response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tithe_payments.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Member Name', 'Contact Number', 'Amount', 'Payment Method'])
        
        for payment in queryset:
            writer.writerow([
                payment.date.strftime('%Y-%m-%d %H:%M'),
                payment.name.name,
                payment.contact_number,
                payment.amount,
                payment.get_status_display()
            ])
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error exporting data: {str(e)}')
        return redirect('tithepayment:tithepayment_list')


class MonthlyReportView(LoginRequiredMixin, ListView):
    template_name = 'tithepayment/monthly_report.html'
    context_object_name = 'monthly_data'

    def get_queryset(self):
        # Get payments grouped by month
        from django.db.models.functions import TruncMonth
        
        monthly_data = TithePayment.objects.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total_amount=Sum('amount'),
            payment_count=Count('id')
        ).order_by('-month')
        
        return monthly_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add year filter
        current_year = self.request.GET.get('year', timezone.now().year)
        context['selected_year'] = current_year
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_monthly'] = True
        

# Additional Views for Extended URLs

class YearlyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'tithepayment/yearly_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get selected year from query params, default to current year
        from django.utils import timezone
        selected_year = int(self.request.GET.get('year', timezone.now().year))
        context['current_year'] = selected_year
        
        # Get available years
        years = TithePayment.objects.dates('date', 'year', order='DESC')
        context['years'] = [y.year for y in years]
        
        # Get data for selected year
        year_payments = TithePayment.objects.filter(
            date__year=selected_year
        )
        
        # Calculate totals
        total_collected = year_payments.aggregate(total=Sum('amount'))['total'] or 0
        total_payments = year_payments.count()
        average_payment = total_collected / total_payments if total_payments > 0 else 0
        
        context['total_collected'] = total_collected
        context['total_payments'] = total_payments
        context['average_payment'] = average_payment
        
        # Get monthly breakdown
        from django.db.models.functions import TruncMonth
        import calendar
        
        monthly_data = year_payments.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            amount=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        # Add month names and calculate averages
        monthly_data_with_names = []
        for item in monthly_data:
            month_num = item['month'].month
            monthly_data_with_names.append({
                'month_name': calendar.month_name[month_num],
                'amount': item['amount'] or 0,
                'count': item['count'] or 0,
                'average': (item['amount'] or 0) / (item['count'] or 1)
            })
        
        context['monthly_data'] = monthly_data_with_names
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_summary'] = True
        
        return context

class MemberTitheReportView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'tithepayment/member_report.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all tithe payments for this member
        member_payments = TithePayment.objects.filter(
            name=self.object
        ).order_by('-date')
        
        context['member_payments'] = member_payments
        context['total_contributions'] = member_payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['payment_count'] = member_payments.count()
        
        # Monthly breakdown for this member
        from django.db.models.functions import TruncMonth
        
        monthly_breakdown = member_payments.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            monthly_total=Sum('amount'),
            payment_count=Count('id')
        ).order_by('-month')
        
        context['monthly_breakdown'] = monthly_breakdown
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_list'] = True
        
        return context


class TitheAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'tithepayment/analytics_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        payments = TithePayment.objects.all()
        
        # Basic stats
        context['total_collected'] = payments.aggregate(total=Sum('amount'))['total'] or 0
        context['total_payments'] = payments.count()
        context['average_payment'] = payments.aggregate(avg=Avg('amount'))['avg'] or 0
        
        # Growth metrics (last 30 days vs previous 30 days)
        today = timezone.now().date()
        last_30_start = today - timedelta(days=30)
        previous_30_start = last_30_start - timedelta(days=30)
        
        last_30_payments = payments.filter(date__date__gte=last_30_start)
        previous_30_payments = payments.filter(
            date__date__gte=previous_30_start, 
            date__date__lt=last_30_start
        )
        
        last_30_total = last_30_payments.aggregate(total=Sum('amount'))['total'] or 0
        previous_30_total = previous_30_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        context['growth_percentage'] = (
            ((last_30_total - previous_30_total) / previous_30_total * 100) 
            if previous_30_total > 0 else 0
        )
        
        # Active state for sidebar
        context['finance_active'] = True
        context['tithepayment_active_summary'] = True
        
        return context
    
@login_required
def generate_receipt(request, payment_id):
    """Generate receipt for existing tithe payment"""
    payment = get_object_or_404(TithePayment, id=payment_id)
    
    # Safely get user name
    user = request.user
    if user:
        full_name = user.get_full_name() if hasattr(user, 'get_full_name') else None
        username = user.username if hasattr(user, 'username') else 'System'
        generated_by = full_name if full_name else username
    else:
        generated_by = 'System'
    
    # Check if receipt already exists
    receipt, created = TitheReceipt.objects.get_or_create(
        tithe_payment=payment,
        defaults={
            'generated_by': generated_by,
            'church_name': settings.CHURCH_NAME,
            'church_address': settings.CHURCH_ADDRESS,
            'church_phone': settings.CHURCH_PHONE,
        }
    )
    
    if created:
        messages.success(request, f"Receipt generated: {receipt.receipt_number}")
    else:
        messages.info(request, f"Receipt already exists: {receipt.receipt_number}")
    
    return redirect('print_receipt', receipt_id=receipt.id)

@login_required
def print_receipt(request, receipt_id):
    receipt = get_object_or_404(TitheReceipt, id=receipt_id)
    
    if request.method == "POST":
        try:
            print_data = receipt.get_print_data()
            receipt.mark_printed()
            
            return JsonResponse({
                'success': True,
                'message': 'Receipt sent to printer successfully',
                'receipt_number': receipt.receipt_number
            })
        except Exception as e:
            receipt.last_print_error = str(e)
            receipt.save()
            return JsonResponse({
                'success': False,
                'message': f'Printing failed: {str(e)}'
            })
    
    context = {
        "receipt": receipt,
        "payment": receipt.tithe_payment,
        "print_data": receipt.get_print_data(),
    }
    return render(request, "tithepayment/print_receipt.html", context)

@login_required
def receipt_list(request):
    template = "tithepayment/receipt_list.html"

    if request.GET.get('ajax_counts') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'unprinted_count': TitheReceipt.objects.filter(is_printed=False).count(),
            'total_receipts': TitheReceipt.objects.count()
        })

    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    print_status = request.GET.get('print_status')
    show_unprinted = request.GET.get('show_unprinted')

    # Query payments and prefetch receipts efficiently
    payments = TithePayment.objects.select_related('name').prefetch_related(
        'receipt'
    ).order_by('-date')

    # Apply filters
    if search_query:
        payments = payments.filter(name__name__icontains=search_query)

    if start_date:
        payments = payments.filter(date__date__gte=start_date)

    if end_date:
        payments = payments.filter(date__date__lte=end_date)

    if show_unprinted:
        payments = payments.filter(receipt__is_printed=False)

    # Filter by print status
    if print_status == 'printed':
        payments = payments.filter(receipt__is_printed=True)
    elif print_status == 'unprinted':
        payments = payments.filter(receipt__is_printed=False)
    elif print_status == 'no_receipt':
        payments = payments.filter(receipt__isnull=True)

    # Build a receipt lookup dict keyed by payment id
    receipt_map = {
        r.tithe_payment_id: r
        for r in TitheReceipt.objects.select_related('tithe_payment')
    }

    # Attach receipt info to each payment object
    for payment in payments:
        receipt = receipt_map.get(payment.id)
        payment.has_receipt = receipt is not None
        payment.receipt_data = receipt

    context = {
        "payments": payments,
        "receipts_active": "active",
        "unprinted_count": TitheReceipt.objects.filter(is_printed=False).count(),
        "total_receipts": TitheReceipt.objects.count(),
        "show_unprinted": bool(show_unprinted),
        "finance_active": True,
        # Filter values for form persistence
        "search_query": search_query,
        "start_date": start_date,
        "end_date": end_date,
        "print_status": print_status,
    }
    return render(request, template, context)

@login_required
def auto_generate_receipt(request, payment_id):
    payment = get_object_or_404(TithePayment, id=payment_id)

    receipt, created = TitheReceipt.objects.get_or_create(
        tithe_payment=payment,
        defaults={
            'generated_by': request.user.get_full_name() or request.user.username,
            'church_name': getattr(settings, 'CHURCH_NAME', 'Christ The King Parish'),
            'church_address': getattr(settings, 'CHURCH_ADDRESS', ''),
            'church_phone': getattr(settings, 'CHURCH_PHONE', ''),
        }
    )

    if created:
        messages.success(request, f'Receipt {receipt.receipt_number} generated successfully.')
    else:
        messages.info(request, f'Receipt {receipt.receipt_number} already exists.')
    
    return redirect('tithepayment:receipt_list')


# =============================================================================
# POS API SECURITY FUNCTIONS
# =============================================================================

def verify_pos_api_key(request):
    """Verify POS API key if POS_API_KEY is configured"""
    configured_key = getattr(settings, 'POS_API_KEY', '')
    if not configured_key:
        return True  # No key required
    
    provided_key = request.headers.get('X-POS-API-Key') or request.GET.get('api_key')
    return provided_key == configured_key


def verify_pos_ip(request):
    """Verify request comes from whitelisted POS IP addresses"""
    allowed_ips = getattr(settings, 'POS_ALLOWED_IPS', [])
    if not allowed_ips:
        return True  # No IP restriction
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR')
    
    return client_ip in allowed_ips


def verify_request_timestamp(request):
    """Verify request timestamp to prevent replay attacks"""
    timestamp_str = request.headers.get('X-Request-Timestamp')
    if not timestamp_str:
        return False, "Missing request timestamp"
    
    try:
        request_time = int(timestamp_str)
        current_time = int(time.time())
        
        # Allow 5-minute window (300 seconds)
        time_diff = abs(current_time - request_time)
        max_window = getattr(settings, 'POS_TIMESTAMP_WINDOW', 300)
        
        if time_diff > max_window:
            return False, f"Request timestamp expired (window: {max_window}s)"
        
        return True, None
    except ValueError:
        return False, "Invalid timestamp format"


def verify_request_signature(request):
    """Verify HMAC signature of the request"""
    secret_key = getattr(settings, 'POS_SECRET_KEY', '')
    if not secret_key:
        return True  # Signature verification disabled
    
    provided_signature = request.headers.get('X-Request-Signature')
    if not provided_signature:
        return False
    
    # Reconstruct expected signature
    timestamp = request.headers.get('X-Request-Timestamp', '')
    body = request.body.decode('utf-8') if request.body else ''
    
    message = f"{timestamp}:{body}"
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(provided_signature, expected_signature)


def rate_limit_pos_request(request, max_requests=60, window_seconds=60):
    """Simple rate limiting for POS API using cache"""
    from django.core.cache import cache
    
    # Get client identifier
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR')
    
    # Create cache key
    cache_key = f"pos_api_rate_limit:{client_ip}"
    
    # Get current count
    current_count = cache.get(cache_key, 0)
    
    if current_count >= max_requests:
        return False, f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds."
    
    # Increment count
    if current_count == 0:
        # First request, set expiry
        cache.set(cache_key, 1, window_seconds)
    else:
        cache.incr(cache_key)
    
    return True, None


def log_pos_transaction(request, success, action, details=None, error=None):
    """Log all POS API transactions for audit trail"""
    try:
        from audits.models import AuditLog
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        client_ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        # Create audit log entry
        AuditLog.objects.create(
            user=None,  # POS requests are system-to-system
            action=f'POS_{action}',
            entity_type='POS_Transaction',
            entity_id=None,
            details={
                'success': success,
                'ip_address': client_ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'endpoint': request.path,
                'method': request.method,
                'request_data': details,
                'error': error,
            },
            ip_address=client_ip,
        )
    except Exception as e:
        # Log silently - don't fail the transaction due to logging issues
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log POS transaction: {e}")


def require_https(request):
    """Check if request is HTTPS (for production)"""
    if getattr(settings, 'POS_REQUIRE_HTTPS', False):
        return request.is_secure()
    return True


@csrf_exempt
def pos_tithe_submission(request):
    """
    POS API Endpoint for submitting tithe payments.
    
    SECURITY FEATURES:
    - API Key authentication (X-POS-API-Key header)
    - IP whitelisting (POS_ALLOWED_IPS setting)
    - Rate limiting (60 requests/minute default)
    - Request timestamp validation (5-minute window)
    - Optional HMAC signature verification
    - HTTPS enforcement in production
    - Comprehensive audit logging
    
    POST /tithe/pos/submit/
    
    Headers:
        - X-POS-API-Key (required if POS_API_KEY configured)
        - X-Request-Timestamp (Unix timestamp, required)
        - X-Request-Signature (HMAC-SHA256, optional)
        - Content-Type: application/json
    
    Body:
        {
            "member_id": 123,           // Required: Member ID
            "amount": 50000.00,         // Required: Tithe amount
            "payment_method": "cash",   // Optional: "cash" or "bank" (default: "cash")
            "auto_print": true          // Optional: Auto-trigger print (default: true)
        }
    
    Response:
        {
            "success": true,
            "message": "Tithe payment recorded successfully",
            "payment_id": 456,
            "receipt": {
                "receipt_number": "TITH-20250115-0001",
                "generated": true,
                "print_data": { ... }
            }
        }
    """
    # Check if POS API is enabled
    if not getattr(settings, 'POS_API_ENABLED', True):
        log_pos_transaction(request, False, 'SUBMISSION', error='POS API is disabled')
        return JsonResponse({
            'success': False,
            'error': 'POS API is disabled'
        }, status=403)
    
    # Verify HTTPS requirement for production
    if not require_https(request):
        log_pos_transaction(request, False, 'SUBMISSION', error='HTTPS required')
        return JsonResponse({
            'success': False,
            'error': 'HTTPS connection required'
        }, status=403)
    
    # Verify IP whitelisting
    if not verify_pos_ip(request):
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        log_pos_transaction(request, False, 'SUBMISSION', error=f'IP not whitelisted: {client_ip}')
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized IP address'
        }, status=403)
    
    # Rate limiting check
    allowed, error_msg = rate_limit_pos_request(request)
    if not allowed:
        log_pos_transaction(request, False, 'SUBMISSION', error=error_msg)
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=429)
    
    # Verify API key if configured
    if not verify_pos_api_key(request):
        log_pos_transaction(request, False, 'SUBMISSION', error='Invalid API key')
        return JsonResponse({
            'success': False,
            'error': 'Invalid or missing API key'
        }, status=401)
    
    # Verify request timestamp (prevent replay attacks)
    timestamp_valid, timestamp_error = verify_request_timestamp(request)
    if not timestamp_valid:
        log_pos_transaction(request, False, 'SUBMISSION', error=timestamp_error)
        return JsonResponse({
            'success': False,
            'error': timestamp_error
        }, status=401)
    
    # Verify HMAC signature if configured
    if not verify_request_signature(request):
        log_pos_transaction(request, False, 'SUBMISSION', error='Invalid signature')
        return JsonResponse({
            'success': False,
            'error': 'Invalid request signature'
        }, status=401)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Only POST method is allowed'
        }, status=405)
    
    try:
        # Parse request body
        data = json.loads(request.body)
        
        # Required fields
        member_id = data.get('member_id')
        amount = data.get('amount')
        
        if not member_id:
            return JsonResponse({
                'success': False,
                'error': 'member_id is required'
            }, status=400)
        
        if not amount:
            return JsonResponse({
                'success': False,
                'error': 'amount is required'
            }, status=400)
        
        # Validate amount
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({
                'success': False,
                'error': 'Invalid amount. Must be a positive number.'
            }, status=400)
        
        # Get member
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Member with ID {member_id} not found'
            }, status=404)
        
        # Get payment method
        payment_method = data.get('payment_method', 'cash')
        if payment_method not in ['cash', 'bank']:
            return JsonResponse({
                'success': False,
                'error': 'payment_method must be "cash" or "bank"'
            }, status=400)
        
        # Create tithe payment
        tithe_payment = TithePayment(
            name=member,
            contact_number=str(member.telephone) if member.telephone else '',
            amount=amount,
            status=payment_method,
            date=timezone.now()
        )
        tithe_payment.save()
        
        # Send SMS notification if enabled
        sms_sent = False
        sms_error = None
        if getattr(settings, 'POS_AUTO_SEND_SMS', False):
            from . import sms_service
            from .signals import get_swahili_month, format_phone_number
            
            phone_number = format_phone_number(str(member.telephone) if member.telephone else '')
            
            if phone_number:
                try:
                    member_name = member.name if hasattr(member, 'name') else "Mpendwa"
                    formatted_amount = "{:,}".format(amount)
                    month_name = get_swahili_month(tithe_payment.date)
                    
                    message = (
                        f"Parokia ya Kristo Mfalme: Tumsifu Yesu Kristu; mpendwa {member_name} "
                        f"zaka ya {month_name} Tsh {formatted_amount} imepokelewa kwa maendeleo ya parokia. Malaki 3:10. Ubarikiwe!"
                    )
                    
                    result = sms_service.send_sms(phone_number, message)
                    
                    if result.get('success'):
                        tithe_payment.sms_sent = True
                        tithe_payment.sms_sent_at = timezone.now()
                        tithe_payment.sms_message_id = result.get('message_id', '')
                        tithe_payment.sms_failure_count = 0
                        tithe_payment.last_sms_error = None
                        tithe_payment.save()
                        sms_sent = True
                    else:
                        tithe_payment.sms_failure_count += 1
                        tithe_payment.last_sms_error = result.get('error', 'Unknown error')
                        tithe_payment.save()
                        sms_error = result.get('error')
                except Exception as e:
                    tithe_payment.sms_failure_count += 1
                    tithe_payment.last_sms_error = str(e)
                    tithe_payment.save()
                    sms_error = str(e)
        
        # Auto-generate receipt
        receipt_data = None
        if getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True):
            receipt, created = TitheReceipt.objects.get_or_create(
                tithe_payment=tithe_payment,
                defaults={
                    'generated_by': 'POS System',
                    'church_name': settings.CHURCH_NAME,
                    'church_address': settings.CHURCH_ADDRESS,
                    'church_phone': settings.CHURCH_PHONE,
                }
            )
            
            receipt_data = {
                'receipt_number': receipt.receipt_number,
                'generated': True,
                'is_new': created,
                'print_data': receipt.get_print_data()
            }
            
            # Auto-mark as printed if configured
            auto_print = data.get('auto_print', getattr(settings, 'TITHE_AUTO_PRINT_RECEIPT', True))
            if auto_print and created:
                receipt.mark_printed()
                receipt_data['printed'] = True
        
        # Prepare response
        response_data = {
            'success': True,
            'message': f'Tithe payment of TZS {amount:,.2f} for {member.name} recorded successfully',
            'payment_id': tithe_payment.id,
            'receipt': receipt_data,
            'sms': {
                'sent': sms_sent,
                'error': sms_error
            }
        }
        
        # Log successful transaction
        log_pos_transaction(
            request, 
            success=True, 
            action='SUBMISSION_SUCCESS',
            details={
                'member_id': member_id,
                'member_name': member.name,
                'amount': str(amount),
                'payment_method': payment_method,
                'payment_id': tithe_payment.id,
                'receipt_number': receipt_data.get('receipt_number') if receipt_data else None
            }
        )
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        log_pos_transaction(request, False, 'SUBMISSION', error='Invalid JSON')
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        log_pos_transaction(request, False, 'SUBMISSION', error=str(e))
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def pos_print_receipt(request, receipt_id):
    """
    POS-optimized print receipt view.
    Returns receipt data in a format optimized for POS thermal printers.
    """
    receipt = get_object_or_404(TitheReceipt, id=receipt_id)
    
    if request.method == "POST":
        try:
            receipt.mark_printed()
            
            return JsonResponse({
                'success': True,
                'message': 'Receipt marked as printed',
                'receipt_number': receipt.receipt_number
            })
        except Exception as e:
            receipt.last_print_error = str(e)
            receipt.save()
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    # Return POS-optimized print data
    print_data = receipt.get_print_data()
    
    # Add POS-specific formatting
    pos_data = {
        **print_data,
        'pos_formatted': {
            'header': f"{print_data['church_name']}\n{print_data['church_address']}\n{print_data['church_phone']}",
            'title': 'TITHE RECEIPT',
            'body': f"""
Receipt No: {print_data['receipt_number']}
Date: {print_data['payment_date']}
Member: {print_data['member_name']}
Phone: {print_data['phone_number']}
Amount: TZS {print_data['amount']}
Method: {print_data['payment_method']}
            """.strip(),
            'footer': 'Thank you for your tithe!'
        }
    }
    
    context = {
        "receipt": receipt,
        "payment": receipt.tithe_payment,
        "print_data": pos_data,
        "is_pos": True
    }
    return render(request, "tithepayment/pos_print_receipt.html", context)


@login_required
def pos_member_lookup(request):
    """
    POS API for quick member lookup by phone or name.
    Used by POS machines to find members quickly.
    
    GET /tithe/pos/member-lookup/?search=query
    """
    search_term = request.GET.get('search', '').strip()
    
    if len(search_term) < 2:
        return JsonResponse({
            'success': False,
            'error': 'Search term must be at least 2 characters'
        }, status=400)
    
    try:
        members = Member.objects.filter(
            Q(name__icontains=search_term) | 
            Q(telephone__icontains=search_term)
        ).order_by('name')[:10]
        
        members_data = []
        for member in members:
            members_data.append({
                'id': member.id,
                'name': member.name,
                'phone': str(member.telephone) if member.telephone else '',
                'location': getattr(member, 'location', ''),
            })
        
        return JsonResponse({
            'success': True,
            'count': len(members_data),
            'members': members_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_pos_settings(request):
    """
    Return POS configuration settings.
    Used by POS machines to sync settings.
    """
    return JsonResponse({
        'success': True,
        'settings': {
            'church_name': settings.CHURCH_NAME,
            'church_address': settings.CHURCH_ADDRESS,
            'church_phone': settings.CHURCH_PHONE,
            'auto_generate_receipt': getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True),
            'auto_print_receipt': getattr(settings, 'TITHE_AUTO_PRINT_RECEIPT', True),
            'currency': 'TZS',
        }
    })


# =============================================================================
# BULK PAYMENT VIEW
# =============================================================================

@login_required
def bulk_payment_create(request):
    """
    Create multiple tithe payments at once using formsets.
    """
    from .forms import BulkTithePaymentFormSet
    
    if request.method == 'POST':
        formset = BulkTithePaymentFormSet(request.POST)
        
        if formset.is_valid():
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    created_count = 0
                    total_amount = 0
                    
                    for form in formset:
                        if form.is_valid() and not form.cleaned_data.get('DELETE'):
                            member = form.cleaned_data['name']
                            amount = form.cleaned_data['amount']
                            payment_method = form.cleaned_data['status']
                            payment_date = form.cleaned_data['date']
                            
                            # Create payment
                            tithe_payment = TithePayment(
                                name=member,
                                contact_number=str(member.telephone) if member.telephone else '',
                                amount=amount,
                                status=payment_method,
                                date=payment_date
                            )
                            tithe_payment.save()
                            
                            # Auto-generate receipt if enabled
                            if getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True):
                                generated_by = request.user.get_full_name() or request.user.username
                                TitheReceipt.objects.get_or_create(
                                    tithe_payment=tithe_payment,
                                    defaults={
                                        'generated_by': generated_by,
                                        'church_name': settings.CHURCH_NAME,
                                        'church_address': settings.CHURCH_ADDRESS,
                                        'church_phone': settings.CHURCH_PHONE,
                                    }
                                )
                            
                            created_count += 1
                            total_amount += float(amount)
                    
                    messages.success(
                        request,
                        f'Successfully created {created_count} tithe payments totaling TZS {total_amount:,.2f}'
                    )
                    return redirect('tithepayment:tithepayment_list')
                    
            except Exception as e:
                messages.error(request, f'Error creating bulk payments: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        formset = BulkTithePaymentFormSet()
    
    context = {
        'formset': formset,
        'title': 'Bulk Create Tithe Payments',
        'finance_active': True,
        'tithepayment_active_create': True,
    }
    
    return render(request, 'tithepayment/bulk_create.html', context)


# =============================================================================
# BULK SMS VIEW
# =============================================================================

@login_required
def bulk_sms_send(request):
    """
    Send bulk SMS notifications to tithe payment recipients.
    """
    from .forms import BulkSMSForm
    from . import sms_service
    from .signals import get_swahili_month, format_phone_number
    import time
    
    if request.method == 'POST':
        form = BulkSMSForm(request.POST)
        
        if form.is_valid():
            recipient_filter = form.cleaned_data['recipient_filter']
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            template_type = form.cleaned_data['template_type']
            custom_message = form.cleaned_data.get('custom_message', '')
            payment_ids = form.cleaned_data.get('payment_ids', '')
            rate_limit_delay = form.cleaned_data.get('rate_limit_delay', 1)
            
            # Build queryset based on filter
            queryset = TithePayment.objects.all()
            
            if recipient_filter == 'all':
                # Last 30 days
                thirty_days_ago = timezone.now() - timedelta(days=30)
                queryset = queryset.filter(date__gte=thirty_days_ago)
            elif recipient_filter == 'selected':
                # Selected payments
                if payment_ids:
                    payment_id_list = [int(pid.strip()) for pid in payment_ids.split(',') if pid.strip().isdigit()]
                    queryset = queryset.filter(id__in=payment_id_list)
                else:
                    messages.error(request, 'No payments selected')
                    return redirect('tithepayment:bulk_sms')
            elif recipient_filter == 'unsent':
                # Payments without SMS
                queryset = queryset.filter(sms_sent=False)
            
            # Apply date filters
            if start_date:
                queryset = queryset.filter(date__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date__date__lte=end_date)
            
            # Get payments
            payments = queryset.select_related('name')
            
            if not payments.exists():
                messages.warning(request, 'No payments found matching the criteria')
                return redirect('tithepayment:bulk_sms')
            
            # Send SMS with rate limiting
            success_count = 0
            failure_count = 0
            results = []
            
            for payment in payments:
                member = payment.name
                phone_number = format_phone_number(str(member.telephone) if member.telephone else '')
                
                if not phone_number:
                    results.append({
                        'member': member.name,
                        'status': 'skipped',
                        'reason': 'Invalid phone number'
                    })
                    failure_count += 1
                    continue
                
                # Build message using signal format
                member_name = member.name if hasattr(member, 'name') else "Mpendwa"
                formatted_amount = "{:,}".format(payment.amount)
                month_name = get_swahili_month(payment.date)
                
                if template_type == 'default':
                    message = (
                        f"Parokia ya Kristo Mfalme: Tumsifu Yesu Kristu; mpendwa {member_name} "
                        f"zaka ya {month_name} Tsh {formatted_amount} imepokelewa kwa maendeleo ya parokia. Malaki 3:10. Ubarikiwe!"
                    )
                elif template_type == 'update':
                    message = (
                        f"Tumsifu Yesu {member_name}, zaka yako ya mwezi wa {month_name} "
                        f"imebadilishwa kuwa Tsh {payment.amount:,.0f}. Malipo yamesasishwa. Ubarikiwe!"
                    )
                else:
                    # Custom template with variable substitution
                    message = custom_message.format(
                        name=member.name,
                        amount=f"{payment.amount:,.2f}",
                        date=payment.date.strftime('%Y-%m-%d'),
                        payment_method=payment.get_status_display(),
                        month=month_name
                    )
                
                # Send SMS
                try:
                    result = sms_service.send_sms(phone_number, message)
                    
                    if result.get('success'):
                        # Update payment record
                        payment.sms_sent = True
                        payment.sms_sent_at = timezone.now()
                        payment.sms_message_id = result.get('message_id', '')
                        payment.sms_failure_count = 0
                        payment.last_sms_error = None
                        payment.save()
                        
                        success_count += 1
                        results.append({
                            'member': member.name,
                            'status': 'sent',
                            'phone': phone_number
                        })
                    else:
                        payment.sms_failure_count += 1
                        payment.last_sms_error = result.get('error', 'Unknown error')
                        payment.save()
                        
                        failure_count += 1
                        results.append({
                            'member': member.name,
                            'status': 'failed',
                            'reason': result.get('error', 'Unknown error')
                        })
                    
                    # Rate limiting delay
                    if rate_limit_delay > 0:
                        time.sleep(rate_limit_delay)
                        
                except Exception as e:
                    failure_count += 1
                    results.append({
                        'member': member.name,
                        'status': 'failed',
                        'reason': str(e)
                    })
            
            # Log results
            messages.success(
                request,
                f'Bulk SMS completed: {success_count} sent, {failure_count} failed'
            )
            
            # Store results in session for display
            request.session['bulk_sms_results'] = results
            
            return redirect('tithepayment:bulk_sms_results')
            
    else:
        form = BulkSMSForm()
    
    context = {
        'form': form,
        'title': 'Send Bulk SMS Notifications',
        'finance_active': True,
        'tithepayment_active_list': True,
    }
    
    return render(request, 'tithepayment/bulk_sms.html', context)


@login_required
def bulk_sms_results(request):
    """
    Display results of bulk SMS operation.
    """
    results = request.session.get('bulk_sms_results', [])
    
    # Calculate statistics
    sent_count = sum(1 for r in results if r['status'] == 'sent')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    
    context = {
        'results': results,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'skipped_count': skipped_count,
        'total_count': len(results),
        'title': 'Bulk SMS Results',
        'finance_active': True,
        'tithepayment_active_list': True,
    }
    
    return render(request, 'tithepayment/bulk_sms_results.html', context)


@login_required
def pos_home(request):
    """
    POS home page with payment type selection cards.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    # Check if PIN is verified in session
    if not request.session.get('pos_pin_verified'):
        return redirect('tithepayment:pos_pin_login')
    
    # Check session timeout (15 minutes)
    pin_verified_time = request.session.get('pos_pin_verified_time')
    if pin_verified_time:
        elapsed = timezone.now().timestamp() - pin_verified_time
        if elapsed > 900:  # 15 minutes
            request.session['pos_pin_verified'] = False
            messages.warning(request, 'POS session expired. Please enter PIN again.')
            return redirect('tithepayment:pos_pin_login')
    
    context = {
        'title': 'POS Terminal',
        'finance_active': True,
    }
    
    return render(request, 'tithepayment/pos_home.html', context)


@login_required
def pos_tithe(request):
    """
    POS tithe payment page with menu, today's payments, individual payment form, and bulk payments.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    view_mode = request.GET.get('view', 'menu')
    
    # Handle POST for individual payment
    if request.method == 'POST' and view_mode == 'individual':
        member_id = request.POST.get('name')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('status', 'cash')
        contact_number = request.POST.get('contact_number')
        send_sms = request.POST.get('send_sms') == 'on'
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            member = Member.objects.get(id=member_id) if member_id else None
            
            # Create Tithe Payment
            tithe_payment = TithePayment.objects.create(
                name=member,
                amount=Decimal(amount),
                date=timezone.now(),
                status=payment_method,
                contact_number=contact_number
            )
            
            # Auto-generate receipt
            generated_by = request.user.get_full_name() or request.user.username
            TitheReceipt.objects.create(
                tithe_payment=tithe_payment,
                generated_by=generated_by,
                church_name=getattr(settings, 'CHURCH_NAME', 'Christ The King Parish'),
                church_address=getattr(settings, 'CHURCH_ADDRESS', ''),
                church_phone=getattr(settings, 'CHURCH_PHONE', '')
            )
            
            # Send SMS if requested
            if send_sms and contact_number:
                send_pos_sms(contact_number, member.name if member else 'Mpendwa', amount, 'tithe')
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Tithe payment of Tsh {amount} recorded successfully!',
                    'payment_id': tithe_payment.id
                })
            
            messages.success(request, f'Tithe payment of Tsh {amount} recorded successfully!')
            return redirect('tithepayment:pos_tithe')
            
        except Member.DoesNotExist:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Member not found. Please select a valid member.'})
            messages.error(request, 'Member not found. Please select a valid member.')
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'Error processing payment: {str(e)}'})
            messages.error(request, f'Error processing payment: {str(e)}')
    
    # Get data based on view mode
    context = {
        'title': 'POS - Tithe',
        'view_mode': view_mode,
        'finance_active': True,
    }
    
    if view_mode == 'today':
        # Get today's payments
        from django.utils import timezone
        today = timezone.now().date()
        today_payments = TithePayment.objects.filter(
            date__date=today
        ).select_related('name').order_by('-date')
        context['today_payments'] = today_payments
    
    return render(request, 'tithepayment/pos_tithe.html', context)


@login_required
def pos_offering(request):
    """
    POS offering payment page.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    if request.method == 'POST':
        offering_type = request.POST.get('offering_type', 'SUNDAY')
        member_id = request.POST.get('member_id')
        donor_name = request.POST.get('donor_name')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'CASH')
        donor_phone = request.POST.get('donor_phone')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        send_sms = request.POST.get('send_sms') == 'on'
        
        try:
            from finance.models import Offering
            
            member = Member.objects.get(id=member_id) if member_id else None
            
            offering = Offering.objects.create(
                user=request.user,
                offering_type=offering_type,
                amount=Decimal(amount),
                payment_method=payment_method,
                donor_name=donor_name if is_anonymous else (member.name if member else None),
                donor_phone=donor_phone,
                member=member if not is_anonymous else None,
                is_anonymous=is_anonymous
            )
            
            # Send SMS if requested
            if send_sms and donor_phone:
                send_pos_sms(donor_phone, donor_name if is_anonymous else (member.name if member else 'Mpendwa'), amount, 'offering')
            
            messages.success(request, f'Offering of Tsh {amount} recorded successfully!')
            return redirect('tithepayment:pos_offering')
            
        except Member.DoesNotExist:
            messages.error(request, 'Member not found. Please select a valid member.')
        except Exception as e:
            messages.error(request, f'Error processing offering: {str(e)}')
    
    context = {
        'title': 'POS - Offering',
        'finance_active': True,
    }
    
    return render(request, 'tithepayment/pos_offering.html', context)


@login_required
def pos_pledge(request):
    """
    POS pledge payment page with active pledges list.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    # Get active pledges (not completed or cancelled)
    from finance.models import EventPledge
    pledges = EventPledge.objects.filter(
        status__in=['PENDING', 'PARTIAL', 'OVERDUE']
    ).select_related('event', 'member').order_by('-created_at')
    
    if request.method == 'POST':
        pledge_id = request.POST.get('pledge_id')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'CASH')
        phone = request.POST.get('phone')
        send_sms = request.POST.get('send_sms') == 'on'
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            from finance.models import PledgePayment
            
            pledge = EventPledge.objects.get(id=pledge_id)
            
            # Create pledge payment
            payment = PledgePayment.objects.create(
                pledge=pledge,
                amount=Decimal(amount),
                payment_method=payment_method,
                payment_date=timezone.now(),
                received_by=request.user
            )
            
            # Send SMS if requested
            if send_sms and phone:
                pledge.send_payment_notification(Decimal(amount))
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Pledge payment of Tsh {amount} recorded successfully!',
                    'payment_id': payment.id
                })
            
            messages.success(request, f'Pledge payment of Tsh {amount} recorded successfully!')
            return redirect('tithepayment:pos_pledge')
            
        except EventPledge.DoesNotExist:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Pledge not found.'})
            messages.error(request, 'Pledge not found.')
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'Error processing pledge payment: {str(e)}'})
            messages.error(request, f'Error processing pledge payment: {str(e)}')
    
    context = {
        'title': 'POS - Pledge',
        'pledges': pledges,
        'finance_active': True,
    }
    
    return render(request, 'tithepayment/pos_pledge.html', context)


def send_pos_sms(phone_number, member_name, amount, payment_type):
    """
    Send SMS confirmation for POS payment.
    """
    try:
        from tithe.sms_api.africastalking import SMS
        from tithe.signals import get_swahili_month
        
        formatted_amount = "{:,}".format(float(amount))
        month_name = get_swahili_month(timezone.now())
        
        if payment_type == 'tithe':
            message = (
                f"Parokia ya Kristo Mfalme: Tumsifu Yesu Kristu; mpendwa {member_name} "
                f"zaka ya {month_name} Tsh {formatted_amount} imepokelewa. Malaki 3:10. Ubarikiwe!"
            )
        elif payment_type == 'offering':
            message = (
                f"Parokia ya Kristo Mfalme: Tumsifu Yesu; mpendwa {member_name} "
                f"mchango wako wa Tsh {formatted_amount} umepokewa. Asante kwa sadaka yako. Ubarikiwe!"
            )
        else:
            message = (
                f"Parokia ya Kristo Mfalme: Mpendwa {member_name}, "
                f"malipo yako ya Tsh {formatted_amount} yamekamilika. Ubarikiwe!"
            )
        
        # Format phone number
        phone = str(phone_number)
        if not phone.startswith('+'):
            phone = '+255' + phone.lstrip('0')
        
        SMS.send_sms(phone, message)
        return True
    except Exception as e:
        print(f"SMS sending failed: {e}")
        return False


@login_required
def pos_pin_login(request):
    """
    PIN authentication for POS access.
    Users must enter their PIN to access the POS terminal.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    if request.method == 'POST':
        pin = request.POST.get('pin')
        
        # TEMPORARY: Allow any 4-digit PIN for testing until pos_pin field is added
        # In production, verify against user.pos_pin
        if pin and len(pin) == 4 and pin.isdigit():
            # PIN verified (temporary - for testing)
            request.session['pos_pin_verified'] = True
            request.session['pos_pin_verified_time'] = timezone.now().timestamp()
            request.session['pos_device_id'] = request.META.get('HTTP_USER_AGENT', '')[:50]
            
            messages.success(request, 'POS access granted.')
            return redirect('tithepayment:pos_home')
        else:
            messages.error(request, 'Invalid PIN. Please enter a 4-digit PIN.')
    
    context = {
        'title': 'POS PIN Login',
        'finance_active': True,
    }
    
    return render(request, 'tithepayment/pos_pin_login.html', context)


@login_required
def pos_logout(request):
    """
    Logout from POS session (clears PIN verification).
    """
    request.session['pos_pin_verified'] = False
    request.session['pos_pin_verified_time'] = None
    
    messages.info(request, 'POS session ended.')
    return redirect('tithepayment:tithepayment_list')


@login_required
def api_recent_payments(request):
    """
    API endpoint to return recent payments for POS interface.
    Returns JSON with last 10 payments.
    """
    recent_payments = TithePayment.objects.select_related('name').order_by('-date')[:10]
    
    data = []
    for payment in recent_payments:
        data.append({
            'id': payment.id,
            'member_name': payment.name.name if payment.name else 'Unknown',
            'amount': float(payment.amount),
            'date': payment.date.strftime('%Y-%m-%d %H:%M'),
            'payment_method': payment.get_status_display(),
        })
    
    return JsonResponse(data, safe=False)


@login_required
def pos_dashboard(request):
    """
    POS dashboard with real-time statistics and overview.
    """
    from datetime import timedelta
    from finance.models import Offering, EventPledge
    
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    # Check if PIN is verified in session
    if not request.session.get('pos_pin_verified'):
        return redirect('tithepayment:pos_pin_login')
    
    # Check session timeout (15 minutes)
    pin_verified_time = request.session.get('pos_pin_verified_time')
    if pin_verified_time:
        elapsed = timezone.now().timestamp() - pin_verified_time
        if elapsed > 900:  # 15 minutes
            request.session['pos_pin_verified'] = False
            messages.warning(request, 'POS session expired. Please enter PIN again.')
            return redirect('tithepayment:pos_pin_login')
    
    # Get today's date
    today = timezone.now().date()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Today's statistics
    today_tithe = TithePayment.objects.filter(date__date=today).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    today_offering = Offering.objects.filter(date=today).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # This week's statistics
    week_ago = today - timedelta(days=7)
    week_tithe = TithePayment.objects.filter(date__date__gte=week_ago).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # This month's statistics
    month_ago = today - timedelta(days=30)
    month_tithe = TithePayment.objects.filter(date__date__gte=month_ago).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Active pledges
    active_pledges = EventPledge.objects.filter(
        status__in=['PENDING', 'PARTIAL']
    ).count()
    
    # Total members
    from member.models import Member
    total_members = Member.objects.filter(active=True).count()
    
    # Recent payments (last 10)
    recent_payments = TithePayment.objects.select_related('name').order_by('-date')[:10]
    
    # Payment method breakdown for today
    payment_methods = TithePayment.objects.filter(date__date=today).values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    context = {
        'title': 'POS Dashboard',
        'finance_active': True,
        'today_tithe_total': today_tithe['total'] or 0,
        'today_tithe_count': today_tithe['count'] or 0,
        'today_offering_total': today_offering['total'] or 0,
        'today_offering_count': today_offering['count'] or 0,
        'week_tithe_total': week_tithe['total'] or 0,
        'week_tithe_count': week_tithe['count'] or 0,
        'month_tithe_total': month_tithe['total'] or 0,
        'month_tithe_count': month_tithe['count'] or 0,
        'active_pledges': active_pledges,
        'total_members': total_members,
        'recent_payments': recent_payments,
        'payment_methods': payment_methods,
        'today': today,
    }
    
    return render(request, 'tithepayment/pos_dashboard.html', context)


@login_required
def pos_reports(request):
    """
    POS reports page with daily, weekly, and monthly summaries.
    """
    from datetime import timedelta, datetime
    from finance.models import Offering, EventPledge
    
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    # Check if PIN is verified in session
    if not request.session.get('pos_pin_verified'):
        return redirect('tithepayment:pos_pin_login')
    
    # Check session timeout (15 minutes)
    pin_verified_time = request.session.get('pos_pin_verified_time')
    if pin_verified_time:
        elapsed = timezone.now().timestamp() - pin_verified_time
        if elapsed > 900:  # 15 minutes
            request.session['pos_pin_verified'] = False
            messages.warning(request, 'POS session expired. Please enter PIN again.')
            return redirect('tithepayment:pos_pin_login')
    
    # Get date range from query params (default to today)
    date_range = request.GET.get('range', 'today')
    
    today = timezone.now().date()
    
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_range == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        # Custom date range
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = today - timedelta(days=7)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = today
    
    # Get tithe payments for the date range
    tithe_payments = TithePayment.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date
    ).select_related('name').order_by('-date')
    
    # Get offerings for the date range
    offerings = Offering.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('-date')
    
    # Calculate totals
    tithe_total = tithe_payments.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    offering_total = offerings.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    grand_total = (tithe_total['total'] or 0) + (offering_total['total'] or 0)
    
    # Payment method breakdown
    payment_breakdown = tithe_payments.values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Daily breakdown
    daily_breakdown = []
    current_date = start_date
    while current_date <= end_date:
        day_tithe = TithePayment.objects.filter(date__date=current_date).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        day_offering = Offering.objects.filter(date=current_date).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        daily_breakdown.append({
            'date': current_date,
            'tithe_total': day_tithe['total'] or 0,
            'tithe_count': day_tithe['count'] or 0,
            'offering_total': day_offering['total'] or 0,
            'offering_count': day_offering['count'] or 0,
            'total': (day_tithe['total'] or 0) + (day_offering['total'] or 0)
        })
        
        current_date += timedelta(days=1)
    
    context = {
        'title': 'POS Reports',
        'finance_active': True,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'tithe_payments': tithe_payments,
        'offerings': offerings,
        'tithe_total': tithe_total['total'] or 0,
        'tithe_count': tithe_total['count'] or 0,
        'offering_total': offering_total['total'] or 0,
        'offering_count': offering_total['count'] or 0,
        'grand_total': grand_total,
        'payment_breakdown': payment_breakdown,
        'daily_breakdown': daily_breakdown,
    }
    
    return render(request, 'tithepayment/pos_reports.html', context)


@login_required
def pos_new_member(request):
    """
    POS new member creation page - simplified version for quick member registration.
    """
    # Check if user has POS access role
    user_roles = getattr(request.user, 'roles', [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    
    allowed_roles = ['admin', 'finance', 'cashier', 'treasurer', 'priest']
    if not any(role in allowed_roles for role in user_roles):
        messages.error(request, 'You do not have permission to access the POS terminal.')
        return redirect('tithepayment:tithepayment_list')
    
    # Check if PIN is verified in session
    if not request.session.get('pos_pin_verified'):
        return redirect('tithepayment:pos_pin_login')
    
    # Check session timeout (15 minutes)
    pin_verified_time = request.session.get('pos_pin_verified_time')
    if pin_verified_time:
        elapsed = timezone.now().timestamp() - pin_verified_time
        if elapsed > 900:  # 15 minutes
            request.session['pos_pin_verified'] = False
            messages.warning(request, 'POS session expired. Please enter PIN again.')
            return redirect('tithepayment:pos_pin_login')
    
    from member.models import Member, Community, Ministry
    from member.forms import MemberForm
    
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Member {member.name} created successfully!')
            return redirect('tithepayment:pos_new_member')
    else:
        form = MemberForm()
    
    context = {
        'title': 'POS - New Member',
        'finance_active': True,
        'form': form,
        'communities': Community.objects.all(),
        'ministries': Ministry.objects.all(),
    }
    
    return render(request, 'tithepayment/pos_new_member.html', context)