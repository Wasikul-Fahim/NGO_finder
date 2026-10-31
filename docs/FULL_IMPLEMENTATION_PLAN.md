# VolunteerSync Full Implementation Plan

## Purpose

This document turns `docs/PROJECT_SPEC.md` and the VolunteerSync dashboard brief
into an implementation checklist for a production-shaped application. It is a
build plan and API contract, not a claim that these features already exist.

The target outcome is a working volunteer/NGO platform where users can sign up,
log in, access role-protected dashboards, discover opportunities, apply, receive
tasks and notifications, record participation, and see measurable impact.

## Current baseline

The repository currently has:

- FastAPI with `GET /api/v1/health` and OpenAPI docs.
- SQLAlchemy/Alembic scaffolding with no domain models or migrations yet.
- React/Vite/Tailwind VolunteerSync dashboard pages with frontend demo data.
- Local Docker-free setup using SQLite for the Phase 0 scaffold.
- Docker Compose configuration for MySQL, backend, and frontend.

The dashboard must be migrated from demo data to API data as the backend modules
are implemented. Do not silently leave a screen looking functional while its
writes still disappear in browser state.

## Non-negotiable rules

1. Keep the existing stack: FastAPI, Pydantic v2, SQLAlchemy ORM, MySQL,
   Alembic, React/Vite, Tailwind, React Router, and Axios.
2. Use integer primary keys, foreign keys, indexes, and UTC timestamps.
3. Access database records through SQLAlchemy ORM queries only. Do not add raw
   SQL to feature code. The health check may use SQLAlchemy's `select(1)` probe.
4. Enforce roles in backend dependencies. Hiding a link in React is not access
   control.
5. Validate every state transition server-side and return HTTP 409 for invalid
   transitions.
6. Keep public responses free of password hashes, refresh-token material, and
   unnecessary beneficiary PII.
7. Every admin mutation must create an append-only audit log in the same
   transaction where practical.
8. Notifications must never make the core transaction fail. Persist first,
   attempt delivery in a guarded service, and log delivery failures.
9. Add tests for every new user-visible flow before marking its phase complete.
10. Use conventional commits and stop to run checks after each phase.

## Target architecture

```text
frontend/
  src/
    api/             Axios client, auth refresh, API modules
    components/      shell, forms, tables, cards, feedback states
    context/         AuthContext, notification state
    hooks/           query/mutation and responsive hooks
    pages/           public and role-specific pages
    routes/          route tree and role guards
backend/app/
  api/v1/            versioned routers and dependencies
  core/              config, database, security, logging, errors
  models/            SQLAlchemy entities and enums
  schemas/           Pydantic request/response contracts
  services/          auth, matching, notifications, audit, reports
  ws/                authenticated notification WebSocket
  tests/             unit, API, state-machine, and permission tests
backend/alembic/     migration environment and revisions
scripts/             idempotent demo-data seed command
```

## Phase 1 — Database foundation

### 1.1 Shared model conventions

Create a declarative base and reusable timestamp mixin:

- `id: int` primary key.
- `created_at` and `updated_at` in UTC.
- `updated_at` changes on update.
- Explicit indexes for email, foreign keys, status fields, dates, and common
  search fields.
- SQLAlchemy relationships use explicit `back_populates` and sensible cascade
  behavior.
- JSON columns are used for skills, interests, availability, and audit details.

### 1.2 Required entities

Implement the entities from `PROJECT_SPEC.md`:

- `User`: name, unique normalized email, password hash, phone, role, location,
  active/verified flags.
- `Volunteer`: one-to-one user profile with skills, interests, availability,
  experience.
- `NGO`: owner user, name, description, address, contact, verification status.
- `Beneficiary`: optional linked user, contact and assistance status.
- `Campaign`: NGO, title, description, location, dates, status, volunteer and
  resource requirements.
- `Opportunity`: NGO, optional campaign, title, description, location, skill,
  interest, availability requirements, active flag.
- `Event`: campaign, event name, date/time, location, description.
- `Application`: volunteer/opportunity link, submission date, status.
- `Task`: campaign, optional opportunity, optional volunteer, task details,
  deadline, status.
- `Participation`: volunteer/event attendance, date, hours.
- `Donation`: donor, NGO, optional campaign, amount/type/date/status. No card
  number, CVV, bank credentials, or raw payment payload.
- `Resource`: campaign resource totals and allocation.
- `ResourceDistribution`: resource/beneficiary quantity and date.
- `CampaignBeneficiary`: composite campaign/beneficiary link and support status.
- `Notification`: user, message, type, priority, date, read status.
- `AuditLog`: actor, action/entity identifiers, JSON details, timestamp.

Add one supporting entity required for refresh-token rotation:

