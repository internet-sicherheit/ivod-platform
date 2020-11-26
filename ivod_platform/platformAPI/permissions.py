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

class ChartIsSharedWithUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Chart:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user in obj.shared_users.all() or (obj.shared_groups.all() & user.groups.all())

class ChartIsShared(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Chart:
            return False
        return obj.visibility >= Chart.VISIBILITY_SHARED

class ChartIsSemiPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Chart:
            return False
        return obj.visibility >= Chart.VISIBILITY_SEMI_PUBLIC

class ChartIsPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Chart:
            return False
        return obj.visibility >= Chart.VISIBILITY_PUBLIC

class IsDatasourceOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Datasource:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user == obj.owner

class DatasourceIsSharedWithUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Datasource:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user in obj.shared_users.all() or (obj.shared_groups.all() & user.groups.all())