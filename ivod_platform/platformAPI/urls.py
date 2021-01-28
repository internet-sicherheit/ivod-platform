from django.contrib import admin
from django.urls import path, include
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from ivod_platform.settings import DEBUG
from .views import debug_reset_database
from .views import helloworld
from .models import Chart
from .views import debug_reset_database, get_code, ChartCreateListView, ChartRetrieveUpdateDestroy, DatasourceCreateListView, DatasourceRetrieveUpdateDestroyAPIView, ChartShareView, DatasourceShareView, ChartTypeView, ChartDataView, ChartCodeView
from .serializers import *

urlpatterns = [
    path('charts', ChartCreateListView.as_view(), name='chart-add'),
    path('charts/<pk>', ChartRetrieveUpdateDestroy.as_view(), name='chart-get'),
    path('charts/<pk>/shared', ChartShareView.as_view(), name='chart-shared'),
    path('charts/<pk>/data', ChartDataView.as_view(), name='chart-data'),
    path('charts/<pk>/code', ChartCodeView.as_view(), name='chart-code'),

    path('code/<version>/<name>', get_code, name='code-get'),

    path('datasources', DatasourceCreateListView.as_view(), name='datasource-add'),
    path('datasources/<pk>', DatasourceRetrieveUpdateDestroyAPIView.as_view(), name='datasource-get'),
    path('datasources/<pk>/shared', DatasourceShareView.as_view(), name='datasource-shared'),
    path('datasources/<pk>/charttypes', ChartTypeView.as_view(), name='datasource-charttypes')
]
if DEBUG:
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
    urlpatterns.append(path("helloworld", helloworld))
