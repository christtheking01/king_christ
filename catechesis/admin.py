from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CatechesisMember, Sacrament, SacramentRequest

@admin.register(CatechesisMember)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'date_of_birth', 
                    'has_baptism_certificate', 'registration_date']
    list_filter = ['registration_date']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(Sacrament)
class SacramentAdmin(admin.ModelAdmin):
    list_display = ['name', 'requires_baptism_certificate', 'min_age']
    list_filter = ['requires_baptism_certificate']


@admin.register(SacramentRequest)
class SacramentRequestAdmin(admin.ModelAdmin):
    list_display = ['member', 'sacrament', 'status', 'request_date', 
                    'reviewed_by', 'scheduled_date', 'completion_date']
    list_filter = ['status', 'sacrament', 'request_date']
    search_fields = ['member__first_name', 'member__last_name']
    readonly_fields = ['request_date', 'review_date']
