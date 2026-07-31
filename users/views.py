from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
from .authentication import issue_token, revoke_user_tokens
from .lockout import is_account_locked, register_failed_login, clear_failed_logins
from .throttling import LoginRateThrottle, PasswordResetRateThrottle
from .models import Profile
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
import logging

audit_logger = logging.getLogger('audit')
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class CustomAuthToken(ObtainAuthToken):
    """
    Login with throttling, account lockout, token rotation & issuance.
    """
    throttle_classes = [LoginRateThrottle]
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request},
        )

        # Pre-check lockout by username before credential validation
        username = request.data.get('username')
        if username:
            try:
                user = User.objects.select_related('profile').get(username=username)
                profile, _ = Profile.objects.get_or_create(user=user)
                if is_account_locked(profile):
                    return Response(
                        {
                            'detail': 'Account temporarily locked due to failed login attempts. Try again later.'
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except User.DoesNotExist:
                pass

        if not serializer.is_valid():
            if username:
                try:
                    user = User.objects.select_related('profile').get(username=username)
                    profile, _ = Profile.objects.get_or_create(user=user)
                    register_failed_login(profile)
                    audit_logger.info(
                        '{"event":"login_failed","username":"%s","attempts":%s}'
                        % (username, profile.failed_login_attempts)
                    )
                except User.DoesNotExist:
                    pass
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        profile, _ = Profile.objects.get_or_create(user=user)
        if is_account_locked(profile):
            return Response(
                {'detail': 'Account temporarily locked due to failed login attempts. Try again later.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        clear_failed_logins(profile)
        # Token rotation: revoke previous token, issue new one
        token = issue_token(user, rotate=True)
        audit_logger.info(
            '{"event":"login_success","user_id":%s,"username":"%s"}' % (user.pk, user.username)
        )

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': user.profile.role if hasattr(user, 'profile') else 'student',
            'token_expires_hours': getattr(settings, 'AUTH_TOKEN_EXPIRY_HOURS', 24),
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.select_related('profile').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CoFounderMatchView(generics.ListAPIView):
    queryset = User.objects.filter(profile__role='student').select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['profile__skills', 'profile__bio', 'username']


class LogoutView(APIView):
    """Token revocation (logout)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            revoke_user_tokens(request.user)
            audit_logger.info(
                '{"event":"logout","user_id":%s}' % request.user.pk
            )
            return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Logout failed.'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # Always return the same message (no email enumeration)
        generic = {'message': 'If an account with that email exists, a password reset email has been sent.'}

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(generic, status=status.HTTP_200_OK)
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email=email).first()

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_base}/password-reset/confirm?uid={uid}&token={token}"
        # Include path-style reference for API/clients: .../confirm/{uid}/{token}/
        api_style = f"/api/users/password-reset/confirm/{uid}/{token}/"

        send_mail(
            'Password Reset Request',
            (
                f'Click the link to reset your password: {reset_link}\n'
                f'Reference: {api_style}\n'
                f'UID: {uid}\nToken: {token}'
            ),
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@startup.local'),
            [email],
            fail_silently=False,
        )

        return Response(generic, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid UID'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        # Revoke all API tokens after password change
        revoke_user_tokens(user)
        profile, _ = Profile.objects.get_or_create(user=user)
        clear_failed_logins(profile)

        return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