- `RefreshToken`: user, token `jti` hash, issued/expiry/revoked timestamps,
  replacement token id, and optional device metadata. Store a hash, never the
  raw refresh token.

### 1.3 Enums and constraints

Use Python/SQLAlchemy enums with matching Pydantic literals for:

- Roles: `NGO_ADMIN`, `VOLUNTEER`, `DONOR`, `BENEFICIARY`, optional
  `PLATFORM_ADMIN`.
- Application: `SUBMITTED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`.
- Task: `PENDING`, `ACCEPTED`, `IN_PROGRESS`, `COMPLETED`, `DECLINED`.
- Donation types: `MONEY`, `FOOD`, `CLOTHES`, `MEDICINE`, `EDUCATIONAL`, `OTHER`.
- Notification status/priority and campaign/NGO verification statuses.

Add database uniqueness and check constraints where they protect invariants,
including one application per volunteer/opportunity and non-negative donation,
resource, quantity, hours, and progress values.

### 1.4 Migration and seed

- Generate one initial Alembic revision for all Phase 1 tables.
- Make `alembic upgrade head` idempotent and tested against MySQL.
- Make `scripts/seed.py` idempotent by stable email/key lookup.
- Seed one verified NGO admin, five volunteers, two donors, two beneficiaries,
  campaigns, opportunities, events, and safe demo records.
- Read seed passwords only from environment or clearly documented local demo
  defaults; never commit real credentials.

**Phase 1 checks:** migration upgrade/downgrade, seed twice without duplicates,
health with MySQL, model import, and repository lint.

## Phase 2 — Authentication, signup, and RBAC

This phase must be completed before claiming that the dashboard is a working
application.

### 2.1 Registration policy

Public registration may create only:

- `VOLUNTEER`
- `DONOR`
- `BENEFICIARY`

`NGO_ADMIN` and `PLATFORM_ADMIN` must be created by a trusted seed/admin flow
or invitation. Never trust a client-supplied admin role.

For volunteer registration, collect name, email, password, location, and role;
then create the linked volunteer profile with empty editable arrays. Donor and
beneficiary profiles may be completed after signup.

Normalize email by trimming and lowercasing. Reject duplicates with a clear
`409` response. Return field-level validation errors for invalid email, weak
password, missing name, unsupported role, or mismatched confirmation.

### 2.2 Token strategy

Use short-lived JWT access tokens and rotating refresh tokens:

- Access token: JWT, approximately 15–30 minutes, includes `sub`, `role`, `jti`,
  and expiry.
- Refresh token: random opaque token, stored only as an HTTP-only cookie in
  production/local same-site development; store only its hash in `RefreshToken`.
- Refresh endpoint revokes the presented token and issues a replacement.
- Reuse of a revoked refresh token revokes the related token family/session.
- Local development uses `Secure=false`; production requires HTTPS and
  `Secure=true`.
- Axios sends `withCredentials: true` and retries one failed request after a
  successful refresh. Prevent infinite refresh loops.
- Logout revokes the current refresh token and clears the cookie.

Password hashing must use bcrypt or Argon2 through a dedicated security service.
Never compare or store plaintext passwords.

### 2.3 Auth API contract

All routes are under `/api/v1/auth`:

| Method | Route | Auth | Result |
| --- | --- | --- | --- |
| `POST` | `/register` | Public | Create user and return safe user summary |
| `POST` | `/login` | Public | Issue access token and refresh cookie |
| `POST` | `/refresh` | Refresh cookie | Rotate refresh token and return access token |
| `POST` | `/logout` | Auth/refresh | Revoke session and clear cookie |
| `GET` | `/me` | Access token | Return current user/profile summary |
| `PATCH` | `/me` | Auth | Update allowed profile fields |
| `POST` | `/change-password` | Auth | Verify current password and replace hash |

Login must be rate-limited by IP and email using `slowapi` or equivalent.
Return the same generic invalid-credentials message for unknown email and wrong
password. Do not reveal whether an email exists.

### 2.4 Backend dependencies

Create reusable dependencies:

- `get_current_user()` — validates access JWT and loads active user.
- `require_roles(*roles)` — rejects unauthorized roles with HTTP 403.
- `require_verified_ngo_admin()` — checks both role and NGO verification.
- `get_optional_user()` — for public endpoints that personalize when logged in.

