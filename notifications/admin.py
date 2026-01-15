from django.contrib import admin
from .models import Notification, NotificationLog
    
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'recipient_type', 
        'status', 
        'send_sms',
        'total_recipients',
        'sms_sent_count', 
        'sms_failed_count',
        'created_at',
        'created_by'
    ]
    list_filter = ['status', 'recipient_type', 'send_sms', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = [
        'total_recipients',
        'sms_sent_count', 
        'sms_failed_count', 
        'sent_at',
        'created_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'message', 'send_sms')
        }),
        ('Recipients', {
            'fields': ('recipient_type', 'member', 'ministry', 'community')
        }),
        ('Status & Tracking', {
            'fields': (
                'status', 
                'total_recipients',
                'sms_sent_count', 
                'sms_failed_count',
                'error_message',
                'created_at',
                'sent_at',
                'created_by'
            )
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'notification', 
        'member', 
        'phone_number', 
        'status',
        'cost',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['member__name', 'phone_number', 'notification__title']
    readonly_fields = ['created_at']