from django.contrib import admin
from .models import AuditLog, SecurityAlert, LoginHistory, DataBackup

# Register your models here.

admin.site.register(AuditLog)
admin.site.register(SecurityAlert)
admin.site.register(LoginHistory)
admin.site.register(DataBackup)