Use a consistent error shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please correct the highlighted fields.",
    "fields": {"email": "Enter a valid email address."}
  }
}
```

### 2.5 Frontend auth flow

Replace the current auth interceptor stub with:

- `AuthContext` storing `user`, `accessToken`, `isLoading`, and auth actions.
- App startup calls `/auth/refresh`, then `/auth/me`; failure means signed out.
- Login form submits email/password, stores access token in memory, and routes
  by role.
- Register form includes role selector for the allowed public roles and
  password confirmation.
- Logout clears user state and returns to `/login`.
- `ProtectedRoute` redirects unauthenticated users to `/login` and preserves
  the intended destination.
- `RoleRoute` rejects users without the page's role.
- All forms show loading, validation, success, and server-error states.
- Do not put refresh tokens in localStorage. If persistence is required for
  the access token, use the smallest practical lifetime and clear it on logout.

### 2.6 Auth acceptance tests

Backend tests must cover:

- Register valid volunteer/donor/beneficiary.
- Reject duplicate email and invalid fields.
- Reject public NGO admin registration.
- Login succeeds with correct credentials.
- Login fails generically with unknown/wrong credentials.
- Access token protects `/auth/me`.
- Refresh rotates the token and rejects reuse of the old token.
- Logout invalidates refresh use.
- Inactive users cannot log in.
- Role dependency returns 403 for the wrong role.
- Password change invalidates the old password.

Frontend smoke tests must cover register, login, logout, redirect, refresh, and
an expired access-token retry.

## Phase 3 — Dashboard data and core volunteer/NGO APIs

Replace `frontend/src/data/dashboardData.js` usage with API modules and loading
states.

### Volunteer endpoints

- `GET/PATCH /volunteers/me`
- `GET /volunteers/{id}` with PII permissions
- `GET /volunteers/me/contributions`

### NGO endpoints

- `GET /ngos/me`
- `PATCH /ngos/me`
- `GET /ngos` for permitted discovery/admin reports
- NGO verification restricted to platform admin.

### Opportunities

- `GET /opportunities` with pagination, search, location, skills, active flag,
  and sort parameters.
- `GET /opportunities/{id}`.
- `POST/PATCH/DELETE /opportunities/{id}` for verified NGO admins who own it.
- `GET /opportunities/recommended` for authenticated volunteers.

### Campaigns and events

- Public/read-authorized campaign list and detail.
- NGO-admin create/update/archive operations.
- Event list/detail and NGO-admin CRUD.

All list endpoints return a consistent envelope:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "pages": 0
}
```

Frontend pages must never assume data is non-empty. Include loading skeletons,
empty states, retryable error states, and mobile-friendly cards/tables.

## Phase 4 — Applications, tasks, participation, and contribution history

### State machines

Implement one transition service per state machine. The service must check the
current state, actor permissions, related records, and valid next state before
committing.

Application transitions:

```text
SUBMITTED -> UNDER_REVIEW -> ACCEPTED
                           -> REJECTED
```

Task transitions:

```text
PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED
        -> DECLINED
```

Only a volunteer with an accepted application may receive an opportunity task.
A volunteer may update only their assigned task. NGO admins may assign/review
owned campaign tasks.

### APIs

- `POST /opportunities/{id}/applications`
- `GET /applications/me`
- `GET /applications` for authorized NGO review queues
- `PATCH /applications/{id}/review`
- `POST /tasks`, `POST /tasks/{id}/assign`
- `PATCH /tasks/{id}/status`
- `GET /tasks/me`
- `POST/PATCH /participation` with attendance and hours
- `GET /contributions/me`

Admin review, accept/reject, assignment, attendance, and status changes create
audit entries and notifications.

## Phase 5 — Matching

Create `services/matching.py` with pure, deterministic functions:

```text
score = 0.45 * skills_similarity
      + 0.20 * interest_similarity
      + 0.20 * location_match
      + 0.15 * availability_overlap
```

Requirements:

- Score from 0 to 1.
- Use Jaccard or cosine similarity consistently and document the choice.
- Location: same city 1.0, same region 0.5, otherwise 0.
- Return score, percentage, and a short breakdown explaining the match.
- Exclude inactive opportunities and sort descending with stable tie-breaking.
- Read weights from settings and validate that they sum to 1.

Unit tests must prove ranking, no-overlap, exact location, partial location,
availability, empty profile, and tie behavior.

## Phase 6 — Donations, resources, beneficiaries, and reports

Implement role-protected endpoints for:

- Campaign donations and donor history.
- Resource totals, allocations, and distributions.
- Beneficiary records and campaign support.
- Donation summary per campaign.
- Volunteer performance ranking by hours and completed tasks.

Access rules:

- Donors see their own donations and authorized campaign utilization.
- Volunteers do not see beneficiary PII.
- Beneficiaries see only their own support status.
- NGO admins see beneficiaries belonging to their NGO/campaign.
- Platform admins may see aggregate reports.

Donation records represent bookkeeping only. There is no payment processor in
this project and no raw card/payment credentials may be accepted or stored.

