import sys
from pathlib import Path

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings

from rest_framework import generics, permissions, status, serializers
from rest_framework.reverse import reverse
from ..serializers import ChartSerializer
from ..permissions import IsOwner, IsSharedWithUser, IsPublic, IsSemiPublic, IsShared
from ..util import get_chart_base_path, get_config_for_chart, get_code_base_path, get_chart_types_for_datasource
from ..models import Chart, Datasource
from rest_framework.response import Response
from json import load
from .util import ShareView

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
        owner_permission = IsOwner()
        shared_permission = IsSharedWithUser()
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
        owner_permission = IsOwner()
        shared_permission = IsSharedWithUser()
        public_permission = IsPublic()
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
    permission_classes = [permissions.IsAuthenticated & (IsOwner | IsShared & IsSharedWithUser)]
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
        if not IsOwner().has_object_permission(request, self, obj):
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
        owner_permission = IsOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChartDataView(generics.RetrieveAPIView):
    """Get processed data associated with a chart"""
    permission_classes = [IsOwner | IsShared & IsSharedWithUser | IsSemiPublic]
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
    permission_classes = [IsOwner | IsShared & IsSharedWithUser | IsSemiPublic]
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
    permission_classes = [IsOwner | IsShared & IsSharedWithUser | IsSemiPublic]
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
    permission_classes = [IsOwner | IsShared & IsSharedWithUser | IsSemiPublic]
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

class ChartTypeView(generics.ListAPIView):
    """Get a list of supported chart types for a datasource"""
    permission_classes = [permissions.IsAuthenticated & (IsOwner | IsSharedWithUser)]
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

class ChartShareView(ShareView):
    """ShareView for Charts"""
    permission_classes = [permissions.IsAuthenticated & IsOwner]
    queryset = Chart.objects.all()