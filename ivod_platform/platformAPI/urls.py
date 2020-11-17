from django.contrib import admin
from django.urls import path, include
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from ivod_platform.settings import DEBUG
from .views import debug_reset_database
from .views import helloworld
from .models import Chart
from .views import debug_reset_database, ChartRetrieveView
from .serializers import *

urlpatterns = [
path('charts/', ListCreateAPIView.as_view(queryset=Chart.objects.all(), serializer_class=ChartSerializer), name='chart-list'),
    path('charts/<pk>/', ChartRetrieveView.as_view(), name='chart-get'),
    path('users/', ListCreateAPIView.as_view(queryset=EnhancedUser.objects.all(), serializer_class=EnhancedUserSerializer), name='users-list'),
    path('users/<pk>/', RetrieveAPIView.as_view(queryset=EnhancedUser.objects.all(), serializer_class=EnhancedUserSerializer), name='users-get'),
    path('groups/', ListCreateAPIView.as_view(queryset=EnhancedGroup.objects.all(), serializer_class=EnhancedGroupSerializer), name='groups-list'),
    path('groups/<pk>/', RetrieveAPIView.as_view(queryset=EnhancedGroup.objects.all(), serializer_class=EnhancedGroupSerializer), name='groups-get'),
    path('datasource/', ListCreateAPIView.as_view(queryset=Datasource.objects.all(), serializer_class=DatasourceSerializer), name='datasources-list'),
    path('datasource/<pk>/', ListCreateAPIView.as_view(queryset=Datasource.objects.all(), serializer_class=DatasourceSerializer), name='datasources-list'),

]
if DEBUG:
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
    urlpatterns.append(path("helloworld", helloworld))
