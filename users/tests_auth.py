from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core import mail
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

    def test_swagger_docs(self):
        url = reverse('schema-swagger-ui')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
