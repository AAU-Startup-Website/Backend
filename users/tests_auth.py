from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.authtoken.models import Token
from django.utils import timezone
from datetime import timedelta
from users.models import Profile
from users.authentication import issue_token, is_token_expired
from users.lockout import register_failed_login, is_account_locked
from django.conf import settings
import re

User = get_user_model()

STRONG_PASSWORD = 'SecurePassw0rd!'


class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123',
        )
        Profile.objects.get_or_create(user=self.user)
        self.token = issue_token(self.user, rotate=True)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_logout(self):
        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_flow(self):
        url_request = reverse('password_reset')
        response = self.client.post(url_request, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        match = re.search(r'confirm/([^/]+)/([^/\s]+)/', email_body)
        self.assertIsNotNone(match)
        uid, token = match.groups()

        url_confirm = reverse('password_reset_confirm')
        new_password = STRONG_PASSWORD
        response = self.client.post(url_confirm, {
            'uid': uid,
            'token': token,
            'new_password': new_password,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        # Tokens revoked after reset
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_password_reset_unknown_email_does_not_enumerate(self):
        url_request = reverse('password_reset')
        response = self.client.post(url_request, {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('If an account', response.data['message'])

    def test_swagger_docs(self):
        url = reverse('schema-swagger-ui')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_issues_rotated_token(self):
        old_key = self.token.key
        self.client.credentials()
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'oldpassword123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertNotEqual(response.data['token'], old_key)
        self.assertFalse(Token.objects.filter(key=old_key).exists())

    def test_expired_token_rejected(self):
        token = Token.objects.get(user=self.user)
        token.created = timezone.now() - timedelta(hours=settings.AUTH_TOKEN_EXPIRY_HOURS + 1)
        token.save(update_fields=['created'])
        self.assertTrue(is_token_expired(token))
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_lockout_after_failed_logins(self):
        self.client.credentials()
        profile = self.user.profile
        for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
            register_failed_login(profile)
            profile.refresh_from_db()
        self.assertTrue(is_account_locked(profile))

        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'oldpassword123',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_registration_and_profile(self):
        self.client.credentials()
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'email': 'student@example.com',
            'password': STRONG_PASSWORD,
            'profile': {'role': 'student', 'skills': 'python,django', 'bio': 'Hi'},
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.profile.role, 'student')
        self.assertFalse(user.is_staff)


class AdminSignupTests(APITestCase):
    def test_signup_as_admin_role_does_not_grant_staff_permissions_by_default(self):
        url = reverse('register')
        data = {
            'username': 'candidate_admin',
            'email': 'admin@example.com',
            'password': STRONG_PASSWORD,
            'profile': {'role': 'admin'},
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username='candidate_admin')
        self.assertEqual(user.profile.role, 'admin')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_user_cannot_escalate_own_role(self):
        user = User.objects.create_user(username='stu', password=STRONG_PASSWORD)
        Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
        token = issue_token(user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.patch(
            reverse('profile'),
            {'profile': {'role': 'admin'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, 'student')
