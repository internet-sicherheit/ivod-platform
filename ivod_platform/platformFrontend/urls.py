from django.contrib import admin
from django.urls import path, include
from .views import landingpage
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("landingpage", landingpage),
    # path(r'^login/$', auth_views.login, name='login'),
    # path(r'^logout/$', auth_views.logout, name='logout'),
    # path(r'^admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
]
