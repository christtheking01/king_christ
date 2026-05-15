from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import CatechesisMember, Sacrament, SacramentRequest,CatechesisInstructor,SacramentClass,Enrollment,ClassAttendance,SacramentRecord


@admin.register(CatechesisMember)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'member_category', 'date_of_birth', 
                    'has_baptism_certificate', 'registration_date', 'is_deleted']
    list_filter = ['member_category', 'registration_date', 'is_deleted']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by', 'deleted_at', 'deleted_by']
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'email', 'phone', 'address')
        }),
        ('Categorization', {
            'fields': ('member_category', 'user')
        }),
        ('Certificates', {
            'fields': ('birth_certificate', 'baptism_certificate')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'modified_by', 'modified_at'),
            'classes': ('collapse',)
        }),
        ('Deletion Status', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
        self.message_user(request, f"{queryset.count()} members soft-deleted.")
    soft_delete_selected.short_description = "Soft delete selected members"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
        self.message_user(request, f"{queryset.count()} members restored.")
    restore_selected.short_description = "Restore selected members"
    
    def get_queryset(self, request):
        return CatechesisMember.all_objects.all()


@admin.register(Sacrament)
class SacramentAdmin(admin.ModelAdmin):
    list_display = ['name', 'requires_baptism_certificate', 'min_age']
    list_filter = ['requires_baptism_certificate']
    readonly_fields = ['created_at', 'modified_at', 'created_by', 'modified_by']


@admin.register(SacramentRequest)
class SacramentRequestAdmin(admin.ModelAdmin):
    list_display = ['member', 'sacrament', 'status', 'request_date', 
                    'scheduled_date', 'completion_date', 'reviewed_by', 'notification_sent']
    list_filter = ['status', 'sacrament', 'request_date', 'is_deleted']
    search_fields = ['member__first_name', 'member__last_name', 'member__email']
    readonly_fields = ['request_date', 'review_date', 'notification_sent_at', 'sms_sent_at',
                       'created_at', 'modified_at', 'created_by', 'modified_by', 'deleted_at', 'deleted_by']
    fieldsets = (
        ('Request Information', {
            'fields': ('member', 'sacrament', 'notes')
        }),
        ('Status & Scheduling', {
            'fields': ('status', 'request_date', 'scheduled_date', 'completion_date')
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'review_date', 'review_notes')
        }),
        ('Completion Information', {
            'fields': ('completed_by',)
        }),
        ('Notifications', {
            'fields': ('notification_sent', 'notification_sent_at', 'sms_sent', 'sms_sent_at'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'modified_by', 'modified_at'),
            'classes': ('collapse',)
        }),
        ('Deletion Status', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    actions = ['approve_selected', 'complete_selected', 'soft_delete_selected', 'restore_selected']
    
    def approve_selected(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user, review_date=timezone.now())
        self.message_user(request, f"{queryset.count()} requests approved.")
    approve_selected.short_description = "Approve selected requests"
    
    def complete_selected(self, request, queryset):
        queryset.update(status='completed', completed_by=request.user, 
                       completion_date=timezone.now().date())
        self.message_user(request, f"{queryset.count()} requests marked as completed.")
    complete_selected.short_description = "Mark selected as completed"
    
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(request.user)
        self.message_user(request, f"{queryset.count()} requests soft-deleted.")
    soft_delete_selected.short_description = "Soft delete selected requests"
    
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()
        self.message_user(request, f"{queryset.count()} requests restored.")
    restore_selected.short_description = "Restore selected requests"
    
    def get_queryset(self, request):
        return SacramentRequest.all_objects.all()

@admin.register(CatechesisInstructor)
class CatechesisInstructorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'get_user_email', 'status', 'joined_date']
    list_filter = ['status', 'gender']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else '-'
    get_user_email.short_description = 'User Email'
 
@admin.register(SacramentClass)
class SacramentClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'sacrament_type', 'status', 'start_date', 'get_current_enrollment', 'max_capacity']
    list_filter = ['sacrament_type', 'status', 'meeting_day']
    filter_horizontal = ['instructors']
    date_hierarchy = 'start_date'
 
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['catechesis_member', 'sacrament_class', 'status', 'enrolled_date']
    list_filter = ['status', 'sacrament_class__sacrament_type']
    search_fields = ['catechesis_member__first_name', 'catechesis_member__last_name']
    date_hierarchy = 'enrolled_date'
 
@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ['get_member_name', 'sacrament_class', 'class_date', 'status']
    list_filter = ['status', 'sacrament_class__sacrament_type']
    date_hierarchy = 'class_date'
    
    def get_member_name(self, obj):
        member = obj.enrollment.catechesis_member
        return f"{member.first_name} {member.last_name}"
    get_member_name.short_description = 'Member'
 
@admin.register(SacramentRecord)
class SacramentRecordAdmin(admin.ModelAdmin):
    list_display = ['catechesis_member', 'sacrament_type', 'status', 'ceremony_date', 'certificate_issued']
    list_filter = ['sacrament_type', 'status', 'certificate_issued']
    search_fields = ['catechesis_member__first_name', 'catechesis_member__last_name', 'certificate_number']
    date_hierarchy = 'ceremony_date'
    
if not admin.site.is_registered(CatechesisMember):
    admin.site.register(CatechesisMember)