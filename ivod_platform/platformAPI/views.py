from django.shortcuts import render, get_object_or_404, reverse, get_list_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden, FileResponse
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
from django.core.exceptions import ObjectDoesNotExist


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

    # FIXME: Upload limits?

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

    # FIXME: Upload limits?

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
    # TODO: Get whitelist from config
    whitelist = ['config.json', 'site.html', 'shape.json']

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

        # FIXME:
        # Only show if not hidden or user has access
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


class ShareGroupRetrieveDestroyView(generics.RetrieveDestroyAPIView):
    serializer_class = ShareGroupSerializer
    queryset = ShareGroup.objects.all()
    permission_classes = [IsGroupPublic | IsUserGroupOwner | IsUserGroupAdmin | IsUserGroupMember]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

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

    def get_affected_users(self, fieldname, request):
        """Get user objects affected in this request"""
        affected_users = []
        for pk in request.data.get(fieldname, []):
            try:
                affected_users.append(User.objects.get(pk=pk))
            except ObjectDoesNotExist:
                return Response({'error': {'key': pk, 'reason': 'No such User'}}, status=status.HTTP_400_BAD_REQUEST)
        return affected_users

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        # Unsupported, return 405
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()

        new_members = self.get_affected_users("group_members", request)
        if type(new_members) == Response:
            # Getting affected users encountered an error, returned a response instead of a list User objects
            return new_members
        new_admins = self.get_affected_users("group_admins", request)
        if type(new_admins) == Response:
            # Getting affected groups encountered an error, returned a response instead of a list Group objects
            return new_admins

        # Add users and groups to object
        obj.group_members.add(*new_members)
        obj.group_admins.add(*new_admins)
        # Return current shares
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        new_members = self.get_affected_users("group_members", request)
        if type(new_members) == Response:
            # Getting affected users encountered an error, returned a response instead of a list User objects
            return new_members
        new_admins = self.get_affected_users("group_admins", request)
        if type(new_admins) == Response:
            # Getting affected groups encountered an error, returned a response instead of a list Group objects
            return new_admins

        # Add users and groups to object
        obj.group_members.remove(*new_members)
        obj.group_admins.remove(*new_admins)
        # Return current shares
        return self.get(request, *args, **kwargs)


class ShareView(generics.RetrieveUpdateDestroyAPIView):
    """ Read, update or delete shares on sharable objects"""
    serializer_class = serializers.Serializer

    def get_affected_users(self, request):
        """Get user objects affected in this request"""
        affected_users = []
        for pk in request.data.get("users", []):
            try:
                affected_users.append(User.objects.get(pk=pk))
            except ObjectDoesNotExist:
                return Response({'error': {'key': pk, 'reason': 'No such User'}}, status=status.HTTP_400_BAD_REQUEST)
        return affected_users

    def get_affected_groups(self, request):
        """Get group objects affected in this request"""

        affected_groups = []
        for pk in request.data.get("groups", []):
            try:
                affected_groups.append(ShareGroup.objects.get(pk=pk))
            except ObjectDoesNotExist:
                return Response({'error': {'key': pk, 'reason': 'No such Group'}}, status=status.HTTP_400_BAD_REQUEST)
        return affected_groups

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

        new_users = self.get_affected_users(request)
        if type(new_users) == Response:
            # Getting affected users encountered an error, returned a response instead of a list User objects
            return new_users
        new_groups = self.get_affected_groups(request)
        if type(new_groups) == Response:
            # Getting affected groups encountered an error, returned a response instead of a list Group objects
            return new_groups

        # Add users and groups to object
        obj.shared_users.add(*new_users)
        obj.shared_groups.add(*new_groups)
        # Return current shares
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        new_users = self.get_affected_users(request)
        if type(new_users) == Response:
            # Getting affected users encountered an error, returned a response instead of a list User objects
            return new_users
        new_groups = self.get_affected_groups(request)
        if type(new_groups) == Response:
            # Getting affected groups encountered an error, returned a response instead of a list Group objects
            return new_groups

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

    def put(self, request, *args, **kwargs):
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


class UserSearchView(generics.CreateAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()

    # serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        # FIXME: Workaround, moving to uuid will break this
        try:
            id_query_input = int(request.data["name"])
        except:
            id_query_input = -1
        search_filter = (Q(id=id_query_input)  # Q(id=request.data["name"]) #direct lookup, should always work
                         | Q(additional_user_data__public_profile=True)  # Otherwise only look for public profiles
                         & (Q(username__contains=request.data[
                    "name"])  # Searching by username should work even if real name is hidden
                            | (
                                    Q(additional_user_data__real_name=True)  # Search by real name only when real name is publicly displayed
                                    & (Q(first_name__contains=request.data["name"]) | Q(
                                    last_name__contains=request.data["name"])))))
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
                #TODO: Check if this
                user = User.objects.get(email=email)
                serialized_id = signing.dumps(user.id.hex)
                target = request.build_absolute_uri(reverse("do_password_reset", kwargs={'reset_id': serialized_id}))

                reset_url = getattr(settings, "PASSWORD_RESET_URL", None)
                if reset_url is None:
                    reset_url = request.build_absolute_uri(reverse("do_password_reset", kwargs={'reset_id': serialized_id}))
                else:
                    #Append token as parameter
                    reset_url += f"?reset_id={serialized_id}"

                context = {
                    "reset_id": serialized_id,
                    "title": "Password Reset",
                    "reset_url" : reset_url
                }

                text_content = render_to_string('platformAPI/mail_reset_text.jinja2', context=context, request=request)
                html_content = render_to_string('platformAPI/mail_reset_html.jinja2', context=context, request=request)
                #Dont send alternative on
                if text_content == "":
                    text_content = None
                if html_content == "":
                    html_content = None
                if text_content is None and html_content is None:
                    #TODO: ValueError is too broad, use appropriate exception type instead
                    raise ValueError("Only empty templates where loaded")
                # Currently a user would need to manually make a post request against the link in the mail
                print(target)
                send_a_mail(email, context["title"], content=text_content, html_content=html_content)
            except User.DoesNotExist:
                pass
            except Exception as e:
                print(type(e))
                print(e)

        if "email" in request.data:
            # Run in thread to avoid runtime oracle
            t = threading.Thread(target=passwordResetProcessing, args=(request.data["email"],), kwargs={})
            t.setDaemon(True)
            t.start()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ResetPassword(generics.ListCreateAPIView):
    serializer_class = serializers.Serializer

    def get(self, request, *args, **kwargs):
        return SimpleTemplateResponse(get_template("platformAPI/default_password_reset_page.jinja2"),
                                      context={"reset_url": "_self", "reset_id": self.kwargs["reset_id"]}, status=200)

    def post(self, request, *args, **kwargs):
        try:
            token = self.kwargs["reset_id"]
            user_id = signing.loads(token, max_age=15) # 15 minute timeout
            if not "password" in request.data:
                raise ValueError("Missing new password")
            if type(request.data["password"]) != str:
                raise ValueError("Password must be a string")
            user = User.objects.get(id=user_id)
            user.set_password(request.data["password"])
            #TODO: Invalidate spent tokens in DB
            return Response(status=status.HTTP_200_OK)
        except signing.SignatureExpired as e:
            #TODO: Inform about timeout
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(type(e))
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='user', rate='1/1s'), name="dispatch")
class PasswordChangeView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            user = request.user
            if not user.check_password(request.data["oldPassword"]):
                return Response("Wrong password", status=status.HTTP_403_FORBIDDEN)
            user.set_password(request.data["newPassword"])
            user.save()
            return Response(status=status.HTTP_200_OK)

        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)




