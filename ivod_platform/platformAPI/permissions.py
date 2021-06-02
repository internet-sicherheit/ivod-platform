from rest_framework import permissions
from .models import *
from django.db.models import Q
from django.contrib.auth.models import User, Group, AnonymousUser

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
        if not user or type(user) == AnonymousUser:
            return False
        shared_users = obj.shared_users.all()
        shared_groups = obj.shared_groups.all()
        group_admin_positions_of_user = user.group_admins.all()
        group_memberships_of_user = user.group_members.all()
        union_membership = (group_admin_positions_of_user | group_memberships_of_user)
        intersection_between_groups = shared_groups & union_membership
        return user in shared_users or intersection_between_groups

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

class IsGroupPublic(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only make decisions about ShareGroup Objects
        if not type(obj) == ShareGroup:
            return False
        user = request.user
        return obj.is_public

class IsUserGroupOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only make decisions about ShareGroup Objects
        if not type(obj) == ShareGroup:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user == obj.owner

class IsUserGroupMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only make decisions about ShareGroup Objects
        if not type(obj) == ShareGroup:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user in obj.group_members.all()

class IsUserGroupAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only make decisions about ShareGroup Objects
        if not type(obj) == ShareGroup:
            return False
        user = request.user
        #Check if user is in request
        if not user:
            return False
        return user in obj.group_admins.all()

class DatasourceIsSharedWithUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Only make decisions about Chart Objects
        if not type(obj) == Datasource:
            return False
        user = request.user
        #Check if user is in request
        if not user or type(user) == AnonymousUser:
            return False
        shared_users = obj.shared_users.all()
        shared_groups = obj.shared_groups.all()
        group_admin_positions_of_user = user.group_admins.all()
        group_memberships_of_user = user.group_members.all()
        union_membership = (group_admin_positions_of_user | group_memberships_of_user)
        intersection_between_groups = shared_groups & union_membership
        return user in shared_users or intersection_between_groups
