from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to create, edit, or delete announcements.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to authenticated admins
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Check Django superuser/staff status
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        # Check Custom Profile role
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            return True
            
        return False
