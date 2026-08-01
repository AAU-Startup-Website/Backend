from rest_framework import viewsets, exceptions
from .models import Event, Resource, Booking
from .serializers import EventSerializer, ResourceSerializer, BookingSerializer
from .permissions import IsIncubatorStaffOrReadOnly, IsOwnerOrIncubatorStaff, _is_incubator_staff


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsIncubatorStaffOrReadOnly]


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsIncubatorStaffOrReadOnly]


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsOwnerOrIncubatorStaff]

    def get_queryset(self):
        user = self.request.user
        if _is_incubator_staff(user):
            return Booking.objects.all()
        return Booking.objects.filter(user=user)

    def perform_update(self, serializer):
        user = self.request.user
        if not _is_incubator_staff(user):
            # A booking's owner may only cancel it, not edit any other
            # field (resource, times, etc). Staff can update anything.
            attempted_fields = set(self.request.data.keys())
            if attempted_fields - {'status'} or serializer.validated_data.get('status') != 'cancelled':
                raise exceptions.PermissionDenied(
                    "You can only cancel your own booking, not modify its other details."
                )
        serializer.save()
