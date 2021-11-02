from django.shortcuts import get_object_or_404

from rest_framework import generics, serializers
from ..models import User, ShareGroup
from rest_framework import status
from rest_framework.response import Response

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