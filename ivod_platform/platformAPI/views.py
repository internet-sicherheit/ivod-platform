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

class ChartListView(generics.ListAPIView):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        print(obj)
        print("---")
        self.check_object_permissions(self.request, obj)
        return obj

class ChartRetrieveView(generics.RetrieveAPIView):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer
    permission_classes = [IsChartOwner | ChartIsShared & ChartIsSharedWithUser | ChartIsSemiPublic]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

class DatasourceCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DatasourceSerializer

    #FIXME: Upload limits?

    def post(self, request, *args, **kwargs):
        print(request.data)
        serializer = DatasourceSerializer(data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
