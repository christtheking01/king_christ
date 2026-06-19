from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta, date
from calendar import monthrange
from .models import (CatechesisMember, Sacrament, SacramentClass, SacramentRequest, Enrollment, ClassAttendance, CatechesisInstructor)
from .forms import MemberRegistrationForm, SacramentRequestForm, ReviewForm, SacramentClassForm, CatechesisInstructorForm, EnrollmentForm

def is_approver(user):
    return user.is_authenticated and hasattr(user, 'is_approver') and user.is_approver()


@login_required
def member_register(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            member.created_by = request.user if request.user.is_authenticated else None
            member.modified_by = request.user if request.user.is_authenticated else None
            member.save()
            messages.success(request, 'Member registered successfully!')
            return redirect('member_detail', pk=member.pk)
    else:
        form = MemberRegistrationForm()
    
    return render(request, 'catechesis/member_register.html', {
        'form': form, 
        'catechesis_active': True,
        'catechesis_register_active': True
    })


@login_required
def member_list(request):
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    members = CatechesisMember.objects.all()
    
    if query:
        members = members.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    if category_filter:
        members = members.filter(member_category=category_filter)
    
    # Calculate category statistics
    category_stats = members.values('member_category').annotate(count=Count('id'))
    
    return render(request, 'catechesis/member_list.html', {
        'members': members,
        'query': query,
        'category_filter': category_filter,
        'category_stats': category_stats,
        'member_categories': CatechesisMember.MEMBER_CATEGORY_CHOICES,
        'catechesis_active': True,
        'catechesis_member_list': True
    })


@login_required
def member_detail(request, pk):
    member = get_object_or_404(CatechesisMember, pk=pk)
    sacrament_requests = member.sacrament_requests.all()
    
    # Get available sacraments for this member
    from .models import SacramentRequest
    all_sacraments = [choice[0] for choice in SacramentRequest.SACRAMENT_CHOICES]
    requested_sacraments = sacrament_requests.values_list('sacrament', flat=True)
    available_sacraments = [s for s in all_sacraments if s not in requested_sacraments]
    
    return render(request, 'catechesis/member_detail.html', {
        'member': member,
        'sacrament_requests': sacrament_requests,
        'available_sacraments': available_sacraments,
        'catechesis_active': True,
        'catechesis_member_detail': True
    })


def member_delete(request, pk):
    """Soft delete a member"""
    member = get_object_or_404(CatechesisMember, pk=pk)
    
    if request.method == 'POST':
        member.soft_delete(request.user)
        messages.success(request, 'Member deleted successfully!')
        return redirect('member_list')
    
    return render(request, 'catechesis/member_delete.html', {
        'member': member,
        'catechesis_active': True
    })


def sacrament_request_create(request, member_pk):
    member = get_object_or_404(CatechesisMember, pk=member_pk)
    
    # Get sacraments the member hasn't requested yet
    requested_sacraments = member.sacrament_requests.values_list('sacrament', flat=True)
    from .models import SacramentRequest, Enrollment
    all_sacraments = [choice[0] for choice in SacramentRequest.SACRAMENT_CHOICES]
    available_sacraments = [s for s in all_sacraments if s not in requested_sacraments]
    
    # If no available sacraments, show all sacraments with a message
    if not available_sacraments:
        messages.warning(request, 'This member has already requested all available sacraments.')
    
    if request.method == 'POST':
        form = SacramentRequestForm(request.POST)
        if form.is_valid():
            sacrament_request = form.save(commit=False)
            sacrament_request.member = member
            sacrament_request.created_by = request.user if request.user.is_authenticated else None
            sacrament_request.modified_by = request.user if request.user.is_authenticated else None
            
            try:
                sacrament_request.save()
                messages.success(request, 'Sacrament request submitted successfully! Awaiting approval.')
                return redirect('member_detail', pk=member.pk)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = SacramentRequestForm()
    
    return render(request, 'catechesis/sacrament_request.html', {
        'form': form,
        'member': member,
        'available_sacraments': available_sacraments,
        'all_sacraments': all_sacraments,
        'catechesis_active': True,
        'catechesis_sacrament_request_create': True
    })


def sacrament_request_delete(request, pk):
    """Soft delete a sacrament request"""
    sacrament_request = get_object_or_404(SacramentRequest, pk=pk)
    member_pk = sacrament_request.member.pk
    
    if request.method == 'POST':
        sacrament_request.soft_delete(request.user)
        messages.success(request, 'Sacrament request deleted successfully!')
        return redirect('member_detail', pk=member_pk)
    
    return render(request, 'catechesis/sacrament_request_delete.html', {
        'sacrament_request': sacrament_request,
        'catechesis_active': True
    })


@user_passes_test(is_approver)
def pending_requests(request):
    """View for priests/catechists to see pending requests"""
    status_filter = request.GET.get('status', 'pending')
    sacrament_filter = request.GET.get('sacrament', '')
    
    requests = SacramentRequest.objects.filter(status=status_filter)
    
    if sacrament_filter:
        requests = requests.filter(sacrament=sacrament_filter)
    
    # If catechist, filter out Marriage and Holy Orders
    if request.user.roles == 'catechist':
        requests = requests.exclude(sacrament__in=['marriage', 'holy_orders'])
    
    return render(request, 'catechesis/pending_request.html', {
        'requests': requests,
        'status_filter': status_filter,
        'sacrament_filter': sacrament_filter,
        'sacraments': SacramentRequest.SACRAMENT_CHOICES,
        'status_choices': SacramentRequest.STATUS_CHOICES,
        'catechesis_active': True,
        'catechesis_pending_request': True
    })


@user_passes_test(is_approver)
def review_request(request, pk):
    """View for reviewing and approving/rejecting requests"""
    sacrament_request = get_object_or_404(SacramentRequest, pk=pk)
    
    # Check if user can approve this type of sacrament
    if not request.user.can_approve_sacrament(sacrament_request.sacrament):
        messages.error(request, 'You do not have permission to approve this sacrament.')
        return redirect('pending_requests')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            action = request.POST.get('action')
            
            sacrament_request.reviewed_by = request.user
            sacrament_request.review_date = timezone.now()
            sacrament_request.review_notes = form.cleaned_data['review_notes']
            sacrament_request.modified_by = request.user
            
            if action == 'approve':
                sacrament_request.status = 'approved'
                sacrament_request.scheduled_date = form.cleaned_data.get('scheduled_date')
                if sacrament_request.scheduled_date:
                    sacrament_request.status = 'scheduled'
                messages.success(request, 'Request approved successfully!')
            elif action == 'reject':
                sacrament_request.status = 'rejected'
                messages.info(request, 'Request rejected.')
            
            sacrament_request.save()
            return redirect('pending_requests')
    else:
        form = ReviewForm()
    
    return render(request, 'catechesis/review_request.html', {
        'sacrament_request': sacrament_request,
        'catechesis_active': True, 
        'catechesis_review_request': True,
        'form': form
    })


@user_passes_test(is_approver)
def complete_request(request, pk):
    """Mark a sacrament as completed"""
    sacrament_request = get_object_or_404(SacramentRequest, pk=pk)
    
    if request.method == 'POST':
        sacrament_request.status = 'completed'
        sacrament_request.completion_date = timezone.now().date()
        sacrament_request.completed_by = request.user
        sacrament_request.modified_by = request.user
        sacrament_request.save()
        
        messages.success(request, f'{sacrament_request.sacrament} completed for {sacrament_request.member}!')
        return redirect('pending_requests')
    
    return render(request, 'catechesis/confirm_complete.html', {
        'sacrament_request': sacrament_request
    })


@login_required
def sacrament_list(request):
    sacraments = Sacrament.objects.all()
    
    # Get request counts per sacrament
    for sacrament in sacraments:
        sacrament.pending_count = sacrament.sacramentrequest_set.filter(status='pending').count()
        sacrament.completed_count = sacrament.sacramentrequest_set.filter(status='completed').count()
    
    return render(request, 'catechesis/sacrament_list.html', {
        'sacraments': sacraments,
        'catechesis_active': True,  
        'catechesis_sacrament_list': True
    })


# ====== CALENDAR & REPORTING VIEWS ======

@user_passes_test(is_approver)
def sacrament_calendar(request, year=None, month=None):
    today = date.today()
    year = int(year or today.year)
    month = int(month or today.month)

    first_day = date(year, month, 1)
    _, num_days = monthrange(year, month)

    # Single query — fetch all at once
    scheduled_sacraments = SacramentRequest.objects.filter(
        scheduled_date__year=year,
        scheduled_date__month=month,
        status__in=['scheduled', 'completed'],
        is_deleted=False,
    ).select_related('member').order_by('scheduled_date')

    # Group events by day number for fast lookup
    events_by_day = {}
    for req in scheduled_sacraments:
        if req.scheduled_date:
            events_by_day.setdefault(req.scheduled_date.day, []).append(req)

    # Build list of day dicts — no get_item filter needed in template
    calendar_days = []
    for day in range(1, num_days + 1):
        day_date = date(year, month, day)
        calendar_days.append({
            'day': day,
            'date': day_date,
            'events': events_by_day.get(day, []),
            'is_today': day_date == today,
            'is_past': day_date < today,
        })

    # Empty leading cells for calendar grid (Sunday-based)
    empty_days = range((first_day.weekday() + 1) % 7)

    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    context = {
        'today': today,
        'year': year,
        'month': month,
        'month_name': first_day.strftime('%B'),
        'calendar_days': calendar_days,   # replaces calendar_data + days_range + num_days
        'empty_days': empty_days,          # leading blank cells
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'catechesis_active': True,
        'catechesis_calendar': True,
    }
    return render(request, 'catechesis/sacrament_calendar.html', context)


@user_passes_test(is_approver)
def analytics_dashboard(request):
    today = timezone.now().date()

    # Overall stats — consistent is_deleted filter
    base_members = CatechesisMember.objects.filter(is_deleted=False)
    base_requests = SacramentRequest.objects.filter(is_deleted=False)

    total_members = base_members.count()
    total_requests = base_requests.count()
    completed_requests = base_requests.filter(status='completed').count()
    pending_requests = base_requests.filter(status='pending').count()

    # Category breakdown
    category_breakdown = base_members.values(
        'member_category'
    ).annotate(count=Count('id')).order_by('-count')

    # Sacrament stats - since sacrament is a CharField, we need to query differently
    sacrament_stats = []
    for sacrament_choice in SacramentRequest.SACRAMENT_CHOICES:
        sacrament_name = sacrament_choice[0]
        sacrament_display = sacrament_choice[1]
        
        total = base_requests.filter(sacrament=sacrament_name).count()
        completed = base_requests.filter(sacrament=sacrament_name, status='completed').count()
        pending = base_requests.filter(sacrament=sacrament_name, status='pending').count()
        
        sacrament_stats.append({
            'name': sacrament_display,
            'sacrament_type': sacrament_name,
            'total_requests': total,
            'completed': completed,
            'pending': pending
        })

    # Monthly completions — single query
    monthly_qs = base_requests.filter(
        status='completed',
        completion_date__gte=today.replace(day=1) - relativedelta(months=5)
    ).annotate(
        month=TruncMonth('completion_date')
    ).values('month').annotate(count=Count('id')).order_by('month')

    monthly_counts = {
        item['month'].strftime('%b %Y'): item['count'] for item in monthly_qs
    }

    monthly_data = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - relativedelta(months=i)
        label = month_date.strftime('%b %Y')
        monthly_data.append({'month': label, 'count': monthly_counts.get(label, 0)})

    context = {
        'total_members': total_members,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'pending_requests': pending_requests,
        'completion_rate': round((completed_requests / total_requests * 100), 1) if total_requests > 0 else 0,
        'category_breakdown': category_breakdown,
        'sacrament_stats': sacrament_stats,
        'monthly_data': monthly_data,
        'max_count': max(item['count'] for item in monthly_data) if monthly_data else 0,
        'catechesis_active': True,
        'catechesis_analytics': True,
    }
    return render(request, 'catechesis/analytics_dashboard.html', context)


@user_passes_test(is_approver)
def member_analytics(request, pk):
    """Individual member sacrament progress"""
    member = get_object_or_404(CatechesisMember, pk=pk)
    
    # Get all sacrament requests with status breakdown
    requests = member.sacrament_requests.all()
    total = requests.count()
    completed = requests.filter(status='completed').count()
    in_progress = requests.filter(status__in=['approved', 'scheduled']).count()
    pending = requests.filter(status='pending').count()
    
    # Progress percentage
    progress = (completed / 7 * 100) if total > 0 else 0  # 7 sacraments total
    
    context = {
        'member': member,
        'total_requests': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'progress_percentage': progress,
        'sacrament_requests': requests,
        'catechesis_active': True
    }
    return render(request, 'catechesis/member_analytics.html', context)

def sacrament_class_list(request):
    status = request.GET.get('status','')
    sacrament_type = request.GET.get('type','')

    classes = SacramentClass.objects.all()

    if status:
        classes = classes.filter(status=status)
    
    if sacrament_type:
        classes = classes.filter(sacrament_type = sacrament_type)

    context = {
        'classes':classes,
        'status_filter':status,
        'type_filter':sacrament_type,
        'sacrament_types': SacramentClass.SACRAMENT_TYPE_CHOICES,
        'status_choices':SacramentClass.STATUS_CHOICES,
        'catechesis_class_list': True,
    }

    return render(request,'catechesis/class_list.html',context)


@login_required
def create_sacrament_class(request):
    """Create a new sacrament class"""
    if request.method == 'POST':
        form = SacramentClassForm(request.POST)
        if form.is_valid():
            sacrament_class = form.save(commit=False)
            sacrament_class.created_by = request.user
            sacrament_class.save()
            form.save_m2m()  # Save many-to-many relationships
            
            # Auto-enroll members with approved sacrament requests
            # Map SacramentRequest sacrament values (lowercase) to SacramentClass sacrament_type values (uppercase)
            sacrament_type_map = {
                'baptism': 'BAPTISM',
                'eucharist': 'FIRST_COMMUNION',
                'confirmation': 'CONFIRMATION',
                'reconciliation': 'RECONCILIATION',
                'marriage': 'CONFIRMATION',
                'holy_orders': 'CONFIRMATION',
                'anointing_sick': 'FIRST_COMMUNION',
            }
            
            # Get the sacrament type to filter by (convert from class type to request type)
            request_sacrament_type = None
            for request_type, class_type in sacrament_type_map.items():
                if class_type == sacrament_class.sacrament_type:
                    request_sacrament_type = request_type
                    break
            
            if not request_sacrament_type:
                request_sacrament_type = sacrament_class.sacrament_type.lower()
            
            # Get members with approved sacrament requests for this type
            approved_requests = SacramentRequest.objects.filter(
                sacrament=request_sacrament_type,
                status='approved'
            )
            
            auto_enrolled_count = 0
            for request_obj in approved_requests:
                # Check if class has capacity
                if not sacrament_class.has_capacity():
                    break
                
                # Check if member is already enrolled in another class of same type
                existing_enrollment = Enrollment.objects.filter(
                    catechesis_member=request_obj.member,
                    sacrament_class__sacrament_type=sacrament_class.sacrament_type,
                    status='ENROLLED'
                ).exists()
                
                if not existing_enrollment:
                    enrollment, created = Enrollment.objects.get_or_create(
                        catechesis_member=request_obj.member,
                        sacrament_class=sacrament_class,
                        defaults={
                            'status': 'ENROLLED',
                            'request_source': f'Auto-enrolled from approved request: {request_obj.sacrament}'
                        }
                    )
                    if created:
                        auto_enrolled_count += 1
            
            if auto_enrolled_count > 0:
                messages.info(request, f'Auto-enrolled {auto_enrolled_count} member(s) with approved sacrament requests.')
            
            messages.success(request, f'Sacrament class "{sacrament_class.name}" created successfully!')
            return redirect('class_list')
    else:
        form = SacramentClassForm()
    
    context = {
        'form': form,
        'catechesis_active': True,
        'catechesis_class_list': True,
    }
    return render(request, 'catechesis/class_form.html', context)


# CatechesisInstructor Views
@login_required
def instructor_list(request):
    """List all catechesis instructors"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    instructors = CatechesisInstructor.objects.all()
    
    if status_filter:
        instructors = instructors.filter(status=status_filter)
    
    if search_query:
        instructors = instructors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(qualification__icontains=search_query)
        )
    
    context = {
        'instructors': instructors,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': CatechesisInstructor.STATUS_CHOICES,
        'catechesis_active': True,
        'instructor_list_active': True,
    }
    return render(request, 'catechesis/instructor_list.html', context)


@login_required
def instructor_detail(request, pk):
    """View instructor details"""
    instructor = get_object_or_404(CatechesisInstructor, pk=pk)
    
    # Get classes coordinated by this instructor
    coordinated_classes = instructor.coordinated_classes.all()
    
    # Get classes taught by this instructor
    teaching_classes = instructor.teaching_classes.all()
    
    context = {
        'instructor': instructor,
        'coordinated_classes': coordinated_classes,
        'teaching_classes': teaching_classes,
        'catechesis_active': True,
        'instructor_list_active': True,
    }
    return render(request, 'catechesis/instructor_detail.html', context)


@login_required
def instructor_create(request):
    """Create a new catechesis instructor"""
    if request.method == 'POST':
        form = CatechesisInstructorForm(request.POST)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f'Instructor "{instructor.full_name()}" created successfully!')
            return redirect('instructor_list')
    else:
        form = CatechesisInstructorForm()
    
    context = {
        'form': form,
        'catechesis_active': True,
        'instructor_list_active': True,
    }
    return render(request, 'catechesis/instructor_form.html', context)


@login_required
def instructor_update(request, pk):
    """Update an existing catechesis instructor"""
    instructor = get_object_or_404(CatechesisInstructor, pk=pk)
    
    if request.method == 'POST':
        form = CatechesisInstructorForm(request.POST, instance=instructor)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f'Instructor "{instructor.full_name()}" updated successfully!')
            return redirect('instructor_detail', pk=instructor.pk)
    else:
        form = CatechesisInstructorForm(instance=instructor)
    
    context = {
        'form': form,
        'instructor': instructor,
        'catechesis_active': True,
        'instructor_list_active': True,
    }
    return render(request, 'catechesis/instructor_form.html', context)


@login_required
def instructor_delete(request, pk):
    """Delete a catechesis instructor"""
    instructor = get_object_or_404(CatechesisInstructor, pk=pk)
    
    if request.method == 'POST':
        instructor_name = instructor.full_name()
        instructor.delete()
        messages.success(request, f'Instructor "{instructor_name}" deleted successfully!')
        return redirect('instructor_list')
    
    context = {
        'instructor': instructor,
        'catechesis_active': True,
        'instructor_list_active': True,
    }
    return render(request, 'catechesis/instructor_confirm_delete.html', context)

@login_required
def enroll_members(request, pk=None):
    """Enroll members in a class - with class selection option"""
    sacrament_class = None
    
    # If pk is provided, it's the old URL pattern (specific class)
    if pk:
        sacrament_class = get_object_or_404(SacramentClass, pk=pk)
    
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, sacrament_class=sacrament_class)
        if form.is_valid():
            # Get the class from the form (for new flow) or use the provided class (for old flow)
            target_class = form.cleaned_data.get('sacrament_class') or sacrament_class
            
            if not target_class:
                messages.error(request, 'Please select a class to enroll members into.')
                return render(request, 'catechesis/enroll_members.html', {'form': form})
            
            members = form.cleaned_data['members']
            enrolled_count = 0
            
            for member in members:
                # Check if class has capacity
                if not target_class.has_capacity():
                    messages.warning(request, f'Class has reached maximum capacity. Could not enroll all members.')
                    break
                
                # Create enrollment
                enrollment, created = Enrollment.objects.get_or_create(
                    catechesis_member=member,
                    sacrament_class=target_class,
                    defaults={
                        'status': 'ENROLLED',
                        'request_source': 'Manual Enrollment'
                    }
                )
                if created:
                    enrolled_count += 1
            
            if enrolled_count > 0:
                messages.success(request, f'Successfully enrolled {enrolled_count} member(s) in {target_class.name}.')
            else:
                messages.info(request, 'No new members were enrolled (they may already be enrolled).')
            
            return redirect('class_list')
    else:
        form = EnrollmentForm(sacrament_class=sacrament_class)
    
    # Get context data
    context = {
        'form': form,
        'sacrament_class': sacrament_class,
        'catechesis_active': True,
        'catechesis_class_list': True,
    }
    
    # If a specific class is selected, get enrollment info
    if sacrament_class:
        enrolled_members = sacrament_class.enrollments.filter(
            status='ENROLLED'
        ).select_related('catechesis_member')
        
        other_class_enrollments = Enrollment.objects.filter(
            sacrament_class__sacrament_type=sacrament_class.sacrament_type,
            status='ENROLLED'
        ).exclude(
            sacrament_class=sacrament_class
        ).select_related('catechesis_member', 'sacrament_class')
        
        context.update({
            'enrolled_members': enrolled_members,
            'other_class_enrollments': other_class_enrollments,
        })
    
    return render(request, 'catechesis/enroll_members.html', context)


@login_required
def take_attendance(request, pk=None):
    """Take attendance for a class on a specific date"""
    # Get pk from URL parameter or POST data
    if request.method == 'POST' and not pk:
        pk = request.POST.get('class_pk')
    
    sacrament_class = get_object_or_404(SacramentClass, pk=pk)
    
    # Get date from query param or default to today
    class_date_str = request.GET.get('date')
    if class_date_str:
        class_date = date.fromisoformat(class_date_str)
    else:
        class_date = date.today()
    
    # Get all enrolled members
    enrollments = Enrollment.objects.filter(
        sacrament_class=sacrament_class,
        status='ENROLLED'
    ).select_related('catechesis_member')
    
    if request.method == 'POST':
        # Process attendance submission
        for enrollment in enrollments:
            status_key = f'status_{enrollment.id}'
            notes_key = f'notes_{enrollment.id}'
            
            status = request.POST.get(status_key, 'ABSENT')
            notes = request.POST.get(notes_key, '')
            
            # Update or create attendance record
            ClassAttendance.mark_attendance(
                sacrament_class=sacrament_class,
                class_date=class_date,
                enrollment=enrollment,
                status=status,
                recorded_by=request.user,
                notes=notes
            )
        
        messages.success(request, f'Attendance recorded for {class_date}')
        return redirect('view_attendance', pk=pk)
    
    # Get existing attendance for this date
    existing_attendance = {
        att.enrollment_id: att 
        for att in ClassAttendance.objects.filter(
            sacrament_class=sacrament_class,
            class_date=class_date
        )
    }
    
    context = {
        'sacrament_class': sacrament_class,
        'enrollments': enrollments,
        'class_date': class_date,
        'existing_attendance': existing_attendance,
        'status_choices': ClassAttendance.STATUS_CHOICES,
    }
    return render(request, 'catechesis/take_attendance.html', context)
 
 
@login_required
def view_attendance(request, pk):
    """View attendance records for a class"""
    sacrament_class = get_object_or_404(SacramentClass, pk=pk)
    
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance_records = ClassAttendance.objects.filter(
        sacrament_class=sacrament_class
    ).select_related(
        'enrollment__catechesis_member',
        'recorded_by'
    ).order_by('-class_date')
    
    if start_date:
        attendance_records = attendance_records.filter(class_date__gte=start_date)
    if end_date:
        attendance_records = attendance_records.filter(class_date__lte=end_date)
    
    # Group by date for display
    dates = attendance_records.values_list('class_date', flat=True).distinct()
    
    context = {
        'sacrament_class': sacrament_class,
        'attendance_records': attendance_records,
        'dates': dates,
        'catechesis_class_list': True,
    }
    return render(request, 'catechesis/view_attendance.html', context)


@login_required
def export_students(request):
    """Export catechism students to CSV"""
    from .exports import export_students_to_csv
    
    # Get filtered queryset
    students = CatechesisMember.objects.all()
    
    # Apply same filters as list view
    query = request.GET.get('q')
    category_filter = request.GET.get('category')
    
    if query:
        students = students.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    if category_filter:
        students = students.filter(member_category=category_filter)
    
    return export_students_to_csv(students)


@user_passes_test(is_approver)
def export_member_analytics(request):
    """Export individual member course progress to CSV"""
    from .exports import export_member_analytics_to_csv
    
    # Get all members with their progress
    members_data = []
    members = CatechesisMember.objects.filter(is_deleted=False)
    
    for member in members:
        requests = member.sacrament_requests.filter(is_deleted=False)
        total = requests.count()
        completed = requests.filter(status='completed').count()
        in_progress = requests.filter(status__in=['approved', 'scheduled']).count()
        pending = requests.filter(status='pending').count()
        progress = (completed / 7 * 100) if total > 0 else 0  # 7 sacraments total
        
        members_data.append({
            'member_id': member.id,
            'name': f"{member.first_name} {member.last_name}",
            'category': member.get_member_category_display(),
            'total_requests': total,
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'progress_percentage': progress
        })
    
    return export_member_analytics_to_csv(members_data)


@user_passes_test(is_approver)
def export_enrollment_records(request):
    """Export class enrollment records to CSV"""
    from .exports import export_enrollment_records_to_csv
    
    class_id = request.GET.get('class_id')
    enrollments = Enrollment.objects.all()
    
    if class_id:
        enrollments = enrollments.filter(sacrament_class_id=class_id)
    
    return export_enrollment_records_to_csv(enrollments)


@user_passes_test(is_approver)
def export_attendance_records(request):
    """Export attendance records to CSV"""
    from .exports import export_attendance_records_to_csv
    
    class_id = request.GET.get('class_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance_records = ClassAttendance.objects.all()
    
    if class_id:
        attendance_records = attendance_records.filter(sacrament_class_id=class_id)
    
    if start_date:
        attendance_records = attendance_records.filter(class_date__gte=start_date)
    
    if end_date:
        attendance_records = attendance_records.filter(class_date__lte=end_date)
    
    return export_attendance_records_to_csv(attendance_records)