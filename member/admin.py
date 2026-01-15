from django.contrib import admin
from .models import Member, Ministry,MinistryLeader, CommunityLeader,Community,Committee, TestDb

# Register your models here.

admin.site.register(Member)
admin.site.register(Ministry)
admin.site.register(CommunityLeader)
admin.site.register(Community)
admin.site.register(Committee)
admin.site.register(MinistryLeader)
