from rest_framework import permissions
from users.permissions import is_portal_admin


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Public read; write restricted to Admin Profile Role / Django Staff / Superuser.
    profile.role == 'admin' does not set is_staff.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_portal_admin(request.user)
