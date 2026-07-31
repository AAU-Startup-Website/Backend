from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from users.models import Profile
from users.authentication import issue_token
from .models import Announcement

User = get_user_model()
STRONG_PASSWORD = 'SecurePassw0rd!'


class AnnouncementTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='stu', password=STRONG_PASSWORD)
        Profile.objects.get_or_create(user=self.student, defaults={'role': 'student'})
        self.portal_admin = User.objects.create_user(username='padmin', password=STRONG_PASSWORD)
        Profile.objects.update_or_create(user=self.portal_admin, defaults={'role': 'admin'})
        self.staff = User.objects.create_user(username='staff', password=STRONG_PASSWORD, is_staff=True)
        Profile.objects.get_or_create(user=self.staff)

        self.announcement = Announcement.objects.create(
            title='Welcome',
            content='Hello campus',
            type='info',
        )

    def test_public_read(self):
        response = self.client.get('/api/announcements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Paginated
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_uuid_primary_key(self):
        response = self.client.get(f'/api/announcements/{self.announcement.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.announcement.id))

    def test_student_cannot_write(self):
        token = issue_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.post('/api/announcements/', {
            'title': 'Nope',
            'content': 'x',
            'type': 'info',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_portal_admin_can_write(self):
        token = issue_token(self.portal_admin)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.post('/api/announcements/', {
            'title': 'Admin Note',
            'content': 'Important',
            'type': 'important',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_type_rejected(self):
        token = issue_token(self.portal_admin)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.post('/api/announcements/', {
            'title': 'Bad',
            'content': 'x',
            'type': 'not-a-real-type',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_write(self):
        token = issue_token(self.staff)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.post('/api/announcements/', {
            'title': 'Staff Note',
            'content': 'y',
            'type': 'warning',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
