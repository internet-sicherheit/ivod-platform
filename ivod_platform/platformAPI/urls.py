from django.contrib import admin
from django.urls import path, include
from ivod_platform.settings import DEBUG
from .views import debug_reset_database

urlpatterns = [
]
if DEBUG:
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
