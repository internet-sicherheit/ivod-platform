from rest_framework import permissions
from .models import *
from django.contrib.auth.models import User, Group

class IsChartOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Chart:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user == obj.owner