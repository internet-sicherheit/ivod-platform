from django.contrib import admin
from django.urls import path, include
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from ivod_platform.settings import DEBUG
from .views import debug_reset_database
from .views import helloworld
from .models import Chart
from .views import debug_reset_database, ChartCreateListView, ChartRetrieveUpdateDestroy, DatasourceCreateListView, DatasourceRetrieveDestroy, ChartShareView, DatasourceShareView
from .serializers import *

urlpatterns = [
    path('charts/', ChartCreateListView.as_view(), name='chart-add'),
    path('charts/<pk>/', ChartRetrieveUpdateDestroy.as_view(), name='chart-get'),
    path('charts/<pk>/shared/', ChartShareView.as_view(), name='chart-shared'),
    path('datasources/', DatasourceCreateListView.as_view(), name='datasource-add'),
    path('datasources/<pk>/', DatasourceRetrieveDestroy.as_view(), name='datasource-get'),
    path('datasources/<pk>/shared/', DatasourceShareView.as_view(), name='datasource-shared'),
]
if DEBUG:
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
    urlpatterns.append(path("helloworld", helloworld))
