"""
RBAC permission classes for the AAU Startups Portal.

Roles (checklist / Authorization):
  - Anonymous
  - Student (profile.role == 'student')
  - Mentor (profile.role == 'mentor')
  - Admin Profile Role (profile.role == 'admin') — does NOT grant Django admin
  - Django Staff (user.is_staff)
  - Django Superuser (user.is_superuser)
"""
from rest_framework import permissions


def get_profile_role(user):
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def is_portal_admin(user):
    """Portal admin = profile admin role OR Django staff/superuser."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return get_profile_role(user) == 'admin'


class IsAnonymous(permissions.BasePermission):
    """Only unauthenticated users."""

    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and get_profile_role(request.user) == 'student'
        )


class IsMentor(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and get_profile_role(request.user) == 'mentor'
        )


class IsAdminProfileRole(permissions.BasePermission):
    """
    profile.role == 'admin' only.
    Does NOT grant Django admin site privileges (is_staff / is_superuser).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and get_profile_role(request.user) == 'admin'
        )


class IsDjangoStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsDjangoSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsPortalAdmin(permissions.BasePermission):
    """
    Write/admin operations for portal content:
    Admin Profile Role OR Django Staff OR Django Superuser.
    Explicitly does not elevate profile.role into is_staff.
    """

    def has_permission(self, request, view):
        return is_portal_admin(request.user)


class IsOwnerOrPortalAdmin(permissions.BasePermission):
    """Object-level: owner field (owner/founder) or portal admin."""

    owner_field = 'owner'

    def has_object_permission(self, request, view, obj):
        if is_portal_admin(request.user):
            return True
        owner = getattr(obj, self.owner_field, None)
        if owner is None and hasattr(obj, 'founder'):
            owner = obj.founder
        return owner == request.user
