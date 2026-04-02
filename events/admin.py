from django.contrib import admin
from .models import (
    EventCategory, EventLocation, Event, EventRegistration,
    EventAttachment, EventReminder, LiturgicalCalendar
)


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(EventLocation)
class EventLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'capacity', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'address']


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    fields = ['first_name', 'last_name', 'email', 'status', 'registered_at']
    readonly_fields = ['registered_at']


class EventAttachmentInline(admin.TabularInline):
    model = EventAttachment
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'event_type', 'start_date', 'start_time',
        'location', 'status', 'requires_registration', 'attendee_count'
    ]
    list_filter = [
        'event_type', 'status', 'requires_registration',
        'is_public', 'featured', 'category', 'created_at'
    ]
    search_fields = ['title', 'description', 'location_details']
    filter_horizontal = ['ministries']
    inlines = [EventRegistrationInline, EventAttachmentInline]
    date_hierarchy = 'start_date'
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'event_type', 'category', 'banner_image')
        }),
        ('Date and Time', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time', 'all_day', 'recurrence', 'recurrence_end_date')
        }),
        ('Location', {
            'fields': ('location', 'location_details')
        }),
        ('Organization', {
            'fields': ('organizer', 'ministries')
        }),
        ('Registration', {
            'fields': ('requires_registration', 'max_attendees', 'registration_deadline', 'registration_open')
        }),
        ('Status', {
            'fields': ('status', 'is_public', 'featured')
        }),
    )


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'event', 'email', 'status', 'registered_at']
    list_filter = ['status', 'registered_at']
    search_fields = ['first_name', 'last_name', 'email', 'event__title']
    date_hierarchy = 'registered_at'


@admin.register(LiturgicalCalendar)
class LiturgicalCalendarAdmin(admin.ModelAdmin):
    list_display = ['date', 'title', 'season', 'celebration_type', 'color']
    list_filter = ['season', 'celebration_type', 'color']
    search_fields = ['title', 'gospel_reference']
    date_hierarchy = 'date'
