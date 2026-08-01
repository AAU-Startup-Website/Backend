from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.authtoken.models import Token
import re

User = get_user_model()

class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='oldpassword123')
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_logout(self):
        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify token is deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        
        # Verify checking protected endpoint fails
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_flow(self):
        # 1. Request Reset
        url_request = reverse('password_reset')
        response = self.client.post(url_request, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Email Sent
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        # Extract Link
        # Link format: .../password-reset/confirm/{uid}/{token}/
        # Pattern: confirm/([^/]+)/([^/]+)/
        match = re.search(r'confirm/([^/]+)/([^/]+)/', email_body)
        self.assertIsNotNone(match)
        uid, token = match.groups()
        
        # 2. Confirm Reset
        url_confirm = reverse('password_reset_confirm')
        new_password = 'newpassword123'
        response = self.client.post(url_confirm, {
            'uid': uid,
            'token': token,
            'new_password': new_password
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Verify Login with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_password_reset_rejects_password_failing_django_validators(self):
        # 1. Request Reset
        url_request = reverse('password_reset')
        response = self.client.post(url_request, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        email_body = mail.outbox[0].body
        match = re.search(r'confirm/([^/]+)/([^/]+)/', email_body)
        self.assertIsNotNone(match)
        uid, token = match.groups()

        # 2. Attempt to confirm with a common/weak password (passes the
        # serializer's min_length=8 but must be rejected by Django's
        # AUTH_PASSWORD_VALIDATORS, notably CommonPasswordValidator).
        url_confirm = reverse('password_reset_confirm')
        response = self.client.post(url_confirm, {
            'uid': uid,
            'token': token,
            'new_password': 'password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Password must remain unchanged.
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('password'))
        self.assertTrue(self.user.check_password('oldpassword123'))

    def test_swagger_docs(self):
        url = reverse('schema-swagger-ui')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class EmailLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='emailuser', email='emailuser@example.com', password='password123'
        )

    def tearDown(self):
        cache.clear()

    def test_login_with_email_succeeds(self):
        url = reverse('login')
        response = self.client.post(
            url, {'email': 'emailuser@example.com', 'password': 'password123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'emailuser')

    def test_login_with_unknown_email_returns_generic_error(self):
        url = reverse('login')
        response = self.client.post(
            url, {'email': 'nobody@example.com', 'password': 'password123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginLockoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='lockoutuser', email='lockout@example.com', password='correctpassword123'
        )

    def tearDown(self):
        cache.clear()

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
    def test_account_locks_after_max_failed_attempts(self):
        url = reverse('login')
        for _ in range(3):
            response = self.client.post(
                url, {'username': 'lockoutuser', 'password': 'wrongpassword'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Even the correct password is now rejected while the lockout is active.
        response = self.client.post(
            url, {'username': 'lockoutuser', 'password': 'correctpassword123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
    def test_successful_login_resets_failed_attempt_counter(self):
        url = reverse('login')
        for _ in range(2):
            response = self.client.post(
                url, {'username': 'lockoutuser', 'password': 'wrongpassword'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Logging in correctly before hitting the threshold resets the counter.
        response = self.client.post(
            url, {'username': 'lockoutuser', 'password': 'correctpassword123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for _ in range(2):
            response = self.client.post(
                url, {'username': 'lockoutuser', 'password': 'wrongpassword'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Only 2 failed attempts since the reset (threshold is 3) -> not locked.
        response = self.client.post(
            url, {'username': 'lockoutuser', 'password': 'correctpassword123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileSelfElevationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='plainstudent', email='plain@example.com', password='password123')
        # created via signal or not; ensure profile exists with default role
        from users.models import Profile
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'role': 'student'})
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_patch_profile_role_to_admin_is_ignored(self):
        url = reverse('profile')
        response = self.client.patch(url, {'profile': {'role': 'admin'}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.role, 'student')
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_patch_profile_other_fields_still_work(self):
        url = reverse('profile')
        response = self.client.patch(url, {'profile': {'bio': 'updated bio', 'role': 'admin'}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'updated bio')
        self.assertEqual(self.profile.role, 'student')


class AdminSignupTests(APITestCase):
    def test_signup_as_admin_role_does_not_grant_staff_permissions_by_default(self):
        url = reverse('register') # Assuming 'register' is the name, need to check users/urls.py
        data = {
            'username': 'candidate_admin',
            'email': 'admin@example.com',
            'password': 'password123',
            'profile': {
                'role': 'admin'
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(username='candidate_admin')
        self.assertEqual(user.profile.role, 'admin')
        # Expecting this to be False currently
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class CoFounderMatchRoleFilterTests(APITestCase):
    @staticmethod
    def _set_role(user, role):
        from users.models import Profile
        if hasattr(user, 'profile'):
            user.profile.role = role
            user.profile.save()
        else:
            Profile.objects.create(user=user, role=role)

    def setUp(self):
        self.requester = User.objects.create_user(username='requester', password='password123')
        self._set_role(self.requester, 'student')

        self.student = User.objects.create_user(username='student1', password='password123')
        self._set_role(self.student, 'student')

        self.mentor = User.objects.create_user(username='mentor1', password='password123')
        self._set_role(self.mentor, 'mentor')

        self.client.force_authenticate(user=self.requester)

    def test_default_returns_only_students(self):
        response = self.client.get('/api/users/match/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data]
        self.assertIn('student1', usernames)
        self.assertNotIn('mentor1', usernames)

    def test_role_query_param_returns_mentors(self):
        response = self.client.get('/api/users/match/?role=mentor')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data]
        self.assertIn('mentor1', usernames)
        self.assertNotIn('student1', usernames)

    def test_invalid_role_falls_back_to_student(self):
        response = self.client.get('/api/users/match/?role=not-a-real-role')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data]
        self.assertIn('student1', usernames)
        self.assertNotIn('mentor1', usernames)
