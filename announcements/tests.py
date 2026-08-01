from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditLog
from .models import Announcement

User = get_user_model()


class AnnouncementAuditLogTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staffadmin', password='password123', is_staff=True)

    def test_create_writes_audit_log(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            '/api/announcements/',
            {'title': 'New Announcement', 'content': 'Body', 'type': 'info'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = AuditLog.objects.get(action='announcement.create')
        self.assertEqual(entry.actor, self.staff)
        self.assertEqual(entry.target_type, 'Announcement')

    def test_delete_writes_audit_log(self):
        announcement = Announcement.objects.create(title='To delete', content='Body')
        self.client.force_authenticate(user=self.staff)
        response = self.client.delete(f'/api/announcements/{announcement.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        entry = AuditLog.objects.get(action='announcement.delete', target_id=str(announcement.id))
        self.assertEqual(entry.actor, self.staff)
