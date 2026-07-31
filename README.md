# AAU Startups Portal Backend

Backend API for the AAU Startups Portal (Django + Django REST Framework).

## Features

- **Authentication**: Registration, login (token rotation + expiry), logout (revocation), password reset, account lockout, login throttling
- **Authorization (RBAC)**: Anonymous, Student, Mentor, Admin Profile Role, Django Staff, Django Superuser
- **Startups**: Ideas, approval flow, phases, milestones, meetings
- **Announcements**: Public read, admin write (UUID PK)
- **Docs**: Swagger UI at `/swagger/`

## Auth architecture note

API clients authenticate with `Authorization: Token <key>` (not HTTP-only cookies).  
Session auth remains available for the browsable API / Django admin.  
Cookie flags (`HttpOnly`, `SameSite`, `Secure`) apply to session/CSRF cookies.

## Setup

1. Clone and create a virtualenv
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set values (never commit secrets)
4. `python manage.py migrate`
5. `python manage.py seed_phases`
6. `python manage.py runserver` (dev) or use Docker/Gunicorn (below)

## Docker

```bash
docker compose up --build
```

Runs Gunicorn behind the `entrypoint.sh` migrate + seed flow.

## Frontend env

Public Next.js apps should set:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Tests

```bash
python manage.py test
```
