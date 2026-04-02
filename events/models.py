from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import calendar

User = get_user_model()


class EventCategory(models.Model):
    """Categories for church events (e.g., Mass, Meeting, Celebration, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for calendar display")
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="FontAwesome icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Event Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class EventLocation(models.Model):
    """Locations where events can be held"""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Event(models.Model):
    """Main event model for church activities"""
    
    EVENT_TYPES = [
        ('MASS', 'Holy Mass'),
        ('MEETING', 'Meeting'),
        ('CELEBRATION', 'Celebration'),
        ('RETREAT', 'Retreat'),
        ('WORKSHOP', 'Workshop'),
        ('FUNDRAISER', 'Fundraiser'),
        ('OUTREACH', 'Community Outreach'),
        ('SACRAMENT', 'Sacrament'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    RECURRENCE_CHOICES = [
        ('NONE', 'Does not repeat'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='OTHER')
    category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    
    # Date and Time
    start_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    all_day = models.BooleanField(default=False)
    
    # Recurrence
    recurrence = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, default='NONE')
    recurrence_end_date = models.DateField(blank=True, null=True)
    
    # Location
    location = models.ForeignKey(EventLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    location_details = models.TextField(blank=True, null=True, help_text="Additional location information")
    
    # Organization
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    ministries = models.ManyToManyField('member.Ministry', blank=True, related_name='events')
    
    # Registration
    requires_registration = models.BooleanField(default=False)
    max_attendees = models.PositiveIntegerField(blank=True, null=True, help_text="Maximum number of attendees")
    registration_deadline = models.DateTimeField(blank=True, null=True)
    registration_open = models.BooleanField(default=True)
    
    # Status and visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_public = models.BooleanField(default=True, help_text="Visible to public/non-logged users")
    featured = models.BooleanField(default=False, help_text="Featured events appear prominently")
    
    # Media
    banner_image = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    
    class Meta:
        ordering = ['start_date', 'start_time']
        indexes = [
            models.Index(fields=['start_date', 'status']),
            models.Index(fields=['event_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_date}"
    
    @property
    def is_past(self):
        """Check if event has already occurred"""
        if self.end_date:
            return self.end_date < timezone.now().date()
        return self.start_date < timezone.now().date()
    
    @property
    def is_ongoing(self):
        """Check if event is currently ongoing"""
        today = timezone.now().date()
        if self.start_date and self.end_date:
            return self.start_date <= today <= self.end_date
        return self.start_date == today
    
    @property
    def duration(self):
        """Calculate event duration"""
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days + 1
        return 1
    
    @property
    def attendee_count(self):
        """Get confirmed attendee count"""
        return self.registrations.filter(status='CONFIRMED').count()
    
    @property
    def available_spots(self):
        """Get remaining available spots"""
        if self.max_attendees:
            return self.max_attendees - self.attendee_count
        return None
    
    @property
    def is_full(self):
        """Check if event is at capacity"""
        if self.max_attendees:
            return self.attendee_count >= self.max_attendees
        return False
    
    @property
    def registration_closed(self):
        """Check if registration is closed"""
        if not self.requires_registration:
            return True
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return True
        if self.is_full:
            return True
        return not self.registration_open
    
    def get_recurrence_dates(self, start=None, end=None):
        """Generate dates for recurring events"""
        if self.recurrence == 'NONE':
            return [self.start_date]
        
        dates = []
        current = self.start_date
        end_date = self.recurrence_end_date or (end or (timezone.now().date() + timedelta(days=365)))
        
        if start and current < start:
            # Advance to first occurrence >= start
            while current < start:
                current = self._get_next_date(current)
        
        while current <= end_date:
            dates.append(current)
            current = self._get_next_date(current)
            
            # Safety limit
            if len(dates) > 1000:
                break
        
        return dates
    
    def _get_next_date(self, current):
        """Get next occurrence date based on recurrence type"""
        if self.recurrence == 'DAILY':
            return current + timedelta(days=1)
        elif self.recurrence == 'WEEKLY':
            return current + timedelta(weeks=1)
        elif self.recurrence == 'BIWEEKLY':
            return current + timedelta(weeks=2)
        elif self.recurrence == 'MONTHLY':
            # Handle month boundary
            if current.day >= 28:
                # Move to last day of next month
                next_month = current.month + 1 if current.month < 12 else 1
                next_year = current.year if current.month < 12 else current.year + 1
                last_day = calendar.monthrange(next_year, next_month)[1]
                return current.replace(year=next_year, month=next_month, day=min(current.day, last_day))
            return current.replace(month=current.month + 1 if current.month < 12 else 1,
                                   year=current.year if current.month < 12 else current.year + 1)
        elif self.recurrence == 'YEARLY':
            return current.replace(year=current.year + 1)
        return current


class EventRegistration(models.Model):
    """Registration model for event attendees"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('ATTENDED', 'Attended'),
        ('NO_SHOW', 'No Show'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    
    # Attendee information
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='event_registrations')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    dietary_requirements = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=200, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Registration status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Metadata
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_attendees')
    
    class Meta:
        unique_together = ['event', 'email']  # One registration per email per event
        ordering = ['registered_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event.title}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class EventAttachment(models.Model):
    """Files attached to events (flyers, documents, etc.)"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='events/attachments/')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title


class EventReminder(models.Model):
    """Reminder settings for events"""
    REMINDER_TYPES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('BOTH', 'Both'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPES, default='EMAIL')
    minutes_before = models.PositiveIntegerField(default=1440, help_text="Minutes before event to send reminder (default 24 hours)")
    sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['minutes_before']
    
    def __str__(self):
        return f"{self.event.title} - {self.minutes_before}min before"


class LiturgicalCalendar(models.Model):
    """Liturgical calendar entries (feasts, solemnities, etc.)"""
    LITURGICAL_SEASONS = [
        ('ADVENT', 'Advent'),
        ('CHRISTMAS', 'Christmas'),
        ('LENT', 'Lent'),
        ('TRIDUUM', 'Triduum'),
        ('EASTER', 'Easter'),
        ('ORDINARY', 'Ordinary Time'),
    ]
    
    CELEBRATION_TYPES = [
        ('SOLEMNITY', 'Solemnity'),
        ('FEAST', 'Feast'),
        ('MEMORIAL', 'Memorial'),
        ('OPTIONAL_MEMORIAL', 'Optional Memorial'),
        ('COMMEMORATION', 'Commemoration'),
        ('FERIAL', 'Ferial Day'),
    ]
    
    date = models.DateField(unique=True)
    title = models.CharField(max_length=200)
    season = models.CharField(max_length=20, choices=LITURGICAL_SEASONS)
    celebration_type = models.CharField(max_length=20, choices=CELEBRATION_TYPES, default='FERIAL')
    color = models.CharField(max_length=20, help_text="Liturgical color (e.g., Green, White, Red, Purple)")
    gospel_reference = models.CharField(max_length=100, blank=True, null=True)
    first_reading = models.CharField(max_length=100, blank=True, null=True)
    psalm = models.CharField(max_length=100, blank=True, null=True)
    second_reading = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['date']
        verbose_name = "Liturgical Calendar Entry"
        verbose_name_plural = "Liturgical Calendar"
    
    def __str__(self):
        return f"{self.title} ({self.date})"
