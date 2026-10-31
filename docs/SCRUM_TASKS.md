# SCRUM Tasks

Jira backlog for VolunteerSync. Ownership split lives in `TEAM_WORKFLOW.md`;
API contract and phase detail live in `FULL_IMPLEMENTATION_PLAN.md`.

| Ticket | Title | Status |
|---|---|---|
| SCRUM-1 | Authentication & Role-Based Access Control | Done (backend tests pass; see verification notes) |
| SCRUM-2 | NGO, Campaign & Event Management | Done (backend tests pass; see verification notes) |
| SCRUM-5 | Volunteer Opportunity & Smart Matching System | Done (backend tests pass; see notes) |
| SCRUM-6 | Application & Task Management Workflow | Done (backend tests pass; see notes) |
| SCRUM-7 | Attendance, Contribution & Reporting | Done (backend tests pass; see notes) |
| SCRUM-8 | Donation & Resource Monitoring | Done (backend tests pass; see notes) |
| SCRUM-9 | Real-Time Notifications & Communication | Done (backend tests pass; see notes) |
| SCRUM-10 | System Administration & Audit Logging | Done (backend tests pass; see notes) |
| SCRUM-11 | NGO Management System | Done (backend tests pass; see notes) |

Work order: all nine tickets are now done (1/2, 5/6, 7/8, 9/10/11).

### Verification notes (SCRUM-1 and SCRUM-2)
- Verified: 51 backend tests, `ruff`, Alembic upgrade/downgrade/check on SQLite,
  seed script run twice, live API smoke test (login, refresh cookie, list, create),
  frontend `npm run build`.
- Not verified: Alembic against MySQL (none available locally), browser click-through
  of the new React pages, frontend automated tests (none exist yet).
- The Campaigns page for volunteers/donors (`/campaigns`) still shows demo data;
  donation fields (raised/goal) belong to SCRUM-8. NGO-admin pages are API-backed.
- NGO admin and platform admin accounts are created by seed/trusted flow only.

---

## SCRUM-1 — Authentication & Role-Based Access Control

Plan reference: Phase 1 (foundation models) and Phase 2.

Scope
- Foundation models/migration needed by auth: `User`, `Volunteer`, `NGO`,
  `Beneficiary`, `RefreshToken`, plus the append-only `AuditLog` utility.
- Registration (`/auth/register`: `VOLUNTEER`, `DONOR`, `BENEFICIARY` only; NGOs use `/auth/register-ngo`, see below),
  login, refresh (rotating), logout, `me` (get/patch), change password.
- bcrypt password hashing, JWT access token, opaque refresh token stored as
  hash and delivered as an HTTP-only cookie, reuse detection.
- Login rate limiting; generic invalid-credentials message.
- Role dependencies: `get_current_user`, `require_roles`,
  `require_verified_ngo_admin`, `get_optional_user`.
- Consistent error envelope (`error.code/message/fields`).
- Frontend: `AuthContext`, Axios refresh-and-retry, Login/Register forms,
  `ProtectedRoute`/`RoleRoute`, logout.

Acceptance criteria
- [x] `/auth/register` cannot create `NGO_ADMIN` / `PLATFORM_ADMIN`. Organisations sign up through `/auth/register-ngo`,
      which creates an NGO admin whose NGO is PENDING (no publishing power) until a platform admin verifies it.
      Platform admins are created by the seed only.
- [x] Duplicate email returns 409; invalid fields return field-level errors.
- [x] Wrong password and unknown email give the same message.
- [x] Refresh rotates the token; reusing an old one is rejected and revokes the session family.
- [x] Logout revokes refresh; inactive users cannot log in.
- [x] Wrong role gets 403; missing/invalid token gets 401.
- [x] Password change invalidates the old password.
- [x] Passwords/refresh tokens are never returned or stored in plaintext.
- [x] Protected frontend routes redirect to `/login` and preserve destination.

## SCRUM-2 — NGO, Campaign & Event Management

Plan reference: Phase 3 (NGO, campaigns, events).

Scope
- `NGO` profile: `GET/PATCH /ngos/me`, `GET /ngos` (discovery), platform-admin
  verification `PATCH /ngos/{id}/verify`.
