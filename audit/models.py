from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Records administrative mutations for accountability (NFR-COMP-01).

    Written from the views that perform the action, not via signals, so the
    log entry only exists when the mutation actually succeeded.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    details = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_label = self.actor.username if self.actor else 'unknown'
        return f"{actor_label} {self.action} {self.target_type}:{self.target_id}"
