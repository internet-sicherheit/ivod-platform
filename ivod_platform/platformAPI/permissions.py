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
        e_user = EnhancedUser.objects.filter(auth_user=user)[0]
        if not e_user:
            return False
        all_charts_shared = set()
        all_charts_shared.update(e_user.charts_shared_with_user.all())
        e_groups = [EnhancedGroup.objects.filter(auth_group=group) for group in user.groups.all()]
        for e_group in e_groups:
            all_charts_shared.update(e_group.charts_shared_with_group.all())
        return obj in all_charts_shared

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
        e_user = EnhancedUser.objects.filter(auth_user=user)[0]
        if not e_user:
            return False
        all_datasources_shared = set()
        all_datasources_shared.update(e_user.datasources_shared_with_user.all())
        e_groups = [EnhancedGroup.objects.filter(auth_group=group) for group in user.groups.all()]
        for e_group in e_groups:
            all_datasources_shared.update(e_group.charts_shared_with_group.all())
        return obj in all_datasources_shared
