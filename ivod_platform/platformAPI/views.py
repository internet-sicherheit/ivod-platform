from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.models import User, Group
from .models import EnhancedUser, EnhancedGroup, Datasource, Chart
from rest_framework import generics
from .serializers import *
from .permissions import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions

# Create your views here.
def helloworld(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Hello World')

def debug_reset_database(request: HttpRequest) -> HttpResponse:
    for user in User.objects.all():
        user.delete()
    for group in Group.objects.all():
        group.delete()

    # Should have been done through cascadation, just to be safe
    for e_user in EnhancedUser.objects.all():
        e_user.delete()
    for e_group in EnhancedGroup.objects.all():
        e_group.delete()

    # Should have been done through cascadation, just to be safe
    for datasource in Datasource.objects.all():
        datasource.delete()
    for chart in Chart.objects.all():
        chart.delete()

    admin = User.objects.create_superuser(username="admin", email=None, password="00000000")
    user1 = User.objects.create_user(username="user1", email=None, password="00000000")
    user2 = User.objects.create_user(username="user2", email=None, password="00000000")

    datasource1 = Datasource.objects.create(source="file://some/file1", scope_path="/file1", owner=user1)
    datasource2 = Datasource.objects.create(source="file://some/file2", scope_path="/file2", owner=user2)

    chart1 = Chart.objects.create(
        chart_name="piechart",
        scope_path="/piechart1",
        owner=user1,
        original_datasource=datasource1,
        config="{}",
        downloadable=True,
        visibility=Chart.VISIBILITY_PRIVATE)

    chart2 = Chart.objects.create(
        chart_name="piechart",
        scope_path="/piechart2",
        owner=user1,
        original_datasource=datasource1,
        config="{}",
        downloadable=False,
        visibility=Chart.VISIBILITY_SHARED)

    chart3 = Chart.objects.create(
        chart_name="barchart",
        scope_path="/barchart1",
        owner=user2,
        original_datasource=datasource2,
        config="{}",
        downloadable=True,
        visibility=Chart.VISIBILITY_PRIVATE)

    chart4 = Chart.objects.create(
        chart_name="barchart",
        scope_path="/barchart2",
        owner=user2,
        original_datasource=datasource2,
        config="{}",
        downloadable=True,
        visibility=Chart.VISIBILITY_PRIVATE)

    chart5 = Chart.objects.create(
        chart_name="barchart",
        scope_path="/barchart3",
        owner=user2,
        original_datasource=datasource2,
        config="{}",
        downloadable=True,
        visibility=Chart.VISIBILITY_PUBLIC)

    euser1 = EnhancedUser.objects.create(auth_user=user1)
    euser2 = EnhancedUser.objects.create(auth_user=user2)
    euser2.charts_shared_with_user.add(chart2)
    euser2.save()


    return HttpResponse('')

class ChartRetrieveView(generics.RetrieveAPIView):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

class DatasourceCreateListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    #FIXME: Upload limits?

    def post(self, request, *args, **kwargs):
        owner = request.user
        data = request.data
        data['owner'] = owner.id
        serializer = DatasourceSerializer(data=data, context={'request': request})
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

class DatasourceRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated & (IsDatasourceOwner | DatasourceIsSharedWithUser)]
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def patch(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != Datasource:
            return current_object
        owner_permission = IsDatasourceOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ChartCreateListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()

    # FIXME: Upload limits?

    def post(self, request, *args, **kwargs):
        owner = request.user
        data = request.data
        data['owner'] = owner.id
        data['config'] = str(data['config'])
        serializer = ChartSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # Only show datasources owned or shared with user
        e_user = EnhancedUser.objects.get(auth_user=request.user)
        owner_permission = IsChartOwner()
        shared_permission = ChartIsSharedWithUser()
        queryset = [obj for obj in queryset if owner_permission.has_object_permission(request, self,
                                                                                      obj) or shared_permission.has_object_permission(
            request, self, obj)]
        serializer = ChartSerializer(data=queryset, many=True)
        serializer.is_valid()
        return Response(serializer.data)

class ChartRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated & (IsChartOwner | ChartIsSharedWithUser)]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def patch(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, *args, **kwargs):
        current_object = self.get_object()
        if type(current_object) != Datasource:
            return current_object
        owner_permission = IsChartOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)