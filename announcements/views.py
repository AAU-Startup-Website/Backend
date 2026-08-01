from rest_framework import viewsets
from .models import Announcement
from .serializers import AnnouncementSerializer
from .permissions import IsAdminOrReadOnly
from audit.utils import log_action

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            self.request.user,
            action='announcement.create',
            target_type='Announcement',
            target_id=instance.id,
            title=instance.title,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request.user,
            action='announcement.update',
            target_type='Announcement',
            target_id=instance.id,
            title=instance.title,
        )

    def perform_destroy(self, instance):
        log_action(
            self.request.user,
            action='announcement.delete',
            target_type='Announcement',
            target_id=instance.id,
            title=instance.title,
        )
        instance.delete()
