from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'is_pinned', 'author', 'created_at')
    list_filter = ('type', 'is_pinned', 'created_at')
    search_fields = ('title', 'content', 'author')
    ordering = ('-created_at',)
