from .models import AuditLog


def log_action(actor, action, target_type, target_id, **details):
    """Best-effort audit write. Never let a logging failure break the request."""
    try:
        AuditLog.objects.create(
            actor=actor if getattr(actor, 'is_authenticated', False) else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=details,
        )
    except Exception:
        # Audit logging must never be the reason a real mutation fails.
        pass
