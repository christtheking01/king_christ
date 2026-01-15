from django.contrib import admin

from .models import UserProfile,User

admin.site.register(UserProfile)

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'firstname', 'lastname', 'is_active', 'roles', 'date_joined', 'is_staff', 'is_verified', 'phone')
    search_fields = ('username', 'email', 'firstname', 'lastname')
    list_filter = ('is_active', 'roles', 'is_staff', 'is_verified')
    add_fieldsets =(
        (None,{'classes':('wide'),
               'fields':('username','email','firstname','lastname','roles','phone','password1','password2',)}),
    )
    ordering = ('date_joined',) 

    def has_add_permission(self, request):
        # Only allow superusers to add users
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        # Only superusers can change users
        if obj:
            return request.user.is_superuser
        return True

admin.site.register(User, UserAdmin)
