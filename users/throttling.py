from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Brute-force protection for login endpoint."""
    scope = 'login'


class PasswordResetRateThrottle(AnonRateThrottle):
    """Throttle password-reset requests."""
    scope = 'password_reset'


class BurstRateThrottle(SimpleRateThrottle):
    """Short-window burst limit keyed by user or IP."""
    scope = 'burst'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
