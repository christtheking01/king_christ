from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import csv
import json

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
        tithe_payment.contact_number = member.telephone
        
        messages.success(
            self.request, 
            f'Tithe payment of Tsh {form.cleaned_data["amount"]} for {member.name} created successfully!'
        )
        return super().form_valid(form)

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
        tithe_payment.contact_number = member.telephone
        
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
    search_term = request.GET.get('search', '').strip()
    
    if len(search_term) < 2:
        return JsonResponse({'members': []})
    
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
                'telephone': str(member.telephone) if member.telephone else '',
            })
        
        return JsonResponse({'members': members_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e), 'members': []})

def get_member_details(request, member_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        member = Member.objects.get(id=member_id)
        return JsonResponse({
            'id': member.id,
            'name': member.name,
            'telephone': member.telephone,
            'full_name': member.name,
        })
    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def quick_add_tithe_payment(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
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
                contact_number=member.telephone,
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
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def export_tithe_payments(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Authentication required')
        return redirect('tithepayment:tithepayment_list')
    
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
        
        return context


# Additional Views for Extended URLs

class YearlyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'tithepayment/yearly_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get yearly data
        from django.db.models.functions import TruncYear
        
        yearly_data = TithePayment.objects.annotate(
            year=TruncYear('date')
        ).values('year').annotate(
            total_amount=Sum('amount'),
            payment_count=Count('id')
        ).order_by('-year')
        
        context['yearly_data'] = yearly_data
        
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
    
    # Check if receipt already exists
    receipt, created = TitheReceipt.objects.get_or_create(
        tithe_payment=payment,
        defaults={
            'generated_by': request.user.get_full_name() or request.user.username,
            'church_name': "Your Church Name",  # Customize these
            'church_address': "Your Church Address",
            'church_phone': "+255 XXX XXX XXX",
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
            # Your printing logic here
            print_data = receipt.get_print_data()
            
            # Simulate printing (replace with actual printer code)
            print(f"Printing receipt: {receipt.receipt_number}")
            
            # Mark as printed
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
    """List all tithe payments with receipt status"""
    template = "tithepayment/receipt_list.html"
    
    # Handle AJAX count requests
    if request.GET.get('ajax_counts') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        unprinted_count = TitheReceipt.objects.filter(is_printed=False).count()
        return JsonResponse({
            'unprinted_count': unprinted_count,
            'total_receipts': TitheReceipt.objects.count()
        })
    
    payments = TithePayment.objects.all().order_by('-date')
    
    # Check if we should show only unprinted receipts
    show_unprinted = request.GET.get('show_unprinted')
    if show_unprinted:
        payments = payments.filter(receipt__is_printed=False)
    
    # Add receipt information to each payment
    for payment in payments:
        payment.has_receipt = hasattr(payment, 'receipt')
        if payment.has_receipt:
            payment.receipt_data = payment.receipt
    
    # Calculate counts
    unprinted_count = TitheReceipt.objects.filter(is_printed=False).count()
    total_receipts = TitheReceipt.objects.count()
    
    context = {
        "payments": payments,
        "receipts_active": "active",
        "unprinted_count": unprinted_count,
        "total_receipts": total_receipts,
        "show_unprinted": bool(show_unprinted),
    }
    return render(request, template, context)

@login_required
def auto_generate_receipt(request, payment_id):
    """Auto-generate receipt after payment save"""
    payment = get_object_or_404(TithePayment, id=payment_id)
    
    # Create receipt automatically
    receipt, created = TitheReceipt.objects.get_or_create(
        tithe_payment=payment,
        defaults={
            'generated_by': 'System',
            'church_name': "Your Church Name",
            'church_address': "Your Church Address", 
            'church_phone': "+255 XXX XXX XXX",
        }
    )
    
    if created:
        return JsonResponse({
            'success': True,
            'receipt_number': receipt.receipt_number,
            'message': 'Receipt generated automatically'
        })
    else:
        return JsonResponse({
            'success': True,
            'receipt_number': receipt.receipt_number,
            'message': 'Receipt already exists'
        })