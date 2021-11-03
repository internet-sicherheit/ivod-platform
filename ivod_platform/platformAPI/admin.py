from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .models import Chart, Datasource, ShareGroup, User, Dashboard
# Register your models here.

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'id')
    readonly_fields = ('id',)

class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'id')
    readonly_fields = ('id',)

# admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(Chart)
admin.site.register(Datasource)
admin.site.register(ShareGroup)
admin.site.register(Dashboard)