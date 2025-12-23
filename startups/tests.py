from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Startup, Meeting, Idea

User = get_user_model()

class MeetingTests(APITestCase):
    def setUp(self):
        # Create Users
        self.founder = User.objects.create_user(username='founder', password='password123')
        self.mentor = User.objects.create_user(username='mentor', password='password123')
        self.other_user = User.objects.create_user(username='other', password='password123')

        # Create Profile for mentor (assuming role field is in profile)
        # Note: Depending on your Profile model trigger, you might need to get or create
        if not hasattr(self.mentor, 'profile'):
             from users.models import Profile
             Profile.objects.create(user=self.mentor, role='mentor')
        else:
             self.mentor.profile.role = 'mentor'
             self.mentor.profile.save()

        # Create Startup
        self.startup = Startup.objects.create(
            name="Test Startup",
            description="A test startup",
            founder=self.founder
        )

        # URLs - Assuming you will register these as 'meeting-list' and 'meeting-detail'
        # Or if using ViewSets, 'meeting-list' and 'meeting-detail'
        # Since we used Generics in views.py, we need to know the URL names.
        # I will assume 'meeting-list' and 'meeting-detail' for now, but we might need to update urls.py first.
        # To avoid URL errors before registration, I will use manual paths in tests if reverse fails, 
        # but better to assume standard naming.

    def test_book_meeting(self):
        self.client.force_authenticate(user=self.founder)
        url = '/api/meetings/' # Assuming this path, verified later
        data = {
            'startup': self.startup.id,
            'mentor': self.mentor.id,
            'title': 'Mentorship Session',
            'description': 'Discussing strategy',
            'link': 'http://meet.google.com/abc'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Meeting.objects.count(), 1)
        self.assertEqual(Meeting.objects.get().title, 'Mentorship Session')

    def test_mentor_can_view_meeting(self):
        # Create meeting first
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title="Existing Meeting"
        )
        
        self.client.force_authenticate(user=self.mentor)
        url = f'/api/meetings/{meeting.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Existing Meeting")

    def test_stranger_cannot_view_meeting(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title="Private Meeting"
        )
        
        self.client.force_authenticate(user=self.other_user)
        url = f'/api/meetings/{meeting.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_meeting(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title="Original Title"
        )
        
        self.client.force_authenticate(user=self.mentor)
        url = f'/api/meetings/{meeting.id}/'
        response = self.client.patch(url, {'title': 'Updated Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.title, 'Updated Title')


class IdeaTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='password123')
        
        self.idea = Idea.objects.create(
            title="Test Idea",
            description="Test Description",
            owner=self.user
        )

    def test_admin_can_approve_idea(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/ideas/{self.idea.id}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.idea.refresh_from_db()
        self.assertEqual(self.idea.status, 'approved')
        
        # Verify startup creation
        self.assertTrue(Startup.objects.filter(name="Test Idea", founder=self.user).exists())
        self.assertIsNotNone(self.idea.startup)

    def test_non_admin_cannot_approve_idea(self):
        self.client.force_authenticate(user=self.user)
        url = f'/api/ideas/{self.idea.id}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.idea.refresh_from_db()
        self.assertNotEqual(self.idea.status, 'approved')
