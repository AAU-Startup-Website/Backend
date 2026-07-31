"""
Account lockout helpers (Security: brute-force protection / account lockout).
"""
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def max_failed_attempts():
    return getattr(settings, 'ACCOUNT_LOCKOUT_THRESHOLD', 5)


def lockout_duration():
    minutes = getattr(settings, 'ACCOUNT_LOCKOUT_MINUTES', 30)
    return timedelta(minutes=minutes)


def is_account_locked(profile):
    if profile.lockout_until and profile.lockout_until > timezone.now():
        return True
    if profile.lockout_until and profile.lockout_until <= timezone.now():
        # Lockout expired — clear
        profile.failed_login_attempts = 0
        profile.lockout_until = None
        profile.save(update_fields=['failed_login_attempts', 'lockout_until'])
    return False


def register_failed_login(profile):
    profile.failed_login_attempts = (profile.failed_login_attempts or 0) + 1
    if profile.failed_login_attempts >= max_failed_attempts():
        profile.lockout_until = timezone.now() + lockout_duration()
    profile.save(update_fields=['failed_login_attempts', 'lockout_until'])


def clear_failed_logins(profile):
    if profile.failed_login_attempts or profile.lockout_until:
        profile.failed_login_attempts = 0
        profile.lockout_until = None
        profile.save(update_fields=['failed_login_attempts', 'lockout_until'])
