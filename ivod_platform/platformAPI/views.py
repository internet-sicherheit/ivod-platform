from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.models import User, Group
from .models import EnhancedUser, EnhancedGroup, Datasource, Chart
from rest_framework import generics
from .serializers import *
from .permissions import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions

from django.core.exceptions import ObjectDoesNotExist

from traceback import print_exc

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
    # Use user3 for a authenticated, but otherwise no permissions
    user3 = User.objects.create_user(username="user3", email=None, password="00000000")

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

    #euser2 = EnhancedUser.objects.get(auth_user=user2)
    chart2.shared_users.add(user2)
    chart2.save()
    # euser2.charts_shared_with_user.add(chart2)
    # euser2.save()


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

class DatasourceRetrieveDestroy(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated & (IsDatasourceOwner | DatasourceIsSharedWithUser)]
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

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

        datasource = Datasource.objects.get(id=request.data['datasource'])
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
        queryset = self.get_queryset()
        # Only show datasources owned or shared with user
        e_user = EnhancedUser.objects.get(auth_user=request.user)
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
    permission_classes = [permissions.IsAuthenticated & (IsChartOwner | ChartIsSharedWithUser)]
    serializer_class = ChartSerializer
    queryset = Chart.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        if type(obj) != Chart:
            return obj
        #Only owner can modify
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
        owner_permission = IsChartOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ShareView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.Serializer

    #FIXME: Validate inputs for correct types

    def get_affected_users(self, request):
        affected_users = []
        for pk in request.data.get("users", []):
            try:
                affected_users.append(User.objects.get(pk=pk))
            except ObjectDoesNotExist:
                return Response({'error': {'key': pk, 'reason': 'No such User'}}, status=status.HTTP_400_BAD_REQUEST)
        return affected_users

    def get_affected_groups(self, request):
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
        obj = self.get_object()
        response = {'users': [user.id for user in obj.shared_users.all()],
                    'groups': [group.id for group in obj.shared_groups.all()]}
        return Response(response)

    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        new_users = self.get_affected_users(request)
        if type(new_users) == Response:
            # Error response
            return new_users
        new_groups = self.get_affected_groups(request)
        if type(new_groups) == Response:
            # Error response
            return new_groups
        obj.shared_users.add(*new_users)
        obj.shared_users.add(*new_groups)
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        new_users = self.get_affected_users(request)
        if type(new_users) == Response:
            # Error response
            return new_users
        new_groups = self.get_affected_groups(request)
        if type(new_groups) == Response:
            # Error response
            return new_groups
        obj.shared_users.remove(*new_users)
        obj.shared_users.remove(*new_groups)
        return self.get(request, *args, **kwargs)

class ChartShareView(ShareView):
    permission_classes = [permissions.IsAuthenticated & IsChartOwner]
    queryset = Chart.objects.all()


class DatasourceShareView(ShareView):
    permission_classes = [permissions.IsAuthenticated & IsDatasourceOwner]
    queryset = Datasource.objects.all()