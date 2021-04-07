from django.shortcuts import render, get_object_or_404, reverse
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden, FileResponse
from django.contrib.auth.models import User, Group
from django_filters.rest_framework import DjangoFilterBackend

from .models import EnhancedUser, EnhancedGroup, Datasource, Chart
from rest_framework import generics
from .serializers import *
from .permissions import *
from .util import *
from .tests import PlatformAPITestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions
from json import load, loads, dumps

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
    for e_user in EnhancedUser.objects.all():
        e_user.delete()
    for e_group in EnhancedGroup.objects.all():
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

    #FIXME: Upload limits?

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
        queryset = [obj for obj in queryset if owner_permission.has_object_permission(request, self, obj) or shared_permission.has_object_permission(request, self, obj)]

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
    #permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()
    filter_backends = [DjangoFilterBackend]
    #filterset_fields = ['creation_time', 'modification_time', 'chart_type']
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
        if not(owner_permission.has_object_permission(request, self, datasource)
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


class ShareView(generics.RetrieveUpdateDestroyAPIView):
    """ Read, update or delete shares on sharable objects"""
    serializer_class = serializers.Serializer

    #FIXME: Validate inputs for correct types

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
                affected_groups.append(Group.objects.get(pk=pk))
            except ObjectDoesNotExist:
                return Response({'error': {'key': pk, 'reason': 'No such User'}}, status=status.HTTP_400_BAD_REQUEST)
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
        #TODO: Error handling (Source unreachable, pive error)
        supported = get_chart_types_for_datasource(datasource)
        return Response(supported)
