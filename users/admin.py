from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html
import hashlib
from .models import UserProfile, User, ChurchMember, ChurchMemberProfile

admin.site.register(UserProfile)

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'firstname', 'lastname', 'preferred_language', 'is_active', 'block_status', 'roles', 'date_joined', 'is_staff', 'is_verified', 'phone')
    search_fields = ('username', 'email', 'firstname', 'lastname')
    list_filter = ('is_active', 'roles', 'is_staff', 'is_verified', 'preferred_language')
    add_fieldsets =(
        (None,{'classes':('wide'),
               'fields':('username','email','firstname','lastname','roles','phone','preferred_language','password1','password2',)}),
    )
    ordering = ('date_joined',)
    actions = ['unblock_users']
    change_form_template = 'admin/users/user/change_form.html'

    def block_status(self, obj):
        """Display if user is currently blocked"""
        lockout_key = f"security:account_lockout:{obj.username.lower()}"
        if cache.get(lockout_key):
            return format_html(
                '<span style="color: red; font-weight: bold;">🔒 BLOCKED</span>'
            )
        return format_html('<span style="color: green;">✓ Active</span>')
    block_status.short_description = 'Security Status'

    def unblock_users(self, request, queryset):
        """Admin action to unblock selected users"""
        unblocked = 0
        for user in queryset:
            username = user.username.lower()
            lockout_key = f"security:account_lockout:{username}"
            failures_key = f"security:account_failures:{username}"

            if cache.get(lockout_key):
                cache.delete(lockout_key)
                cache.delete(failures_key)
                unblocked += 1

        self.message_user(request, f'{unblocked} user(s) unblocked successfully.')
    unblock_users.short_description = "🔓 Unblock selected users"

    def get_urls(self):
        """Add custom unblock URL"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/unblock/',
                self.admin_site.admin_view(self.unblock_single),
                name='users_user_unblock'
            ),
        ]
        return custom_urls + urls

    def unblock_single(self, request, user_id):
        """Handle single user unblock from change form"""
        from django.http import HttpResponseRedirect
        from django.contrib import messages

        user = self.get_object(request, user_id)
        if user:
            username = user.username.lower()
            cache.delete(f"security:account_lockout:{username}")
            cache.delete(f"security:account_failures:{username}")
            messages.success(request, f'User "{user.username}" has been unblocked.')

        return HttpResponseRedirect(
            request.META.get('HTTP_REFERER', '/admin/users/user/')
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add block status to change form context"""
        extra_context = extra_context or {}
        user = self.get_object(request, object_id)
        if user:
            lockout_key = f"security:account_lockout:{user.username.lower()}"
            is_blocked = cache.get(lockout_key) is not None
            extra_context['block_status'] = 'blocked' if is_blocked else 'active'
        return super().change_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request):
        # Only allow superusers to add users
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Only superusers can change users
        if obj:
            return request.user.is_superuser
        return True

admin.site.register(User, UserAdmin)


class ChurchMemberProfileInline(admin.StackedInline):
    model = ChurchMemberProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class ChurchMemberInline(admin.StackedInline):
    """Inline for managing ChurchMember from User admin"""
    model = ChurchMember
    can_delete = True
    verbose_name_plural = 'Portal Profile'


@admin.register(ChurchMember)
class ChurchMemberAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone', 'member_code', 'link_status', 'is_portal_active', 'created_at')
    list_filter = ('link_status', 'is_portal_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone', 'member_code')
    actions = ['activate_portal', 'link_to_member']
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',),
            'description': 'This portal profile is linked to a User account'
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Member Linking', {
            'fields': ('member_code', 'member', 'link_status'),
            'description': 'Link this portal account to a church member record'
        }),
        ('Portal Status', {
            'fields': ('is_portal_active', 'created_at', 'updated_at')
        }),
        ('Verification', {
            'fields': ('verification_code', 'verification_sent_at', 'verification_method', 'code_attempts'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'verification_sent_at')
    
    def username(self, obj):
        return obj.user.username
    username.short_description = 'Username'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    
    def activate_portal(self, request, queryset):
        """Bulk activate portal access"""
        for church_member in queryset:
            church_member.is_portal_active = True
            church_member.user.is_active = True
            church_member.save()
            church_member.user.save()
        self.message_user(request, f'{queryset.count()} portal account(s) activated.')
    activate_portal.short_description = "Activate portal access"
    
    def link_to_member(self, request, queryset):
        """Link unlinked portal accounts to member records by phone number"""
        from member.models import Member
        linked_count = 0
        
        for church_member in queryset.filter(link_status='unlinked'):
            # Try to find matching member by phone
            try:
                member = Member.objects.get(
                    telephone=church_member.phone,
                    active=True
                )
                church_member.member = member
                church_member.member_code = member.code
                church_member.link_status = 'linked'
                church_member.save()
                linked_count += 1
            except Member.DoesNotExist:
                continue
        
        self.message_user(request, f'{linked_count} portal account(s) linked to member records.')
    link_to_member.short_description = "Auto-link to member records by phone"


@admin.register(ChurchMemberProfile)
class ChurchMemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'emergency_contact_name', 'receive_email_notifications', 'receive_sms_notifications')
    list_filter = ('receive_email_notifications', 'receive_sms_notifications', 'city')
    search_fields = ('user__username', 'user__email', 'emergency_contact_name')
