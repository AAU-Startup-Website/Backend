from rest_framework import permissions
from users.permissions import is_portal_admin


class IsIdeaOwnerOrPortalAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_portal_admin(request.user):
            return True
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user or is_portal_admin(request.user)
        return obj.owner == request.user


class IsStartupFounderOrPortalAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_portal_admin(request.user):
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.founder == request.user


class IsMilestoneStartupMemberOrPortalAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_portal_admin(request.user):
            return True
        return obj.startup.founder == request.user


class IsMeetingParticipant(permissions.BasePermission):
    """Mentor or startup founder may access; others get 403."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_portal_admin(request.user):
            return True
        return obj.mentor == request.user or obj.startup.founder == request.user


class CanCreateMeeting(permissions.BasePermission):
    """Only the startup founder may create meetings."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanUpdateMeeting(permissions.BasePermission):
    """Mentor (or portal admin) may update meetings."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.mentor == request.user or obj.startup.founder == request.user or is_portal_admin(request.user)
        if request.method == 'DELETE':
            return (
                obj.startup.founder == request.user
                or obj.mentor == request.user
                or is_portal_admin(request.user)
            )
        # PUT/PATCH — mentor update permissions
        return obj.mentor == request.user or is_portal_admin(request.user)
