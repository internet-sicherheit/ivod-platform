from django.shortcuts import get_object_or_404
from rest_framework import generics
from ..serializers import DatasourceSerializer
from ..permissions import IsOwner, IsSharedWithUser, IsShared
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions
from .util import ShareView
from ..models import Datasource

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
        owner_permission = IsOwner()
        shared_permission = IsSharedWithUser()
        queryset = [obj for obj in queryset if owner_permission.has_object_permission(request, self,
                                                                                      obj) or shared_permission.has_object_permission(
            request, self, obj)]

        serializer = DatasourceSerializer(data=queryset, many=True)
        serializer.is_valid()
        return Response(serializer.data)


class DatasourceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Modify or delete an existing datasource"""
    permission_classes = [permissions.IsAuthenticated & (IsOwner | IsShared & IsSharedWithUser)]
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
        owner_permission = IsOwner()
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
        owner_permission = IsOwner()
        if not owner_permission.has_object_permission(request, self, current_object):
            return Response(status=status.HTTP_403_FORBIDDEN)

        current_object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DatasourceShareView(ShareView):
    """ShareView for Datasources"""
    permission_classes = [permissions.IsAuthenticated & IsOwner]
    queryset = Datasource.objects.all()