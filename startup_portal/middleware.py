"""
Security middleware: CSP / hardening headers and structured audit logging.
"""
import json
import logging
import time

audit_logger = logging.getLogger('audit')


class SecurityHeadersMiddleware:
    """
    Adds Content-Security-Policy and related hardening headers.
    Compatible with reverse proxies (Nginx) that may also set headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        response.setdefault('X-Frame-Options', 'DENY')
        return response


class AuditLogMiddleware:
    """JSON structured audit log for authenticated mutating API requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)

        if request.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            user = getattr(request, 'user', None)
            payload = {
                'event': 'api_mutation',
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': duration_ms,
                'user_id': user.pk if user and user.is_authenticated else None,
                'username': user.username if user and user.is_authenticated else None,
                'ip': request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR')),
            }
            audit_logger.info(json.dumps(payload))

        return response
