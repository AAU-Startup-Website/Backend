from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from audit.models import AuditLog
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
        # The queryset itself is scoped to mentor/founder, so an out-of-scope
        # meeting ID looks identical to a nonexistent one: 404, not 403 (a 403
        # here would confirm to an unauthorized user that the meeting exists).
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_out_of_scope_and_nonexistent_meeting_return_same_status(self):
        meeting = Meeting.objects.create(
            startup=self.startup,
            mentor=self.mentor,
            title="Private Meeting"
        )
        nonexistent_id = meeting.id + 99999

        self.client.force_authenticate(user=self.other_user)
        out_of_scope_response = self.client.get(f'/api/meetings/{meeting.id}/')
        nonexistent_response = self.client.get(f'/api/meetings/{nonexistent_id}/')

        self.assertEqual(out_of_scope_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(out_of_scope_response.status_code, nonexistent_response.status_code)

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

    def test_approving_idea_writes_audit_log_entry(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/ideas/{self.idea.id}/approve/'
        self.client.post(url)

        entry = AuditLog.objects.get(action='idea.approve', target_id=str(self.idea.id))
        self.assertEqual(entry.actor, self.admin)
        self.assertEqual(entry.target_type, 'Idea')

    def test_non_admin_cannot_approve_idea(self):
        self.client.force_authenticate(user=self.user)
        url = f'/api/ideas/{self.idea.id}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.idea.refresh_from_db()
        self.assertNotEqual(self.idea.status, 'approved')

    def test_reapproving_idea_is_a_documented_noop(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/ideas/{self.idea.id}/approve/'

        first_response = self.client.post(url)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.idea.refresh_from_db()
        startup_count_after_first_approval = Startup.objects.count()
        startup_id_after_first_approval = self.idea.startup.id

        # Re-approving must not silently succeed again, create a second
        # Startup, or otherwise mutate state.
        second_response = self.client.post(url)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.idea.refresh_from_db()
        self.assertEqual(self.idea.status, 'approved')
        self.assertEqual(self.idea.startup.id, startup_id_after_first_approval)
        self.assertEqual(Startup.objects.count(), startup_count_after_first_approval)


class PitchDeckUploadValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pitchfounder', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_disallowed_file_extension_is_rejected(self):
        bad_file = SimpleUploadedFile(
            "malware.exe", b"fake binary content", content_type="application/octet-stream"
        )
        response = self.client.post('/api/ideas/', {
            'title': 'Test idea',
            'description': 'desc',
            'pitch_deck': bad_file,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pitch_deck', response.data)
        self.assertEqual(Idea.objects.count(), 0)

    def test_oversized_file_is_rejected(self):
        oversized_content = b'0' * (11 * 1024 * 1024)  # 11MB > the 10MB limit
        big_file = SimpleUploadedFile("deck.pdf", oversized_content, content_type="application/pdf")
        response = self.client.post('/api/ideas/', {
            'title': 'Test idea',
            'description': 'desc',
            'pitch_deck': big_file,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pitch_deck', response.data)
        self.assertEqual(Idea.objects.count(), 0)

    def test_allowed_small_pdf_is_accepted(self):
        small_file = SimpleUploadedFile("deck.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf")
        response = self.client.post('/api/ideas/', {
            'title': 'Test idea',
            'description': 'desc',
            'pitch_deck': small_file,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Idea.objects.count(), 1)
