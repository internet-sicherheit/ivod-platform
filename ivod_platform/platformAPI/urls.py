from django.urls import path
from .views import *
from django.conf import settings

from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token, refresh_jwt_token
from rest_framework_jwt.blacklist.views import BlacklistView

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

    path('dashboards', DashboardCreateListView.as_view(), name='dashboard-add'),
    path('dashboards/<pk>', DashboardRetrieveUpdateDestroyAPIView.as_view(), name='dashboard-get'),
    path('dashboards/<pk>/shared', DashboardShareView.as_view(), name='dashboard-shared'),

    path('groups', ShareGroupCreateListView.as_view(), name='sharegroup-add'),
    path('groups/<pk>', ShareGroupRetrieveDestroyView.as_view(), name='sharegroup-get'),
    path('groups/<pk>/properties', ShareGroupRetrieveUpdateDestroyView.as_view(), name='sharegroup-properties'),

    # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('token/',  obtain_jwt_token, name='token_obtain'),
    path('token/refresh/', refresh_jwt_token, name='token_refresh'),
    path('token/verify/', verify_jwt_token, name='token_verify'),
    path('token/blacklist/', BlacklistView.as_view({"post": "create"}), name='token_blacklist'),

    path('user/me/', LoggedInUserView.as_view(), name='get_current_user'),
    path('user/me/password/', PasswordChangeView.as_view(), name='change_password'),
    path('user/me/email/', ChangeMailView.as_view(), name='change_email'),
    path('user/id/<pk>/', UserView.as_view(), name='get_user'),
    path('user/search/', UserSearchView.as_view(), name='search_user_by_name'),
    path('user/', MultiUserView.as_view(), name='get_users'),
    path('user/register/', CreateUserView.as_view(), name='create_user'),

    path('password/reset/', CreatePasswordResetRequest.as_view(), name='iniate_password_reset'),
    path('password/reset/<token>/', ResetPasswordView.as_view(), name='do_password_reset'),
    path('email/confirm/<token>/', ConfirmMailView.as_view(), name='confirm_email'),
]

if getattr(settings, "DEBUG", False):
    urlpatterns.append(path("debug_reset_database", debug_reset_database))
    urlpatterns.append(path("helloworld", helloworld))
