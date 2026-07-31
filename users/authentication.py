"""
Token authentication with expiration and rotation support.

Architecture note (Security / Token lifecycle):
  API auth uses DRF Token in the Authorization header (not HTTP-only cookies).
  SessionAuthentication remains available for browsable API / Django admin flows.
  Token revocation is performed on logout (token delete) and on password reset.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


def token_ttl():
    hours = getattr(settings, 'AUTH_TOKEN_EXPIRY_HOURS', 24)
    return timedelta(hours=hours)


def is_token_expired(token):
    return token.created < timezone.now() - token_ttl()


def issue_token(user, rotate=True):
    """
    Issue a token for the user.
    When rotate=True (default), revoke any existing token first (token rotation).
    """
    if rotate:
        Token.objects.filter(user=user).delete()
    token, _ = Token.objects.get_or_create(user=user)
    return token


def revoke_user_tokens(user):
    Token.objects.filter(user=user).delete()


class ExpiringTokenAuthentication(TokenAuthentication):
    """Reject tokens older than AUTH_TOKEN_EXPIRY_HOURS."""

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        if is_token_expired(token):
            token.delete()
            raise exceptions.AuthenticationFailed('Token has expired. Please log in again.')

        return (token.user, token)
