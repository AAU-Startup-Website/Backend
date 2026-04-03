import uuid
from django.db import models

class Announcement(models.Model):
    TYPE_CHOICES = (
        ('important', 'Important'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('success', 'Success'),
        ('announcement', 'Announcement'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='announcement')
    category = models.CharField(max_length=50, null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    author = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
