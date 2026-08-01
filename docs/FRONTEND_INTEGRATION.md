# Frontend Integration Guide — New Backend Additions

This covers everything added/changed on `readytoprod` since the last integration
pass: three new apps (**announcements**, **audit**, **operations**) and
hardening changes to the existing **users** and **startups** apps.

All endpoints are mounted under `/api/`. Interactive docs: `/swagger/` or `/redoc/`.

## Auth recap (unchanged, but relevant to everything below)

- `TokenAuthentication` — send `Authorization: Token <token>` on every
  authenticated request. Token comes from `POST /api/users/login/`.
- `role` lives on `request.user.profile.role`: `student`, `mentor`,
  `investor`, `admin`. There's also Django's own `is_staff`/`is_superuser`.
  Anywhere below that says "staff", it means: `is_staff` OR `is_superuser` OR
  `profile.role == 'admin'`.
- CORS is an explicit allow-list (`CORS_ALLOWED_ORIGINS`), not a wildcard —
  make sure your frontend origin is registered in the backend env for
  non-DEBUG deployments.

---

## 1. Announcements — `/api/announcements/`

Standard DRF router (`ModelViewSet`), so all of these exist:

| Method | URL | Auth | Notes |
|---|---|---|---|
| GET | `/api/announcements/` | none required | public read |
| GET | `/api/announcements/{id}/` | none required | public read |
| POST | `/api/announcements/` | staff only | create |
| PATCH/PUT | `/api/announcements/{id}/` | staff only | update |
| DELETE | `/api/announcements/{id}/` | staff only | delete |

Non-staff users get `403` on write methods (read-only otherwise, per
`IsAdminOrReadOnly`).

**Object shape** (all fields writable except `id`/timestamps):

```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "type": "important | warning | info | success | announcement",
  "category": "string | null",
  "is_pinned": false,
  "author": "string | null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

Default ordering is newest-first (`-created_at`) — sort/pin logic (e.g.
showing pinned items first) needs to happen client-side, `is_pinned` doesn't
affect ordering server-side.

Every create/update/delete writes an entry to the audit log (see §2) —
nothing the frontend needs to do differently, just know it's tracked.

---

## 2. Audit log — internal only, no API

`audit.AuditLog` records staff mutations (announcement CRUD, idea approval,
more to come) for accountability. **There is no REST endpoint for it** —
it's currently Django-admin-only (`/admin/`). Don't build any frontend
screen expecting `/api/audit/...` to exist yet; if you need one, that's a
new backend task.

---

## 3. Operations — `/api/events/`, `/api/resources/`, `/api/bookings/`

Three related resources for incubator events, bookable resources (rooms/
equipment), and bookings against them.

### Events — `/api/events/`
Read requires auth (not public like announcements). Write requires staff.

| Method | Auth |
|---|---|
| GET (list/detail) | any authenticated user |
| POST / PATCH / DELETE | staff only |

```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "event_date": "ISO8601 datetime",
  "location": "string",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### Resources — `/api/resources/`
Same auth shape as events (auth to read, staff to write).

```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "type": "meeting_room | equipment | workspace | other",
  "capacity": "integer | null",
  "availability": "available | unavailable",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

`availability` is a plain field, not computed from bookings — the frontend
(or backend, later) is responsible for reconciling it against active
bookings if you want real-time availability.

### Bookings — `/api/bookings/`
Different rules — every authenticated user can create a booking; visibility
and edit rights depend on ownership vs. staff:

| Method | Behavior |
|---|---|
| GET (list) | non-staff sees only their own bookings; staff sees all |
| POST | any authenticated user; `user` is set server-side from the token, don't send it |
| PATCH (own booking, non-staff) | **only allowed to set `status: "cancelled"`** — any other field or value returns 403 |
| PATCH (staff) | can update any field on any booking |
| DELETE | subject to the same `IsOwnerOrIncubatorStaff` object check |

```json
{
  "id": "uuid",
  "resource": "resource-uuid",
  "resource_name": "string (read-only, denormalized)",
  "user": "user-id (read-only, set from token)",
  "user_name": "string (read-only)",
  "purpose": "string",
  "start_time": "ISO8601 datetime",
  "end_time": "ISO8601 datetime",
  "status": "pending | confirmed | cancelled",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

For a "cancel my booking" button: `PATCH /api/bookings/{id}/` with body
`{"status": "cancelled"}` only — including any other key in the payload will
cause the request to be rejected for non-staff users, even if the value is
unchanged.

---

## 4. Users app changes

No new endpoints, but behavior changed on existing ones:

- **`POST /api/users/login/`** now supports login by `username` *or*
  `email` (admin dashboard uses email per FR-DASH-03; public portal keeps
  using username). Send whichever field you have — the response shape is
  unchanged (`token`, `user_id`, `username`, `role`).
- **Account lockout**: after `LOGIN_MAX_FAILED_ATTEMPTS` (default 5) failed
  attempts on one username, login returns `423 Locked` with
  `{"error": "Too many failed login attempts. Try again later."}` for
  `LOGIN_LOCKOUT_SECONDS` (default 300s). Surface this distinctly from a
  generic "wrong password" message if you want good UX here.
- **Per-IP rate limit** on login (`10/min` by default, configurable) —
  handle `429` responses on the login form too.
- **`PATCH /api/users/profile/`**: `role` is silently dropped if included in
  the `profile` payload — a user can never self-promote to `admin` this way.
  Don't rely on a role change via this endpoint; it's admin-panel-only.

---

## 5. Startups app changes

- **Pitch deck upload** (`Idea.pitch_deck`, part of the idea create/update
  payload) now has server-side validation:
  - allowed extensions: `pdf, ppt, pptx, doc, docx`
  - max size: 10MB
  - Validation errors surface as normal DRF `400` with
    `{"pitch_deck": ["..."]}`. Client-side pre-validation (extension + size)
    before upload will save round-trips but isn't required for correctness.

- **`POST /api/ideas/{id}/approve/`** (staff only) is now idempotent: calling
  it on an already-approved idea returns `400` with
  `{"status": "idea already approved", "startup_id": <id or null>}` instead
  of silently re-running. Treat a `400` here as "already done", not
  necessarily a hard failure — check the response body.

- **`GET/PATCH/DELETE /api/meetings/{id}/`**: an out-of-scope meeting ID
  (one you're not the mentor or founder on) now returns a plain `404`
  instead of `403`. If the frontend was branching on 403 vs 404 for this
  endpoint, that logic needs updating — both "doesn't exist" and "not yours"
  now look identical (intentional, to avoid leaking existence of other
  users' meetings).

---

## Summary of endpoints to wire up

| App | Base path | Public read? | Write access |
|---|---|---|---|
| announcements | `/api/announcements/` | yes | staff |
| operations/events | `/api/events/` | no (auth required) | staff |
| operations/resources | `/api/resources/` | no (auth required) | staff |
| operations/bookings | `/api/bookings/` | no (own bookings only, unless staff) | owner (cancel-only) / staff (full) |
| audit | — | n/a, no API | Django admin only |
