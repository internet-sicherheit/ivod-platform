from uuid import UUID

from django.db import IntegrityError
from django.shortcuts import render, get_object_or_404, reverse, get_list_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden, FileResponse
from django.template import Engine
from django.template.loader import get_template, render_to_string
from django.template.response import SimpleTemplateResponse
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from django.contrib.auth.models import Group
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.conf import settings

from rest_framework import generics
from .serializers import *
from .permissions import *
from .util import *
from .tests import PlatformAPITestCase
from .models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions
from json import load, loads, dumps
import threading

from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth.password_validation import validate_password


def get_affected_objects(key, clazz, request, error_on_missing=True):
    """Get user objects affected in this request"""
    affected_users = clazz.objects.filter(pk__in=request.data.get(key, []))
    if error_on_missing:
        for pk in request.data.get(key, []):
            user_missing = True
            for user in affected_users:
                if str(pk) == str(user.id):
                    user_missing = False
                    continue
            if user_missing:
                raise ValueError(f"{pk} doesnt refer to any objects")
    return affected_users


# Create your views here.
def helloworld(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Hello World')


def debug_reset_database(request: HttpRequest) -> HttpResponse:
    """DEBUG VIEW. DONT USE IN PRODUCTION! Clears the database and creates some entries for testing purposes.
    The data used is the same as used in the test cases
    """
    # Delete all users and groups
    for user in User.objects.all():
        user.delete()
    for group in Group.objects.all():
        group.delete()

    # Should have been done through cascadation, just to be safe
    # Delete all admins and admin groups
    for e_user in User.objects.all():
        e_user.delete()
    for e_group in ShareGroup.objects.all():
        e_group.delete()

    # Should have been done through cascadation, just to be safe
    # Delete all datasources and charts
    for datasource in Datasource.objects.all():
        datasource.delete()
    for chart in Chart.objects.all():
        chart.delete()

    # Setup database by creating a testcase object and using the setup call
    case = PlatformAPITestCase()
    case.client = case.client_class()
    case.SERVER_NAME = request.get_host().split(":")[0]
    case.SERVER_PORT = request.get_port()
    case.PROTO = 'https' if request.is_secure() else 'http'
    case.setUp()

    return HttpResponse('')


class DatasourceCreateListView(generics.ListCreateAPIView):
    """Add or list existing datasources, for which the caller has access rights"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = DatasourceSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Only show datasources owned or shared with user
        owner_permission = IsDatasourceOwner()
        shared_permission = DatasourceIsSharedWithUser()
        queryset = [obj for obj in queryset if owner_permission.has_object_permission(request, self,
                                                                                      obj) or shared_permission.has_object_permission(
            request, self, obj)]

        serializer = DatasourceSerializer(data=queryset, many=True)
        serializer.is_valid()
        return Response(serializer.data)


class DatasourceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Modify or delete an existing datasource"""
    permission_classes = [permissions.IsAuthenticated & (IsDatasourceOwner | DatasourceIsSharedWithUser)]
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        # Unsupported, return 405
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != Datasource:
            return current_object

        # Check if modifying user is owner
        owner_permission = IsDatasourceOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = DatasourceSerializer(current_object, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != Datasource:
            return current_object

        # Check if modifying user is owner
        owner_permission = IsDatasourceOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChartCreateListView(generics.ListCreateAPIView):
    """Add or list existing charts, for which the caller has access rights"""
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['creation_time', 'modification_time', 'chart_type']
    filterset_fields = {
        'creation_time': ['gte', 'lte'],
        'modification_time': ['gte', 'lte'],
        'chart_type': ['exact'],
    }

    def post(self, request, *args, **kwargs):
        datasource = Datasource.objects.get(id=request.data['datasource'])

        # Only allow creation if used datasource is available to user
        if not permissions.IsAuthenticated().has_permission(request, self):
            return Response("Must be logged in to create charts", status=status.HTTP_403_FORBIDDEN)
        owner_permission = IsDatasourceOwner()
        shared_permission = DatasourceIsSharedWithUser()
        if not (owner_permission.has_object_permission(request, self, datasource)
                or shared_permission.has_object_permission(request, self, datasource)):
            return Response("No such datasource or forbidden", status=status.HTTP_403_FORBIDDEN)

        serializer = ChartSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Only show charts owned or shared with user or that are public
        owner_permission = IsChartOwner()
        shared_permission = ChartIsSharedWithUser()
        public_permission = ChartIsPublic()
        queryset = [obj for obj in queryset
                    if owner_permission.has_object_permission(request, self, obj)
                    or shared_permission.has_object_permission(request, self, obj)
                    or public_permission.has_object_permission(request, self, obj)
                    ]

        serializer = ChartSerializer(data=queryset, many=True, context={'request': request})
        serializer.is_valid()
        return Response(serializer.data)


class ChartRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    """Modify or delete an existing chart"""
    permission_classes = [permissions.IsAuthenticated & (IsChartOwner | ChartIsSharedWithUser)]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        # Unsupported, return 405
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if type(obj) != Chart:
            return obj

        # Check if modifying user is owner
        if not IsChartOwner().has_object_permission(request, self, obj):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ChartSerializer(obj, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != Chart:
            return current_object

        # Check if modifying user is owner
        owner_permission = IsChartOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChartDataView(generics.RetrieveAPIView):
    """Get processed data associated with a chart"""
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]
    serializer_class = serializers.Serializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            with get_chart_base_path().joinpath(str(obj.id)).joinpath('data.json').open('rb') as data_file:
                return HttpResponse(data_file.read())
        except Exception as e:
            print(e, file=sys.stderr)
            return Response("Error retrieving data", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChartConfigView(generics.RetrieveAPIView):
    """Get config associated with a chart"""
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]
    serializer_class = serializers.Serializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            config = get_config_for_chart(obj)
            return Response(config)
        except Exception as e:
            print(e, file=sys.stderr)
            return Response("Error retrieving data", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChartCodeView(generics.RetrieveAPIView):
    """Get js code associated with a chart"""
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]
    serializer_class = serializers.Serializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            config = get_config_for_chart(obj)
            version = config['version']

            # Whitelist check of version, to avoid XSS
            whitelist = (str(path.name) for path in Path(get_code_base_path()).resolve().iterdir() if path.is_dir())
            if version not in whitelist:
                return Response("Version of this chart is not supported", status=status.HTTP_409_CONFLICT)

            # Redirect to the correct endpoint
            with get_chart_base_path().joinpath(str(obj.id)).joinpath('persisted.json').open('r') as file:
                config = load(file)
                name = config['chart_name'].lower() + ".js"
                target = reverse("code-get", kwargs={'version': version, 'name': name})
            return HttpResponseRedirect(redirect_to=target)
        except Exception as e:
            print(e, file=sys.stderr)
            return Response("Error retrieving code", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChartFileView(generics.RetrieveAPIView):
    """Get another file associated with a chart (e.g. shapefile for maps)"""
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]
    serializer_class = serializers.Serializer
    queryset = Chart.objects.all()

    # Add possible new files here
    # 'data.json' omitted on purpose, allows to limit data download separately later on with the chart-data endpoint
    whitelist = getattr(settings, 'CHART_FILE_WHITELIST', [])

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        filepath = get_chart_base_path().joinpath(str(obj.id)).joinpath(self.kwargs["filename"])
        if filepath.name not in self.__class__.whitelist or not filepath.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            with filepath.open('rb') as data_file:
                return HttpResponse(data_file.read())
        except Exception as e:
            print(e, file=sys.stderr)
            return Response("Error retrieving data", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_code(request: HttpRequest, version, name) -> HttpResponse:
    """Get js code file specified by name and version"""
    filepath = Path(get_code_base_path()).resolve().joinpath(version).joinpath(name)
    if filepath.exists():
        return FileResponse(filepath.open("rb"))
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)


def get_common_code(request: HttpRequest, name) -> HttpResponse:
    """Get js code file specified by name and version"""
    filepath = Path(get_code_base_path()).resolve().joinpath(name)
    if filepath.exists():
        return FileResponse(filepath.open("rb"))
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)


class ShareGroupCreateListView(generics.ListCreateAPIView):
    """Add or list existing datasources, for which the caller has access rights"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShareGroupSerializer
    queryset = ShareGroup.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = ShareGroupSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        is_public_permission = IsGroupPublic()
        is_user_group_owner_permission = IsUserGroupOwner()
        is_user_group_member_permission = IsUserGroupMember()
        is_user_group_admin_permission = IsUserGroupAdmin()
        queryset = [obj for obj in queryset if
                    is_public_permission.has_object_permission(request, self, obj)
                    or is_user_group_owner_permission.has_object_permission(request, self, obj)
                    or is_user_group_member_permission.has_object_permission(request, self, obj)
                    or is_user_group_admin_permission.has_object_permission(request, self, obj)]

        serializer = ShareGroupSerializer(data=queryset, many=True)
        serializer.is_valid()
        return Response(serializer.data)


class ShareGroupRetrieveDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShareGroupSerializer
    queryset = ShareGroup.objects.all()
    permission_classes = [IsGroupPublic | IsUserGroupOwner | IsUserGroupAdmin | IsUserGroupMember]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def patch(self, request, *args, **kwargs):
        sharegroup = self.get_object()
        # Need elevated permission to
        if not (
                IsUserGroupOwner().has_object_permission(request, self, sharegroup)
                or IsUserGroupAdmin().has_object_permission(request, self, sharegroup)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(sharegroup, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != ShareGroup:
            return current_object

        # Check if modifying user is owner
        owner_permission = IsUserGroupOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShareGroupRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShareGroupSerializer
    queryset = ShareGroup.objects.all()
    permission_classes = [IsUserGroupOwner | IsUserGroupAdmin]

    # FIXME: Validate inputs for correct types
    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        # Unsupported, return 405
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            new_members = get_affected_objects("group_members", User, request)
            new_admins = get_affected_objects("group_admins", User, request)
        except ValueError as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

        # Add users and groups to object
        obj.group_members.add(*new_members)
        obj.group_admins.add(*new_admins)
        # Return current shares
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            new_members = get_affected_objects("group_members", User, request)
            new_admins = get_affected_objects("group_admins", User, request)
        except ValueError as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

        # Add users and groups to object
        obj.group_members.remove(*new_members)
        obj.group_admins.remove(*new_admins)
        # Return current shares
        return self.get(request, *args, **kwargs)


class ShareView(generics.RetrieveUpdateDestroyAPIView):
    """ Read, update or delete shares on sharable objects"""
    serializer_class = serializers.Serializer

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        # Get current shares
        obj = self.get_object()
        response = {'users': [user.id for user in obj.shared_users.all()],
                    'groups': [group.id for group in obj.shared_groups.all()]}
        return Response(response)

    def put(self, request, *args, **kwargs):
        # Unsupported, return 405
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            new_users = get_affected_objects("users", User, request)
            new_groups = get_affected_objects("groups", ShareGroup, request)
        except ValueError as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

        # Add users and groups to object
        obj.shared_users.add(*new_users)
        obj.shared_groups.add(*new_groups)
        # Return current shares
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            new_users = get_affected_objects("users", User, request)
            new_groups = get_affected_objects("groups", ShareGroup, request)
        except ValueError as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

        # Try to remove users and groups
        obj.shared_users.remove(*new_users)
        obj.shared_groups.remove(*new_groups)
        # Return current shares
        return self.get(request, *args, **kwargs)


class ChartShareView(ShareView):
    """ShareView for Charts"""
    permission_classes = [permissions.IsAuthenticated & IsChartOwner]
    queryset = Chart.objects.all()


class DatasourceShareView(ShareView):
    """ShareView for Datasources"""
    permission_classes = [permissions.IsAuthenticated & IsDatasourceOwner]
    queryset = Datasource.objects.all()


class ChartTypeView(generics.ListAPIView):
    """Get a list of supported chart types for a datasource"""
    permission_classes = [permissions.IsAuthenticated & (IsDatasourceOwner | DatasourceIsSharedWithUser)]
    queryset = Datasource.objects.all()
    serializer_class = serializers.Serializer

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, *args, **kwargs):
        datasource = self.get_object()
        # TODO: Error handling (Source unreachable, pive error)
        supported = get_chart_types_for_datasource(datasource)
        return Response(supported)


class LoggedInUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, many=False, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

  
class UserView(generics.RetrieveAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj


class UserSearchView(generics.RetrieveAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()


    def get(self, request, *args, **kwargs):

        name = request.query_params["name"]
        def build_uuid_filter(id_query_input):
            # Check if input is a uuid. If input is not a uuid the whole lookup will fail with a ValidationError
            try:
                _ = UUID(id_query_input)
                return Q(id=id_query_input)  # Q(id=request.data["name"]) #direct lookup, should always work
            except Exception as e:
                # Empty query filter
                return Q()

        search_filter = (build_uuid_filter(name)  # Q(id=request.data["name"]) #direct lookup, should always work
                         | Q(public_profile=True)  # Otherwise only look for public profiles
                         & (Q(username__contains=name)  # Searching by username should work even if real name is hidden
                            | (
                                    Q(real_name=True)  # Search by real name only when real name is publicly displayed
                                    & (
                                            Q(first_name__contains=name)
                                            | Q(last_name__contains=name)))))
        objects = User.objects.filter(search_filter)
        serializer = UserSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


class MultiUserView(generics.CreateAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()

    # serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        objects = User.objects.filter(pk__in=request.data["users"])
        serializer = UserSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class CreatePasswordResetRequest(generics.CreateAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):

        def passwordResetProcessing(email):
            try:
                # Get user with this email, if they exist. If they dont exist, there is nothing to do
                user = User.objects.get(email=email)
                serialized_id = signing.dumps({'user': user.id.hex, 'token_type': "PASSWORD_RESET"})
                target = request.build_absolute_uri(reverse("do_password_reset", kwargs={'reset_id': serialized_id}))

                # Get the URL that lets users reset their e-mail from the settings
                reset_url = getattr(settings, "PASSWORD_RESET_URL", None)
                if reset_url is None:
                    # if no URL is set in the settings, take default reset endpoint
                    reset_url = target
                else:
                    # Render token into the url
                    reset_url = render_to_string(Engine.get_default().from_string(reset_url),
                                                 context={'token': serialized_id, 'target': target}, request=request)

                # Build a reset mail from templates
                context = {
                    "reset_id": serialized_id,
                    "title": "Password Reset",
                    "reset_url": reset_url
                }
                text_content = render_to_string('platformAPI/mail_reset_text.jinja2', context=context, request=request)
                html_content = render_to_string('platformAPI/mail_reset_html.jinja2', context=context, request=request)
                # Dont send alternative when its an empty string
                if text_content == "":
                    text_content = None
                if html_content == "":
                    html_content = None

                # At least one message type must be specified
                if text_content is None and html_content is None:
                    # TODO: ValueError is too broad, use appropriate exception type instead
                    raise ValueError("Only empty templates where loaded")
                send_a_mail(email, context["title"], content=text_content, html_content=html_content)
            except User.DoesNotExist:
                pass

        if "email" in request.data:
            # Run in thread to avoid runtime oracle
            t = threading.Thread(target=passwordResetProcessing, args=(request.data["email"],), kwargs={})
            t.setDaemon(True)
            t.start()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ResetPasswordView(generics.ListCreateAPIView):
    serializer_class = serializers.Serializer

    def get(self, request, *args, **kwargs):
        # Simple password reset form. Replace the platformAPI/default_password_reset_page.jinja2 template to create your own form or change PASSWORD_RESET_URL to point to your frontend
        return SimpleTemplateResponse(get_template("platformAPI/default_password_reset_page.jinja2"),
                                      context={"reset_url": "_self", "reset_id": self.kwargs["reset_id"]}, status=200)

    def post(self, request, *args, **kwargs):
        try:
            token = self.kwargs["token"]
            # Load data from token and check expiration
            loadedObject = signing.loads(token, max_age=15 * 60)  # 15 minute timeout
            # Check if token type is a password reset token and not another signed by this server
            if "token_type" not in loadedObject or loadedObject["token_type"] != "PASSWORD_RESET":
                # Wrong token
                return Response(status=status.HTTP_400_BAD_REQUEST)
            user_id = loadedObject["user_id"]
            # Verify password is a string
            if not "password" in request.data:
                raise ValueError("Missing new password")
            if type(request.data["password"]) != str:
                raise ValueError("Password must be a string")
            validate_password(request.data["password"])

            # User is most likely not logged in when requesting a password change request, use user specified in token
            user = User.objects.get(id=user_id)
            # Change password in database
            user.set_password(request.data["password"])
            return Response(status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except signing.SignatureExpired as e:
            # Token expired
            return Response("Request expired!", status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ChangeMailView(generics.CreateAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Create a request to change the users e-mail

        user = request.user
        # Verify users password again to make sure the request comes from the user and not someone hijacking the session
        if not user.check_password(request.data["password"]):
            return Response("Wrong password", status=status.HTTP_403_FORBIDDEN)

        # Create a token for user with specified new e-mail
        serialized_id = signing.dumps(
            {'user': user.id.hex, 'token_type': "EMAIL_CHANGE", 'email': request.data["newEmail"]})

        # Build a verification mail from templates
        context = {
            'title': 'Verify your mail address',
            'token': serialized_id,
            'confirmation_url': request.build_absolute_uri(
                reverse("confirm_email", kwargs={'token': serialized_id}))
        }
        text_content = render_to_string('platformAPI/mail_change_text.jinja2', context=context, request=request)
        html_content = render_to_string('platformAPI/mail_change_html.jinja2', context=context, request=request)


        try:
            # Check if the mail is already in use. If yes, fail silently to not leak information
            _ = User.objects.get(email=request.data["newEmail"])
        except User.DoesNotExist:
            # Mail not in use currently
            # Send the mail to the new mail address
            send_a_mail(
                request.data["newEmail"], context['title'], text_content, html_content=html_content)
        return Response(status=status.HTTP_200_OK)

@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ConfirmMailView(generics.RetrieveAPIView):
    serializer_class = serializers.Serializer
    # User doesnt need to be logged in, all required information and authorisation is provided by posessing the token

    def get(self, request, *args, **kwargs):
        try:
            # Load data from token and check expiration
            loadedObject = signing.loads(kwargs["token"], max_age=15 * 60)  # 15 minute timeout
            # Check if token type is an e-mail change token and not another signed by this server
            if "token_type" not in loadedObject or loadedObject["token_type"] != "EMAIL_CHANGE":
                # Wrong token
                return Response(status=status.HTTP_400_BAD_REQUEST)
            # User might not be logged in on the device the mail arrives, use user specified in token
            user = User.objects.get(id=loadedObject["user"])
            # Update databse entries
            user.email = loadedObject["email"]
            user.save()
            #TODO: Redirect to success/failure pages
            return Response("Email confirmed", status=status.HTTP_200_OK)
        except signing.SignatureExpired as e:
            # Token expired
            return Response("Request expired!", status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            # DB-Constrain violated
            return Response("E-Mail already in use", status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='user', rate='1/1s'), name="dispatch")
class PasswordChangeView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            # Verify users password again to make sure the request comes from the user and not someone hijacking the session
            if not user.check_password(request.data["oldPassword"]):
                return Response("Wrong password", status=status.HTTP_403_FORBIDDEN)
            validate_password(request.data["newPassword"])
            # Change password in database
            user.set_password(request.data["newPassword"])
            user.save()
            return Response(status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