- `Campaign` model + API: public/authorized list and detail with pagination,
  search, status and location filters; verified NGO admin create/update/archive,
  scoped to their own NGO.
- `Event` model + API: list/detail, verified NGO admin CRUD scoped to own campaigns.
- Campaign status machine: `DRAFT -> ACTIVE -> COMPLETED`, `ACTIVE/DRAFT -> ARCHIVED`;
  invalid transitions return 409.
- Every NGO/campaign/event mutation writes an audit log entry.
- Frontend: NGO-admin pages to manage campaigns and events (API-backed, with
  loading/empty/error states).

Acceptance criteria
- [x] Only a verified NGO admin can create/edit; others get 403.
- [x] An NGO admin cannot modify another NGO's campaigns or events (404/403).
- [x] Event date must fall within campaign dates; end date >= start date.
- [x] List endpoints use the standard `items/page/page_size/total/pages` envelope.
- [x] Invalid campaign status transitions return 409.
- [x] Admin mutations are recorded in the `audit_logs` table (the read-only viewer is SCRUM-10).

---

## SCRUM-5 — Volunteer Opportunity & Smart Matching System

Plan reference: Phase 3 (opportunities, volunteer profile) and Phase 5.

Scope
- `Opportunity` model and API: browse/search (title, location, skill, campaign, sort,
  pagination); verified NGO admin create/update/deactivate, scoped to own NGO.
- Volunteer profile: `GET/PATCH /volunteers/me` (skills, interests, availability days, experience, city).
- `services/matching.py`: pure, deterministic scoring
  `0.45*skills + 0.20*interests + 0.20*location + 0.15*availability` (weights from settings,
  validated to sum to 1). Skills/interests use Jaccard; location is `City[, Region]` (same city 1.0,
  same region 0.5); availability is the share of required days the volunteer can cover.
- `GET /opportunities/recommended`: active opportunities of verified NGOs ranked best-first with
  score, percentage, per-factor breakdown and "why matched" reasons; ties break by lowest id.
- Frontend: Opportunities page (Recommended tab with match %, Browse tab with filters and Apply),
  volunteer Profile page, NGO-admin Opportunities page.

Acceptance criteria
- [x] Score is 0..1 and deterministic; weights come from config.
- [x] Unit tests cover ranking, no overlap, exact/partial location, availability, empty profile, ties.
- [x] Inactive opportunities and unverified NGOs never appear publicly or in recommendations.
- [x] Only the owning, verified NGO admin can create/edit/close an opportunity.
- [x] Opportunity changes are audit-logged.

## SCRUM-6 — Application & Task Management Workflow

Plan reference: Phase 4 (applications and tasks; attendance is SCRUM-7).

Scope
- Application state machine `SUBMITTED -> UNDER_REVIEW -> ACCEPTED | REJECTED`; one application per
  volunteer per opportunity (DB unique constraint plus a 409).
- APIs: apply, `GET /applications/me`, NGO review queue `GET /applications`,
  `PATCH /applications/{id}/review` (with optional note).
- Task state machine `PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED`, or `PENDING -> DECLINED`.
  Volunteers move only their own tasks; NGO admins create, edit and (re)assign.
