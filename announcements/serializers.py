from .models import Announcement
from startup_portal.serializers import StrictModelSerializer


class AnnouncementSerializer(StrictModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'type', 'category',
            'is_pinned', 'author', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
