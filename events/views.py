from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, date, timedelta
import calendar
import json

from .models import (
    EventCategory, EventLocation, Event, EventRegistration,
    EventAttachment, EventReminder, LiturgicalCalendar
)
from member.models import Ministry


# ====== CALENDAR VIEWS ======

def calendar_view(request):
    """Main calendar view - displays full calendar with events"""
    today = timezone.now().date()
    
    # Get filter parameters
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    category_id = request.GET.get('category')
    event_type = request.GET.get('event_type')
    
    # Calculate date range for the month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # Extend range to show surrounding weeks
    calendar_start = first_day - timedelta(days=first_day.weekday())
    calendar_end = last_day + timedelta(days=(6 - last_day.weekday()))
    
    # Query events
    events = Event.objects.filter(
        status__in=['PUBLISHED', 'COMPLETED'],
        start_date__gte=calendar_start,
        start_date__lte=calendar_end
    ).select_related('category', 'location', 'organizer').prefetch_related('ministries')
    
    if category_id and category_id.strip():
        events = events.filter(category_id=category_id)
    if event_type:
        events = events.filter(event_type=event_type)
    
    # Get categories for filter
    categories = EventCategory.objects.filter(is_active=True)
    
    # Get liturgical calendar entries for this month
    liturgical_days = LiturgicalCalendar.objects.filter(
        date__gte=calendar_start,
        date__lte=calendar_end
    )
    liturgical_dict = {day.date: day for day in liturgical_days}
    
    # Build calendar data
    calendar_weeks = []
    current_week = []
    current_date = calendar_start
    
    while current_date <= calendar_end:
        day_events = []
        for event in events:
            if event.start_date <= current_date <= (event.end_date or event.start_date):
                day_events.append(event)
        
        liturgical = liturgical_dict.get(current_date)
        
        current_week.append({
            'date': current_date,
            'events': day_events,
            'liturgical': liturgical,
            'is_today': current_date == today,
            'is_current_month': current_date.month == month
        })
        
        if len(current_week) == 7:
            calendar_weeks.append(current_week)
            current_week = []
        
        current_date += timedelta(days=1)
    
    # Navigation months
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'calendar_weeks': calendar_weeks,
        'month_name': calendar.month_name[month],
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'categories': categories,
        'selected_category': category_id,
        'selected_type': event_type,
        'event_types': Event.EVENT_TYPES,
        'events_active': True,
    }
    return render(request, 'events/calendar.html', context)


