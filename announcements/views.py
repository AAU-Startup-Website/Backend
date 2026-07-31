from rest_framework import viewsets, filters
from .models import Announcement
from .serializers import AnnouncementSerializer
from .permissions import IsAdminOrReadOnly


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['title', 'content', 'category', 'author']
    ordering_fields = ['created_at', 'is_pinned', 'type']
    ordering = ['-is_pinned', '-created_at']
