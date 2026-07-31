from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Startup, Meeting, Idea, Phase, Milestone
from users.models import Profile
from users.authentication import issue_token
from users.permissions import is_portal_admin

User = get_user_model()
STRONG_PASSWORD = 'SecurePassw0rd!'


def auth_client(client, user):
    token = issue_token(user, rotate=True)
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    return token


class MeetingTests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(username='founder', password=STRONG_PASSWORD)
        self.mentor = User.objects.create_user(username='mentor', password=STRONG_PASSWORD)
        self.other_user = User.objects.create_user(username='other', password=STRONG_PASSWORD)

        Profile.objects.update_or_create(user=self.mentor, defaults={'role': 'mentor'})
        Profile.objects.get_or_create(user=self.founder, defaults={'role': 'student'})
        Profile.objects.get_or_create(user=self.other_user, defaults={'role': 'student'})

        self.startup = Startup.objects.create(
            name='Test Startup',
            description='A test startup',
            founder=self.founder,
        )

    def test_book_meeting(self):
        auth_client(self.client, self.founder)
        url = '/api/meetings/'
        data = {
            'startup': self.startup.id,
            'mentor': self.mentor.id,
            'title': 'Mentorship Session',
            'description': 'Discussing strategy',
            'link': 'http://meet.google.com/abc',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Meeting.objects.count(), 1)
        meeting = Meeting.objects.get()
        self.assertEqual(meeting.title, 'Mentorship Session')
        self.assertIsNotNone(meeting.schedule_date)

    def test_non_founder_cannot_book_meeting(self):
        auth_client(self.client, self.other_user)
        response = self.client.post('/api/meetings/', {
            'startup': self.startup.id,
            'mentor': self.mentor.id,
            'title': 'Unauthorized',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_set_schedule_date(self):
        auth_client(self.client, self.founder)
        response = self.client.post('/api/meetings/', {
            'startup': self.startup.id,
            'mentor': self.mentor.id,
            'title': 'Dated',
            'schedule_date': '2020-01-01T00:00:00Z',
        }, format='json')
        # schedule_date is read_only — either ignored (201) or rejected as unexpected
        self.assertIn(response.status_code, (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST))
        if response.status_code == 201:
            meeting = Meeting.objects.get()
            self.assertNotEqual(str(meeting.schedule_date.year), '2020')

    def test_mentor_can_view_meeting(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title='Existing Meeting',
        )
        auth_client(self.client, self.mentor)
        response = self.client.get(f'/api/meetings/{meeting.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Existing Meeting')

    def test_stranger_cannot_view_meeting(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title='Private Meeting',
        )
        auth_client(self.client, self.other_user)
        response = self.client.get(f'/api/meetings/{meeting.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_meeting_by_mentor(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title='Original Title',
        )
        auth_client(self.client, self.mentor)
        response = self.client.patch(f'/api/meetings/{meeting.id}/', {'title': 'Updated Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting.refresh_from_db()
        self.assertEqual(meeting.title, 'Updated Title')

    def test_founder_cannot_update_meeting(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title='Original Title',
        )
        auth_client(self.client, self.founder)
        response = self.client.patch(f'/api/meetings/{meeting.id}/', {'title': 'Hijack'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IdeaTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password=STRONG_PASSWORD)
        Profile.objects.get_or_create(user=self.user, defaults={'role': 'student'})
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password=STRONG_PASSWORD
        )
        self.portal_admin = User.objects.create_user(username='padmin', password=STRONG_PASSWORD)
        Profile.objects.update_or_create(user=self.portal_admin, defaults={'role': 'admin'})
        self.portal_admin = User.objects.select_related('profile').get(pk=self.portal_admin.pk)
        self.assertFalse(self.portal_admin.is_staff)
        self.assertTrue(is_portal_admin(self.portal_admin))

        self.idea = Idea.objects.create(
            title='Test Idea',
            description='Test Description',
            owner=self.user,
        )

    def test_admin_can_approve_idea(self):
        auth_client(self.client, self.admin)
        response = self.client.post(f'/api/ideas/{self.idea.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.idea.refresh_from_db()
        self.assertEqual(self.idea.status, 'approved')
        self.assertTrue(Startup.objects.filter(name='Test Idea', founder=self.user).exists())
        self.assertIsNotNone(self.idea.startup)

    def test_portal_admin_role_can_approve_without_staff(self):
        auth_client(self.client, self.portal_admin)
        response = self.client.post(f'/api/ideas/{self.idea.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.idea.refresh_from_db()
        self.assertEqual(self.idea.status, 'approved')

    def test_duplicate_approval_prevented(self):
        auth_client(self.client, self.admin)
        self.client.post(f'/api/ideas/{self.idea.id}/approve/')
        response = self.client.post(f'/api/ideas/{self.idea.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Startup.objects.filter(name='Test Idea').count(), 1)

    def test_non_admin_cannot_approve_idea(self):
        auth_client(self.client, self.user)
        response = self.client.post(f'/api/ideas/{self.idea.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.idea.refresh_from_db()
        self.assertNotEqual(self.idea.status, 'approved')

    def test_owner_cannot_set_status_via_api(self):
        auth_client(self.client, self.user)
        response = self.client.post('/api/ideas/', {
            'title': 'New',
            'description': 'Desc',
            'status': 'approved',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')

    def test_unexpected_fields_rejected(self):
        auth_client(self.client, self.user)
        response = self.client.post('/api/ideas/', {
            'title': 'New',
            'description': 'Desc',
            'hacker_field': 'nope',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MilestonePermissionTests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(username='f1', password=STRONG_PASSWORD)
        self.other = User.objects.create_user(username='o1', password=STRONG_PASSWORD)
        Profile.objects.get_or_create(user=self.founder)
        Profile.objects.get_or_create(user=self.other)
        self.phase = Phase.objects.create(name='Ideation', order=1)
        self.startup = Startup.objects.create(
            name='S', description='D', founder=self.founder, current_phase=self.phase
        )
        self.milestone = Milestone.objects.create(
            startup=self.startup, phase=self.phase, title='M1'
        )

    def test_other_user_cannot_access_milestone(self):
        auth_client(self.client, self.other)
        response = self.client.get(f'/api/milestones/{self.milestone.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