## Phase 7 — Notifications and WebSocket delivery

Implement:

- `GET /notifications`
- `PATCH /notifications/{id}/read`
- `PATCH /notifications/read-all`
- `WS /ws/notifications?token=<JWT>`

Authenticate the JWT before accepting the WebSocket. Persist every notification
before attempting delivery. Add a connection manager keyed by user id, and use
a safe publish helper:

```text
try:
    persist notification
    await deliver if connected
except Exception:
    log the delivery failure
    never roll back the main business transaction solely because delivery failed
```

Push on application review, task assignment, event reminders, campaign changes,
donation updates, and high-priority emergency alerts. Deduplicate equivalent
notifications and keep priority/status filters in the UI.

## Frontend implementation contract

### Routes

Public:

- `/` — landing/marketing page when signed out, dashboard when signed in.
- `/login`
- `/register`

Volunteer:

- `/dashboard`
- `/profile`
- `/opportunities`
- `/opportunities/:id`
- `/applications`
- `/tasks`
- `/events`
- `/impact`

NGO admin:

- `/admin`
- `/admin/opportunities`
- `/admin/campaigns`
- `/admin/events`
- `/admin/applications`
- `/admin/tasks`
- `/admin/attendance`
- `/admin/donations`
- `/admin/reports`
- `/admin/audit-log`
- `/admin/announcements`

Donor:

- `/campaigns`
- `/campaigns/:id`
- `/donate/:campaignId`
- `/donations`
- `/donations/utilization`

Beneficiary:

- `/support`
- `/support/:campaignId`

### API client modules

Keep API calls out of presentational components:

- `api/client.js` — base URL, credentials, access token, refresh retry.
- `api/auth.js`
- `api/opportunities.js`
- `api/campaigns.js`
- `api/tasks.js`
- `api/donations.js`
- `api/notifications.js`
- `api/reports.js`

Every page must support loading, empty, error, and success states. Use reusable
form controls and consistent toast/inline error presentation.

## Configuration

Document and validate these variables:

```text
DB_URL
SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
CORS_ORIGINS
REFRESH_COOKIE_SECURE
REFRESH_COOKIE_SAMESITE
MATCHING_SKILLS_WEIGHT
MATCHING_INTEREST_WEIGHT
MATCHING_LOCATION_WEIGHT
MATCHING_AVAILABILITY_WEIGHT
VITE_API_URL
MYSQL_DATABASE
MYSQL_USER
MYSQL_PASSWORD
MYSQL_ROOT_PASSWORD
```

Production secrets must come from the deployment environment. Never commit a
real `.env`, demo password, JWT secret, or payment payload.

## Verification gates

Do not move to the next phase until its gate passes.

### Backend gate

```sh
.venv/bin/python -m pytest backend/app/tests -q
.venv/bin/python -m ruff check backend/app
cd backend && ../.venv/bin/alembic upgrade head && ../.venv/bin/alembic current
```

Add integration tests against MySQL for migrations and core flows. SQLite is
useful for the Phase 0 health smoke test but is not sufficient proof of MySQL
compatibility.

### Frontend gate

```sh
npm --prefix frontend run build
npm --prefix frontend audit --omit=dev
```

Run browser smoke checks for registration, login, protected redirect, dashboard
load, opportunity search, application, task transition, donation history, and
logout on desktop and mobile widths.

### End-to-end definition of done

A seeded local environment must support this complete scenario:

1. A volunteer registers and logs in.
2. The volunteer profile is saved and can be edited.
3. The volunteer sees ranked opportunities and match explanations.
4. The volunteer applies to an opportunity.
5. An NGO admin reviews and accepts the application.
6. The NGO admin assigns a valid task.
7. The volunteer receives a persisted/live notification.
8. The volunteer moves the task through valid states to completed.
9. The NGO admin records event attendance and hours.
10. The volunteer sees updated contribution history and impact metrics.
11. A donor records a donation and sees their donation history/utilization.
12. Admin actions appear in the read-only audit log.
13. Invalid transitions and unauthorized resource access are rejected.
14. Tests, lint, migrations, frontend build, and browser smoke checks pass.

## Recommended commit sequence

```text
feat: add domain models and initial migration
feat: implement registration and password hashing
feat: implement jwt login and refresh rotation
feat: add role-based route dependencies
feat: connect auth forms and protected routes
feat: implement volunteer and opportunity APIs
feat: connect dashboard to backend data
feat: implement applications and task state machines
feat: add matching service and tests
feat: implement donations resources and reports
feat: add notification websocket delivery
chore: harden validation and complete deployment docs
```

Each commit should leave the documented checks runnable. Update the README and
setup guide whenever a new required service, environment variable, or migration
step is introduced.
