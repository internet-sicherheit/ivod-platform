
from django.shortcuts import get_object_or_404

from rest_framework import generics, serializers
from ..serializers import ShareGroupSerializer
from ..permissions import IsGroupPublic, IsUserGroupOwner, IsUserGroupMember, IsUserGroupAdmin
from ..models import User, ShareGroup
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions
from .util import get_affected_objects

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
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

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
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

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
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

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
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        # Try to remove users and groups
        obj.shared_users.remove(*new_users)
        obj.shared_groups.remove(*new_groups)
        # Return current shares
        return self.get(request, *args, **kwargs)