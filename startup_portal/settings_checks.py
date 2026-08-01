"""
Pure validation helpers for production-sensitive settings.

Kept separate from settings.py (which calls these at import time) so they can
be unit-tested directly without needing to reload Django's settings module.
"""
from django.core.exceptions import ImproperlyConfigured


def validate_production_network_settings(debug, allowed_hosts, cors_allowed_origins):
    """Raise ImproperlyConfigured if production hosts/origins are unset or wildcarded.

    Must be called with DEBUG=False; a no-op otherwise, since local development
    is allowed to fall back to permissive localhost defaults.
    """
    if debug:
        return

    if not allowed_hosts or '*' in allowed_hosts:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be an explicit, non-wildcard list of production "
            "hostnames when DEBUG=False. Set the ALLOWED_HOSTS environment "
            "variable (comma-separated, e.g. 'api.example.com,www.example.com')."
        )

    if not cors_allowed_origins:
        raise ImproperlyConfigured(
            "CORS_ALLOWED_ORIGINS must be an explicit list of allowed frontend "
            "origins when DEBUG=False. Set the CORS_ALLOWED_ORIGINS environment "
            "variable (comma-separated, e.g. 'https://portal.example.com')."
        )
