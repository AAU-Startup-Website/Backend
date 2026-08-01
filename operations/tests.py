from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Booking, Resource

User = get_user_model()


class ResourceEventPermissionTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student1', password='password123')
        self.staff = User.objects.create_user(username='staffuser', password='password123', is_staff=True)
        self.resource = Resource.objects.create(name='Conference Room A', type='meeting_room')

    def test_anonymous_cannot_list_resources(self):
        response = self.client.get('/api/resources/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_authenticated_user_can_browse_but_not_write_resources(self):
        self.client.force_authenticate(user=self.student)

        list_response = self.client.get('/api/resources/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/resources/', {'name': 'Workspace B', 'type': 'workspace'}, format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

        update_response = self.client.patch(
            f'/api/resources/{self.resource.id}/', {'availability': 'unavailable'}, format='json'
        )
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_and_create_resources(self):
        self.client.force_authenticate(user=self.staff)
        list_response = self.client.get('/api/resources/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/resources/', {'name': 'Workspace B', 'type': 'workspace'}, format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

    def test_profile_role_admin_without_staff_flag_can_manage_resources(self):
        from users.models import Profile
        profile_admin = User.objects.create_user(username='profileadmin', password='password123')
        Profile.objects.filter(user=profile_admin).update(role='admin') if Profile.objects.filter(
            user=profile_admin
        ).exists() else Profile.objects.create(user=profile_admin, role='admin')

        self.client.force_authenticate(user=profile_admin)
        response = self.client.get('/api/resources/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/resources/', {'name': 'Workspace C', 'type': 'workspace'}, format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

    def test_non_staff_authenticated_user_can_browse_but_not_write_events(self):
        self.client.force_authenticate(user=self.student)

        list_response = self.client.get('/api/events/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/events/',
            {'title': 'Pitch Night', 'event_date': '2026-09-01T18:00:00Z'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)


class BookingPermissionTests(APITestCase):
    def setUp(self):
        self.founder = User.objects.create_user(username='founder1', password='password123')
        self.other_founder = User.objects.create_user(username='founder2', password='password123')
        self.staff = User.objects.create_user(username='staffuser2', password='password123', is_staff=True)
        self.resource = Resource.objects.create(name='Meeting Room', type='meeting_room')

    def _create_booking_payload(self, **overrides):
        payload = {
            'resource': str(self.resource.id),
            'start_time': '2026-08-01T10:00:00Z',
            'end_time': '2026-08-01T11:00:00Z',
        }
        payload.update(overrides)
        return payload

    def test_booking_user_is_set_server_side(self):
        self.client.force_authenticate(user=self.founder)
        response = self.client.post(
            '/api/bookings/',
            self._create_booking_payload(user=99999),  # attempted spoof — must be ignored
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], self.founder.id)

    def test_non_staff_only_sees_own_bookings(self):
        own_booking = Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        Booking.objects.create(
            resource=self.resource, user=self.other_founder,
            start_time='2026-08-02T10:00:00Z', end_time='2026-08-02T11:00:00Z',
        )

        self.client.force_authenticate(user=self.founder)
        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [b['id'] for b in response.data]
        self.assertEqual(returned_ids, [str(own_booking.id)])

    def test_staff_sees_all_bookings(self):
        Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        Booking.objects.create(
            resource=self.resource, user=self.other_founder,
            start_time='2026-08-02T10:00:00Z', end_time='2026-08-02T11:00:00Z',
        )

        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_owner_can_cancel_own_booking(self):
        booking = Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        self.client.force_authenticate(user=self.founder)
        response = self.client.patch(
            f'/api/bookings/{booking.id}/', {'status': 'cancelled'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_owner_cannot_edit_other_fields_of_own_booking(self):
        booking = Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        self.client.force_authenticate(user=self.founder)
        response = self.client.patch(
            f'/api/bookings/{booking.id}/', {'start_time': '2026-08-01T12:00:00Z'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_cannot_confirm_own_booking(self):
        booking = Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        self.client.force_authenticate(user=self.founder)
        response = self.client.patch(
            f'/api/bookings/{booking.id}/', {'status': 'confirmed'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_act_on_someone_elses_booking(self):
        booking = Booking.objects.create(
            resource=self.resource, user=self.other_founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        self.client.force_authenticate(user=self.founder)
        response = self.client.patch(
            f'/api/bookings/{booking.id}/', {'status': 'cancelled'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_confirm_a_booking(self):
        booking = Booking.objects.create(
            resource=self.resource, user=self.founder,
            start_time='2026-08-01T10:00:00Z', end_time='2026-08-01T11:00:00Z',
        )
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            f'/api/bookings/{booking.id}/', {'status': 'confirmed'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
