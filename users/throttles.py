from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Per-IP request-rate limit on the login endpoint.

    Complements (does not replace) the per-username progressive lockout in
    CustomAuthToken — this throttle catches a single IP hammering many
    usernames; the lockout catches many attempts against one username from
    anywhere.
    """
    scope = 'login'
