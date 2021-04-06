from django.contrib import admin
from django.urls import path, include
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from django.conf import settings
from .views import debug_reset_database
from .views import helloworld
from .models import Chart
from .views import *
from .serializers import *

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    path('charts', ChartCreateListView.as_view(), name='chart-add'),
    path('charts/<pk>', ChartRetrieveUpdateDestroy.as_view(), name='chart-get'),
    path('charts/<pk>/shared', ChartShareView.as_view(), name='chart-shared'),
    path('charts/<pk>/data', ChartDataView.as_view(), name='chart-data'),
    path('charts/<pk>/code', ChartCodeView.as_view(), name='chart-code'),
    path('charts/<pk>/config', ChartConfigView.as_view(), name='chart-config'),
    path('charts/<pk>/files/<filename>', ChartFileView.as_view(), name='chart-files'),

    path('code/<name>', get_common_code, name='code-common-get'),
    path('code/<version>/<name>', get_code, name='code-get'),

    path('datasources', DatasourceCreateListView.as_view(), name='datasource-add'),
    path('datasources/<pk>', DatasourceRetrieveUpdateDestroyAPIView.as_view(), name='datasource-get'),
    path('datasources/<pk>/shared', DatasourceShareView.as_view(), name='datasource-shared'),
    path('datasources/<pk>/charttypes', ChartTypeView.as_view(), name='datasource-charttypes'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
if getattr(settings, "DEBUG", False):
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
    urlpatterns.append(path("helloworld", helloworld))
