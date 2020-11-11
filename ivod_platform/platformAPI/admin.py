from django.contrib import admin
from .models import Chart, Datasource, EnhancedGroup, EnhancedUser
# Register your models here.

admin.site.register(Chart)
admin.site.register(Datasource)
admin.site.register(EnhancedGroup)
admin.site.register(EnhancedUser)