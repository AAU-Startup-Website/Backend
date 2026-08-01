import logging

from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import Profile
from .serializers import UserSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
from .throttles import LoginRateThrottle
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from rest_framework.views import APIView


User = get_user_model()
logger = logging.getLogger('users.auth')


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class CustomAuthToken(ObtainAuthToken):
    throttle_classes = [LoginRateThrottle]

    @staticmethod
    def _attempts_cache_key(username):
        return f'login:failed_attempts:{username.lower()}'

    @staticmethod
    def _lockout_cache_key(username):
        return f'login:locked_until:{username.lower()}'

    def post(self, request, *args, **kwargs):
        data = request.data
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()

        # The admin dashboard authenticates by email (FR-DASH-03); the public
        # portal authenticates by username. Both hit this same endpoint —
        # resolve email to the corresponding username up front so the rest of
        # this view (throttling, lockout, DRF's AuthTokenSerializer) only
        # ever has to deal with usernames. An unrecognized email intentionally
        # falls through with an empty username, producing the same generic
        # "invalid credentials" response as a bad password (no email
        # enumeration).
        if not username and email:
            try:
                username = User.objects.get(email__iexact=email).username
            except User.DoesNotExist:
                username = ''
            data = {**data, 'username': username}

        ip = _client_ip(request)

        if username and cache.get(self._lockout_cache_key(username)):
            logger.warning(
                'Login rejected: account locked from repeated failed attempts',
                extra={'username': username, 'ip': ip, 'event': 'login_locked'},
            )
            return Response(
                {'error': 'Too many failed login attempts. Try again later.'},
                status=status.HTTP_423_LOCKED,
            )

        serializer = self.serializer_class(data=data,
                                           context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            if username:
                attempts_key = self._attempts_cache_key(username)
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=settings.LOGIN_LOCKOUT_SECONDS)
                logger.warning(
                    'Failed login attempt',
                    extra={
                        'username': username,
                        'ip': ip,
                        'attempts': attempts,
                        'event': 'login_failed',
                    },
                )
                if attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                    cache.set(
                        self._lockout_cache_key(username),
                        True,
                        timeout=settings.LOGIN_LOCKOUT_SECONDS,
                    )
                    logger.warning(
                        'Account locked after repeated failed login attempts',
                        extra={'username': username, 'ip': ip, 'event': 'login_lockout_triggered'},
                    )
            raise

        user = serializer.validated_data['user']
        # Successful login resets any failed-attempt counter/lockout for this username.
        cache.delete(self._attempts_cache_key(username))
        cache.delete(self._lockout_cache_key(username))

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': user.profile.role if hasattr(user, 'profile') else 'student'
        })

class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class CoFounderMatchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['profile__skills', 'profile__bio', 'username']

    def get_queryset(self):
        # Defaults to student-only (co-founder matching); an explicit
        # ?role= override lets the same endpoint list mentors for the
        # meeting-booking mentor picker, etc. Restricted to real Profile
        # roles so this can't be used to enumerate arbitrary querysets.
        valid_roles = dict(Profile.ROLE_CHOICES).keys()
        role = self.request.query_params.get('role', 'student')
        if role not in valid_roles:
            role = 'student'
        return User.objects.filter(profile__role=role)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Delete the user's token to logout
            request.user.auth_token.delete()
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Points at the frontend, which collects the new password and POSTs
        # it (with uid/token) to PasswordResetConfirmView. FRONTEND_URL is
        # environment-driven so this resolves to the real deployed domain in
        # production instead of localhost. NOTE: the public portal does not
        # yet implement a /reset-password/confirm page to receive this link
        # — that's a separate frontend task, tracked outside this fix.
        reset_link = f"{settings.FRONTEND_URL}/reset-password/confirm/{uid}/{token}/"

        # Send Email
        send_mail(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_link}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid UID'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            return Response({'error': exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)

