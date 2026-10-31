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
| SCRUM-9 | Real-Time Notifications & Communication | To do |
| SCRUM-10 | System Administration & Audit Logging | To do |
| SCRUM-11 | NGO Management System | To do |

Work order: SCRUM-1/2, 5/6 and 7/8 are done; then the rest.

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
- Registration (public roles only: `VOLUNTEER`, `DONOR`, `BENEFICIARY`),
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
- [x] Public signup cannot create `NGO_ADMIN` / `PLATFORM_ADMIN`.
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
Persisted notifications, REST list/mark-read, authenticated WebSocket
delivery, priorities, dedupe, emergency alerts, announcements.

## SCRUM-10 — System Administration & Audit Logging
Platform-admin user management and NGO verification, read-only audit log
viewer with filters, audit coverage for all admin actions.

## SCRUM-11 — NGO Management System
NGO-admin dashboard tying together opportunities, campaigns, events,
applications, tasks, attendance, donations and reports for one NGO.
