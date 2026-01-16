from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone
from .models import CatechesisMember, Sacrament, SacramentRequest
from .forms import MemberRegistrationForm, SacramentRequestForm, ReviewForm

def is_approver(user):
    return user.is_authenticated and hasattr(user, 'is_approver') and user.is_approver()

def member_register(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, 'Member registered successfully!')
            return redirect('member_detail', pk=member.pk)
    else:
        form = MemberRegistrationForm()
    
    return render(request, 'catechesis/member_register.html', {'form': form, 'catechesis_active':True,
        'catechesis_register_active':True})


def member_list(request):
    query = request.GET.get('q', '')
    members = CatechesisMember.objects.all()
    
    if query:
        members = members.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    return render(request, 'catechesis/member_list.html', {
        'members': members,
        'query': query,
        'catechesis_active': True,
        'catechesis_member_list': True  #
    })

def member_detail(request, pk):
    member = get_object_or_404(CatechesisMember, pk=pk)
    sacrament_requests = member.sacrament_requests.all()
    
    return render(request, 'catechesis/member_detail.html', {
        'member': member,
        'sacrament_requests': sacrament_requests,
        'catechesis_active':True,
        'catechesis_member_detail':True
    })


def sacrament_request_create(request, member_pk):
    member = get_object_or_404(CatechesisMember, pk=member_pk)
    
    # Get sacraments the member hasn't requested yet
    requested_sacrament_ids = member.sacrament_requests.values_list('sacrament_id', flat=True)
    available_sacraments = Sacrament.objects.exclude(id__in=requested_sacrament_ids)
    
    if request.method == 'POST':
        form = SacramentRequestForm(request.POST)
        if form.is_valid():
            sacrament_request = form.save(commit=False)
            sacrament_request.member = member
            
            try:
                sacrament_request.save()
                messages.success(request, 'Sacrament request submitted successfully! Awaiting approval.')
                return redirect('member_detail', pk=member.pk)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = SacramentRequestForm()
    
    # Filter form choices to only show available sacraments
    form.fields['sacrament'].queryset = available_sacraments
    
    return render(request, 'catechesis/sacrament_request.html', {
        'form': form,
        'member': member,
        'available_sacraments': available_sacraments,
        'catechesis_active':True,
        'catechesis_sacrament_request_create':True
    })


@user_passes_test(is_approver)
def pending_requests(request):
    """View for priests/catechists to see pending requests"""
    status_filter = request.GET.get('status', 'pending')
    
    requests = SacramentRequest.objects.filter(status=status_filter)
    
    # If catechist, filter out Marriage and Holy Orders
    if request.user.role == 'catechist':
        requests = requests.exclude(sacrament__name__in=['marriage', 'holy_orders'])
    
    return render(request, 'catechesis/pending_requests.html', {
        'requests': requests,
        'status_filter': status_filter,
        'catechesis_active':True,
        'catechesis_pending_request':True
    })


@user_passes_test(is_approver)
def review_request(request, pk):
    """View for reviewing and approving/rejecting requests"""
    sacrament_request = get_object_or_404(SacramentRequest, pk=pk)
    
    # Check if user can approve this type of sacrament
    if not request.user.can_approve_sacrament(sacrament_request.sacrament.name):
        messages.error(request, 'You do not have permission to approve this sacrament.')
        return redirect('pending_requests')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            action = request.POST.get('action')
            
            sacrament_request.reviewed_by = request.user
            sacrament_request.review_date = timezone.now()
            sacrament_request.review_notes = form.cleaned_data['review_notes']
            
            if action == 'approve':
                sacrament_request.status = 'approved'
                sacrament_request.scheduled_date = form.cleaned_data.get('scheduled_date')
                messages.success(request, 'Request approved successfully!')
            elif action == 'reject':
                sacrament_request.status = 'rejected'
                messages.info(request, 'Request rejected.')
            
            sacrament_request.save()
            return redirect('pending_requests')
    else:
        form = ReviewForm()
    
    return render(request, 'catechesis/review_request.html', {
        'sacrament_request': sacrament_request,'catechesis_active':True, 'catechesis_review_guest':True,
        'form': form, 'review':sacrament_request
    })


@user_passes_test(is_approver)
def complete_request(request, pk):
    """Mark a sacrament as completed"""
    sacrament_request = get_object_or_404(SacramentRequest, pk=pk)
    
    if request.method == 'POST':
        sacrament_request.status = 'completed'
        sacrament_request.completion_date = timezone.now().date()
        sacrament_request.completed_by = request.user
        sacrament_request.save()
        
        messages.success(request, f'{sacrament_request.sacrament} completed for {sacrament_request.member}!')
        return redirect('pending_requests')
    
    return render(request, 'catechesis/confirm_complete.html', {
        'sacrament_request': sacrament_request
    })


def sacrament_list(request):
    sacraments = Sacrament.objects.all()
    return render(request, 'catechesis/sacrament_list.html', {
        'sacraments': sacraments,
        'catechesis_active': True,  
        'catechesis_sacrament_list': True
    })