from rest_framework import permissions


def _is_incubator_staff(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == 'admin'


class IsIncubatorStaff(permissions.BasePermission):
    """
    Full staff-only access. Used where even reading is staff-internal.
    """

    def has_permission(self, request, view):
        return _is_incubator_staff(request.user)


class IsIncubatorStaffOrReadOnly(permissions.BasePermission):
    """
    Events and resources: any authenticated user (founder, mentor, etc.) can
    browse them, but only incubator staff/profile-admin can create, edit, or
    delete them. Read access still requires authentication — this data isn't
    meant to be public the way announcements are.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_incubator_staff(user)


class IsOwnerOrIncubatorStaff(permissions.BasePermission):
    """
    Bookings: any authenticated user can create a booking for themselves.
    Staff/profile-admin can view and update any booking (confirm/cancel).
    A non-staff user can only act on their own booking, and only to cancel
    it (enforced in BookingViewSet.perform_update, not here) — object-level
    checks below just gate access, not which fields/values are allowed.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_incubator_staff(request.user):
            return True
        return obj.user_id == request.user.id