@login_required
def calendar_api(request):
    """API endpoint for FullCalendar or other calendar widgets"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    if start:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
    else:
        start_date = timezone.now().date()
    
    if end:
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date()
    else:
        end_date = start_date + timedelta(days=30)
    
    events = Event.objects.filter(
        status='PUBLISHED',
        start_date__gte=start_date,
        start_date__lte=end_date
    ).select_related('category', 'location')
    
    event_list = []
    for event in events:
        # Handle recurring events
        if event.recurrence != 'NONE':
            dates = event.get_recurrence_dates(start_date, end_date)
            for event_date in dates:
                event_list.append({
                    'id': f"{event.id}_{event_date.isoformat()}",
                    'title': event.title,
                    'start': f"{event_date.isoformat()}T{event.start_time or '00:00:00'}",
                    'end': f"{(event.end_date or event_date).isoformat()}T{event.end_time or '23:59:59'}" if event.end_date or event.end_time else None,
                    'allDay': event.all_day,
                    'color': event.category.color if event.category else '#007bff',
                    'url': f'/events/{event.id}/',
                    'extendedProps': {
                        'location': str(event.location) if event.location else None,
                        'type': event.get_event_type_display(),
                    }
                })
        else:
            event_list.append({
                'id': event.id,
                'title': event.title,
                'start': f"{event.start_date.isoformat()}T{event.start_time or '00:00:00'}",
                'end': f"{(event.end_date or event.start_date).isoformat()}T{event.end_time or '23:59:59'}" if event.end_date or event.end_time else None,
                'allDay': event.all_day,
                'color': event.category.color if event.category else '#007bff',
                'url': f'/events/{event.id}/',
                'extendedProps': {
                    'location': str(event.location) if event.location else None,
                    'type': event.get_event_type_display(),
                }
            })
    
    return JsonResponse(event_list, safe=False)


# ====== EVENT VIEWS ======

def event_list(request):
    """List all events with filtering"""
    today = timezone.now().date()
    
    # Filter parameters
    view_type = request.GET.get('view', 'upcoming')  # upcoming, past, all
    category_id = request.GET.get('category')
    event_type = request.GET.get('event_type')
    search = request.GET.get('search')
    
    # Base query
    events = Event.objects.filter(status__in=['PUBLISHED', 'COMPLETED']).select_related('category', 'location')
    
    # Apply filters
    if view_type == 'upcoming':
        events = events.filter(start_date__gte=today)
    elif view_type == 'past':
        events = events.filter(start_date__lt=today)
    elif view_type == 'featured':
        events = events.filter(featured=True)
    
    if category_id and category_id.strip():
        events = events.filter(category_id=category_id)
    if event_type:
        events = events.filter(event_type=event_type)
    if search:
        events = events.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    # Get counts for tabs
    upcoming_count = Event.objects.filter(status='PUBLISHED', start_date__gte=today).count()
    past_count = Event.objects.filter(status__in=['PUBLISHED', 'COMPLETED'], start_date__lt=today).count()
    featured_count = Event.objects.filter(featured=True, status='PUBLISHED').count()
    
    # Get categories for filter
    categories = EventCategory.objects.filter(is_active=True)
    
    context = {
        'events': events.order_by('start_date', 'start_time'),
        'view_type': view_type,
        'upcoming_count': upcoming_count,
        'past_count': past_count,
        'featured_count': featured_count,
        'categories': categories,
        'event_types': Event.EVENT_TYPES,
        'selected_category': category_id,
        'selected_type': event_type,
        'search': search,
        'events_active': True,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    """Event detail view"""
    event = get_object_or_404(
        Event.objects.select_related('category', 'location', 'organizer')
        .prefetch_related('ministries', 'registrations'),
        pk=pk
    )
    
    # Check if user is registered
    user_registered = False
    if request.user.is_authenticated:
        user_registered = EventRegistration.objects.filter(
            event=event,
            user=request.user,
            status__in=['PENDING', 'CONFIRMED']
        ).exists()
    
    # Get related events
    related_events = Event.objects.filter(
        status='PUBLISHED',
        category=event.category,
        start_date__gte=timezone.now().date()
    ).exclude(id=event.id)[:3]
    
    context = {
        'event': event,
        'user_registered': user_registered,
        'related_events': related_events,
        'events_active': True,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def event_create(request):
    """Create new event"""
    if request.method == 'POST':
        # Extract form data
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        category_id = request.POST.get('category')
        
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time') or None
        end_date = request.POST.get('end_date') or None
        end_time = request.POST.get('end_time') or None
        all_day = request.POST.get('all_day') == 'on'
        
        recurrence = request.POST.get('recurrence', 'NONE')
        recurrence_end_date = request.POST.get('recurrence_end_date') or None
        
        location_id = request.POST.get('location')
        location_details = request.POST.get('location_details')
        
        requires_registration = request.POST.get('requires_registration') == 'on'
        max_attendees = request.POST.get('max_attendees') or None
        registration_deadline = request.POST.get('registration_deadline') or None
        registration_open = request.POST.get('registration_open') == 'on'
        
        is_public = request.POST.get('is_public') == 'on'
        featured = request.POST.get('featured') == 'on'
        
        # Get ministries
        ministry_ids = request.POST.getlist('ministries')
        
        # Create event
        event = Event.objects.create(
            title=title,
            description=description,
            event_type=event_type,
            category_id=category_id if category_id else None,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
            all_day=all_day,
            recurrence=recurrence,
            recurrence_end_date=recurrence_end_date,
            location_id=location_id if location_id else None,
            location_details=location_details,
            organizer=request.user,
            requires_registration=requires_registration,
            max_attendees=max_attendees,
            registration_deadline=registration_deadline,
            registration_open=registration_open,
            is_public=is_public,
            featured=featured,
            created_by=request.user,
            status='PUBLISHED'
        )
        
        # Add ministries
        if ministry_ids:
            event.ministries.set(ministry_ids)
        
        # Handle banner image
        if request.FILES.get('banner_image'):
            event.banner_image = request.FILES['banner_image']
            event.save()
        
        messages.success(request, 'Event created successfully!')
        return redirect('event_detail', pk=event.pk)
    
    categories = EventCategory.objects.filter(is_active=True)
    locations = EventLocation.objects.filter(is_active=True)
    ministries = Ministry.objects.all()
    
    context = {
        'categories': categories,
        'locations': locations,
        'ministries': ministries,
        'event_types': Event.EVENT_TYPES,
        'recurrence_choices': Event.RECURRENCE_CHOICES,
        'events_active': True,
    }
    return render(request, 'events/event_form.html', context)


@login_required
def event_edit(request, pk):
    """Edit existing event"""
    event = get_object_or_404(Event, pk=pk)
    
    # Check if user is organizer or staff
    if event.organizer != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('event_detail', pk=event.pk)
    
    if request.method == 'POST':
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.event_type = request.POST.get('event_type')
        event.category_id = request.POST.get('category') or None
        
        event.start_date = request.POST.get('start_date')
        event.start_time = request.POST.get('start_time') or None
        event.end_date = request.POST.get('end_date') or None
        event.end_time = request.POST.get('end_time') or None
        event.all_day = request.POST.get('all_day') == 'on'
        
        event.recurrence = request.POST.get('recurrence', 'NONE')
        event.recurrence_end_date = request.POST.get('recurrence_end_date') or None
        
        event.location_id = request.POST.get('location') or None
        event.location_details = request.POST.get('location_details')
        
        event.requires_registration = request.POST.get('requires_registration') == 'on'
        event.max_attendees = request.POST.get('max_attendees') or None
        event.registration_deadline = request.POST.get('registration_deadline') or None
        event.registration_open = request.POST.get('registration_open') == 'on'
        
        event.is_public = request.POST.get('is_public') == 'on'
        event.featured = request.POST.get('featured') == 'on'
        event.status = request.POST.get('status', 'PUBLISHED')
        
        # Update ministries
        ministry_ids = request.POST.getlist('ministries')
        event.ministries.set(ministry_ids)
        
        # Handle banner image
        if request.FILES.get('banner_image'):
            event.banner_image = request.FILES['banner_image']
        
        event.save()
        messages.success(request, 'Event updated successfully!')
        return redirect('event_detail', pk=event.pk)
    
    categories = EventCategory.objects.filter(is_active=True)
    locations = EventLocation.objects.filter(is_active=True)
    ministries = Ministry.objects.all()
    
    context = {
        'event': event,
        'categories': categories,
        'locations': locations,
        'ministries': ministries,
        'event_types': Event.EVENT_TYPES,
        'recurrence_choices': Event.RECURRENCE_CHOICES,
        'selected_ministries': list(event.ministries.values_list('id', flat=True)),
        'events_active': True,
    }
    return render(request, 'events/event_form.html', context)


@login_required
def event_delete(request, pk):
    """Delete event"""
    event = get_object_or_404(Event, pk=pk)
    
    if event.organizer != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('event_detail', pk=event.pk)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('event_list')
    
    context = {
        'event': event,
        'events_active': True,
    }
    return render(request, 'events/event_delete.html', context)


# ====== REGISTRATION VIEWS ======

def event_register(request, pk):
    """Register for an event"""
    event = get_object_or_404(Event, pk=pk)
    
    if not event.requires_registration:
        messages.error(request, 'This event does not require registration.')
        return redirect('event_detail', pk=event.pk)
    
    if event.registration_closed:
        messages.error(request, 'Registration is closed for this event.')
        return redirect('event_detail', pk=event.pk)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        notes = request.POST.get('notes')
        dietary_requirements = request.POST.get('dietary_requirements')
        emergency_contact = request.POST.get('emergency_contact')
        emergency_phone = request.POST.get('emergency_phone')
        
        # Check if already registered
        if EventRegistration.objects.filter(event=event, email=email).exists():
            messages.error(request, 'You are already registered for this event with this email.')
            return redirect('event_detail', pk=event.pk)
        
        registration = EventRegistration.objects.create(
            event=event,
            user=request.user if request.user.is_authenticated else None,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            notes=notes,
            dietary_requirements=dietary_requirements,
            emergency_contact=emergency_contact,
            emergency_phone=emergency_phone,
            status='CONFIRMED',
            registered_by=request.user if request.user.is_authenticated else None
        )
        
        messages.success(request, 'Registration successful!')
        return redirect('event_detail', pk=event.pk)
    
    context = {
        'event': event,
        'events_active': True,
    }
    return render(request, 'events/event_register.html', context)


@login_required
def registration_cancel(request, pk):
    """Cancel a registration"""
    registration = get_object_or_404(EventRegistration, pk=pk)
    
    # Check permissions
    if registration.user != request.user and registration.registered_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to cancel this registration.')
        return redirect('event_detail', pk=registration.event.pk)
    
    if request.method == 'POST':
        registration.status = 'CANCELLED'
        registration.save()
        messages.success(request, 'Registration cancelled successfully.')
        return redirect('event_detail', pk=registration.event.pk)
    
    context = {
        'registration': registration,
        'events_active': True,
    }
    return render(request, 'events/registration_cancel.html', context)


@login_required
def my_registrations(request):
    """View my event registrations"""
    registrations = EventRegistration.objects.filter(
        Q(user=request.user) | Q(email=request.user.email),
        status__in=['PENDING', 'CONFIRMED']
    ).select_related('event').order_by('event__start_date')
    
    context = {
        'registrations': registrations,
        'events_active': True,
    }
    return render(request, 'events/my_registrations.html', context)


# ====== DASHBOARD VIEWS ======

@login_required
def events_dashboard(request):
    """Events management dashboard"""
    today = timezone.now().date()
    
    # Statistics
    total_events = Event.objects.filter(created_by=request.user).count()
    upcoming_events = Event.objects.filter(
        organizer=request.user,
        start_date__gte=today,
        status__in=['DRAFT', 'PUBLISHED']
    ).count()
    total_registrations = EventRegistration.objects.filter(
        event__organizer=request.user
    ).count()
    
    # Recent events
    recent_events = Event.objects.filter(
        organizer=request.user
    ).select_related('category').order_by('-created_at')[:5]
    
    # Upcoming events for quick view
    upcoming = Event.objects.filter(
        organizer=request.user,
        start_date__gte=today,
        status='PUBLISHED'
    ).order_by('start_date')[:5]
    
    # Events needing attention (draft, cancelled, or past)
    attention_events = Event.objects.filter(
        organizer=request.user,
        status__in=['DRAFT', 'CANCELLED']
    ).order_by('-created_at')[:5]
    
    context = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'total_registrations': total_registrations,
        'recent_events': recent_events,
        'upcoming': upcoming,
        'attention_events': attention_events,
        'events_active': True,
    }
    return render(request, 'events/dashboard.html', context)


# ====== LITURGICAL CALENDAR VIEWS ======

def liturgical_calendar(request):
    """View liturgical calendar"""
    today = timezone.now().date()
    
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    # Calculate date range
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # Extend range to show surrounding weeks
    calendar_start = first_day - timedelta(days=first_day.weekday())
    calendar_end = last_day + timedelta(days=(6 - last_day.weekday()))
    
    # Get liturgical entries
    liturgical_days = LiturgicalCalendar.objects.filter(
        date__gte=calendar_start,
        date__lte=calendar_end
    )
    liturgical_dict = {day.date: day for day in liturgical_days}
    
    # Build calendar
    calendar_weeks = []
    current_week = []
    current_date = calendar_start
    
    while current_date <= calendar_end:
        liturgical = liturgical_dict.get(current_date)
        
        current_week.append({
            'date': current_date,
            'liturgical': liturgical,
            'is_today': current_date == today,
            'is_current_month': current_date.month == month
        })
        
        if len(current_week) == 7:
            calendar_weeks.append(current_week)
            current_week = []
        
        current_date += timedelta(days=1)
    
    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'calendar_weeks': calendar_weeks,
        'month_name': calendar.month_name[month],
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'events_active': True,
    }
    return render(request, 'events/liturgical_calendar.html', context)