- A task can only be assigned to a volunteer with an ACCEPTED application to this NGO (and to the
  task's opportunity when it has one). A declined task can be reassigned and restarts as PENDING.
- Invalid transitions return 409 `INVALID_TRANSITION`; ineligible assignee returns 409 `NOT_ELIGIBLE`.
- Review, task create/update/assign are audit-logged.
- Frontend: My Applications, My Tasks (accept/decline/start/complete), NGO-admin Applications review
  queue and Tasks (create/assign) pages.

Acceptance criteria
- [x] Skipping or reversing a state returns 409 for both machines.
- [x] Rejected/pending/other-NGO volunteers cannot be assigned tasks.
- [x] A volunteer cannot see or change another volunteer's task (404); admins cannot drive volunteer status (403).
- [x] The review queue is scoped to the admin's own NGO and exposes no volunteer email/phone.

### Verification notes (SCRUM-5 and SCRUM-6)
- Verified: 91 backend tests total, `ruff`, Alembic 0002 upgrade/downgrade/check on SQLite,
  a live API run of the whole path (ranked matches -> apply -> review -> accept -> assign -> task
  completed), `npm run build`.
- Not verified: the React pages in a browser, MySQL, notifications on status changes (SCRUM-9).
- `availability` is a list of weekday codes (`MON`..`SUN`) on both volunteers and opportunities.

## SCRUM-7 — Attendance, Contribution & Reporting

Plan reference: Phase 4 (participation, contributions) and Phase 6 (volunteer ranking).

Scope
- `Participation` model: attendance flag, hours (0-24), unique per volunteer and event.
- `POST/PATCH /participation`, `GET /participation`: verified NGO admin records attendance for events
  of their own campaigns, only for volunteers with an accepted application with that NGO, and only
  once the event date has passed. Marking someone absent zeroes the hours.
- `GET /contributions/me`: total hours, events attended, tasks completed/assigned, hours per month,
  and the participation history (newest first).
- `GET /reports/volunteer-performance`: ranking by hours then completed tasks (equal numbers share a
  rank). NGO admins see their own NGO, platform admins see all; optional `campaign_id` filter.
- Frontend: volunteer "My impact" page (replaces the demo numbers), NGO-admin Attendance and Reports pages.

Acceptance criteria
- [x] Duplicate attendance returns 409; hours outside 0-24 or hours on an absent volunteer return 422.
- [x] Attendance cannot be recorded for future events, other NGOs' events, or non-accepted volunteers.
- [x] Contribution totals update immediately after attendance or task completion.
- [x] Ranking and report scope are tested, including NGO isolation.
- [x] Attendance changes are audit-logged.

## SCRUM-8 — Donation & Resource Monitoring

Plan reference: Phase 6.

Scope
- `Donation` model (bookkeeping only) with `POST /donations` (donors), `GET /donations/me`,
  NGO `GET /donations`, and `PATCH /donations/{id}/status` (`PENDING -> RECEIVED | REJECTED`, else 409).
  The request schema rejects unknown fields, so card numbers/CVV/bank details can never be submitted or stored.
  Donations are accepted only for ACTIVE campaigns of verified NGOs.
- `Resource` and `ResourceDistribution`: per-campaign stock with an atomic check-and-increment, so
  distributions can never exceed the total (409 "not enough stock"); the total can't drop below what's gone out.
- `CampaignBeneficiary`: NGO admins enrol a registered beneficiary (by email) or record a new person for one
  of their campaigns, and track `PENDING -> ACTIVE -> COMPLETED` support.
- `GET /campaigns/{id}/utilization`: aggregate money received and resource usage. Visible to the owning NGO,
  platform admins, and donors whose donation to that campaign was marked received. Contains no beneficiary data.
- `GET /support/me`: a beneficiary sees only their own enrolment and what they personally received.
- `GET /reports/donation-summary`: per-campaign received/pending money, donation and donor counts, by type.
- Frontend: donor Donations page (donate, history, utilization), beneficiary Support page, real Campaigns
  list for everyone, NGO-admin Donations, Resources & beneficiaries, and Reports pages.

Acceptance criteria
- [x] Only donors can donate; volunteers, beneficiaries and NGO admins get 403.
- [x] Payment fields are rejected (422) and no such columns exist.
- [x] Over-allocation is impossible; failed attempts leave stock unchanged.
- [x] Volunteers, donors and other NGOs get 403 on beneficiary data; beneficiaries see only their own records.
- [x] Donation confirmation, resource, distribution and enrolment changes are audit-logged.

### Verification notes (SCRUM-7 and SCRUM-8)
- Verified: 120 backend tests total, `ruff`, Alembic 0003 upgrade/downgrade/check on SQLite, seed run
  twice, `npm run build`,, and a live API run of the whole flow on the seeded app.
- Not verified: the React pages in a browser, MySQL, concurrent distributions under real parallel load
  (the check-and-increment is a single SQL UPDATE, but only tested sequentially).
- Finance writes (resources, enrolment, distributions) are blocked only on ARCHIVED campaigns, so a
  COMPLETED campaign can still hand out leftover stock.
- Notifications for donation/attendance updates arrive with SCRUM-9.

## SCRUM-9 — Real-Time Notifications & Communication

Plan reference: Phase 7.

Scope
- `Notification` model (title, message, type, priority LOW/NORMAL/HIGH, UNREAD/READ, optional in-app link,
  dedupe key). Every notification is persisted first.
- `services/notifications.notify()` writes inside a SAVEPOINT of the caller's transaction, so it commits or
  rolls back with the business change, and swallows its own errors: a failed notification can never fail a
  review, donation or assignment. Live push happens only after the commit succeeds and is also best-effort.
- Triggers: new application / application review, task assigned / task status changed, donation pledged /
  confirmed or rejected, attendance recorded, campaign status change (volunteers and donors of that NGO/campaign),
  manual event reminders (`POST /events/{id}/reminders`), announcements, emergency alerts.
- `POST /announcements` (verified NGO admin): audience = the NGO's accepted volunteers and/or donors, optionally
  narrowed to one campaign. Priority HIGH is an emergency alert. Audit-logged.
- REST: `GET /notifications` (filter by status, priority, type; paginated), `GET /notifications/unread-count`,
  `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`.
- `WS /ws/notifications?token=<JWT>`: the token is validated *before* the socket is accepted (bad/missing/expired
  token or inactive user is refused), the first message reports the unread count, `ping` gets `pong`.
- Fatigue controls: identical unread notifications are deduplicated, three priority levels, filters in the UI.
- Frontend: live bell with unread badge and dropdown, urgent toast for HIGH priority, full Notifications page with
  filters, NGO-admin Announcements page (with emergency confirm), "Remind volunteers" on upcoming events.
  The client reconnects with backoff and polls every 60 s as a fallback.

Acceptance criteria
- [x] Bad, missing or expired tokens and deactivated users cannot open the socket.
- [x] A connected user receives the notification live after the transaction commits; others receive nothing.
- [x] A disconnected user still finds it in their inbox.
- [x] Simulated failures in notification creation and in live delivery do not break the core request.
- [x] Users can read only their own notifications (404 otherwise).
- [x] Duplicates are suppressed while the first is unread.

## SCRUM-10 — System Administration & Audit Logging

Plan reference: Phase 2 (audit utility), Phase 6 (platform reports), admin console.

Scope
- Platform-admin only (one router-level guard): `GET /admin/audit-logs` (filters: actor, action, entity type/id,
  date range, text; paginated), `GET /admin/audit-logs/actions`, `GET /admin/users` (+ role/active/search filters),
  `GET/PATCH /admin/users/{id}` (activate/deactivate), `POST /admin/ngo-admins` (the trusted way to create an NGO
  admin), `GET /admin/stats`. NGO verification stays at `PATCH /ngos/{id}/verify`.
- Deactivating a user revokes all their refresh tokens and their access token stops working immediately.
  An admin cannot deactivate themselves.
- The audit log is append-only: no write routes exist (405), and the ORM refuses to update or delete an
  `AuditLog` row. Every admin mutation from SCRUM-1..8 plus user (de)activation, NGO-admin creation,
  announcements and emergency alerts is recorded with actor, action, entity and details.
- Frontend (platform admin): Overview, NGOs & verification (with create-NGO-admin form), Users, Audit Log viewer.

Acceptance criteria
- [x] NGO admins, volunteers and anonymous callers cannot reach any `/admin` route (403/401).
- [x] Audit entries cannot be modified or deleted through the API or the ORM.
- [x] Each action in the spec list (approve/reject application, donation/resource edits, task assignment,
  NGO verification) has an audit entry.
- [x] Deactivated users are locked out at once; no-op changes write no audit row.

## SCRUM-11 — NGO Management System

Plan reference: ties together SCRUM-2, 5, 6, 7 and 8 for one NGO.

Scope
- `GET /ngos/me/dashboard`: campaigns, opportunities, applications and tasks by status, accepted volunteers,
  volunteer hours, beneficiaries, money received, pending pledges, resource stock vs given out, upcoming events,
  last 10 actions, and a "needs your attention" list (applications to review, donations to confirm, unassigned or
  declined tasks, past events without attendance). Zero-count items are hidden.
- `GET /ngos/me/activity`: the NGO's own change history (read-only, paginated). Everything is scoped to the caller's NGO.
- Frontend: the NGO-admin home is now this dashboard; organisation profile moved to `/admin/profile`; navigation
  groups Campaigns, Events, Opportunities, Applications, Tasks, Attendance, Donations, Resources, Reports,
  Announcements.

Acceptance criteria
- [x] Numbers match the underlying modules (tested across all of them in one scenario).
- [x] Another NGO's data never appears; unverified NGOs still get their dashboard.
- [x] Only NGO admins can call it (403 for everyone else).

### NGO onboarding and applicant contact (added after review)
- `POST /auth/register-ngo`: an organisation signs itself up (signup form: "NGO / organisation"). The account can log
  in and edit its profile at once, but is PENDING: campaigns, opportunities, events, announcements and every other
  write are blocked (403) until a platform admin verifies it. Platform admins are notified of each signup; the NGO is
  notified of the decision (with the rejection reason, if any). Signup is audit-logged.
- Applying shares the applicant's name, email and phone with the NGO that owns the opportunity (and only that NGO).
  The review queue shows them with mailto/tel links; the volunteer's own list never carries these fields.
- `POST /applications/{id}/messages`: a verified NGO admin messages an applicant in-app. It arrives as a live
  notification with the NGO's reply address; identical unread messages are not repeated; the audit log records that a
  message was sent, not its content.
- Tests: `test_ngo_onboarding.py` (15 tests).

### Alignment with the project report (added after reading `CSE314_Report_Overleaf.pdf`)
Full endpoint-by-endpoint mapping, with every deliberate difference, is in `docs/API_REFERENCE.md`. Summary of what was added:
- **Mobile number:** collected at signup, editable on the volunteer profile and My Account, validated (7-15 digits);
  a volunteer cannot apply until it is set (409 `PROFILE_INCOMPLETE`) because NGOs contact applicants through it.
- **NGO registration details:** contact number, registration information, validated logo upload (PNG/JPG/WEBP, 2 MB,
  checked by content), admin remarks on verification; `PUT/DELETE /ngos/{id}` (delete refused when the NGO has records).
- **Volunteer API:** `POST/GET/PUT/DELETE /volunteers[/{id}]`, contributions review for NGOs, `GET/PUT /users/profile`.
- **Report paths:** every route also answers under `/api/...` (not only `/api/v1/...`); `PUT` accepted wherever the report says it;
  `POST /applications`, `PATCH /applications/{id}/status`, `GET /matching/opportunities`, `/participations`, top-level
  `/resources` and `/beneficiaries`, role-aware `GET /tasks` and `GET /donations`, `PUT /donations/{id}`, `POST /notifications`.
- **Campaigns:** donation goal with progress bar, emergency flag (sorted first), create as draft or active.
- **Events:** NGOs assign volunteers to an event roster; volunteers can view upcoming events, join and leave.
- **Volunteer screens:** a real dashboard (replacing the demo numbers), Events page, impact page with people reached and
  NGOs supported, printable volunteer certificate, notification settings, My Account menu.
- **Admin:** delete accounts with no history, `/admin/reports` bundle, campaign and resource-utilization reports.
- **Operations:** `scripts/backup_local.py` (backup and `--restore`) for the report's backup and recovery requirement.

### Verification notes (SCRUM-9, 10 and 11)
- Verified: full backend suite, `ruff`, Alembic 0004 upgrade/downgrade/check on SQLite, seed run twice,
  `npm run build`, and a run against a real uvicorn server: a bad WebSocket token was refused, an emergency alert
  sent by the NGO arrived live on the volunteer's open socket, and unread counts, dashboard, platform stats and
  audit log returned the expected data.
- Not verified: the React pages in a browser (including the bell/toast and WebSocket reconnect behaviour),
  MySQL, many simultaneous sockets or multiple server workers.
- The WebSocket manager is in-process. With several uvicorn workers, a live push only reaches sockets held by the
  worker that handled the request (the notification is still saved and shows up on the next poll). Use a shared
  broker such as Redis pub/sub if you deploy more than one worker.
- An access token is checked once when the socket opens; a very long-lived connection is not re-checked until it reconnects.
- Announcements reach only people connected to the NGO (accepted volunteers, donors); there is no broadcast to
  every user on the platform.
