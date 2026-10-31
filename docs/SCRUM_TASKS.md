# SCRUM Tasks

Jira backlog for VolunteerSync. Ownership split lives in `TEAM_WORKFLOW.md`;
API contract and phase detail live in `FULL_IMPLEMENTATION_PLAN.md`.

| Ticket | Title | Status |
|---|---|---|
| SCRUM-1 | Authentication & Role-Based Access Control | Done (backend tests pass; see verification notes) |
| SCRUM-2 | NGO, Campaign & Event Management | Done (backend tests pass; see verification notes) |
| SCRUM-5 | Volunteer Opportunity & Smart Matching System | To do |
| SCRUM-6 | Application & Task Management Workflow | To do |
| SCRUM-7 | Attendance, Contribution & Reporting | To do |
| SCRUM-8 | Donation & Resource Monitoring | To do |
| SCRUM-9 | Real-Time Notifications & Communication | To do |
| SCRUM-10 | System Administration & Audit Logging | To do |
| SCRUM-11 | NGO Management System | To do |

Work order: SCRUM-1 and SCRUM-2 first, then the rest.

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
Opportunity CRUD with search/filters, `services/matching.py` (weighted score:
0.45 skills, 0.20 interests, 0.20 location, 0.15 availability), and
`GET /opportunities/recommended` with a match explanation. Unit-tested ranking.

## SCRUM-6 — Application & Task Management Workflow
Application state machine (`SUBMITTED -> UNDER_REVIEW -> ACCEPTED|REJECTED`),
task state machine (`PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED`, or
`DECLINED`), tasks only assignable to volunteers with an accepted application,
invalid transitions return 409.

## SCRUM-7 — Attendance, Contribution & Reporting
Participation/attendance and hours, contribution history per volunteer,
volunteer performance ranking and impact metrics.

## SCRUM-8 — Donation & Resource Monitoring
Donation bookkeeping (no payment data), resources and distributions,
beneficiary support, donation summary per campaign, role-scoped visibility.

## SCRUM-9 — Real-Time Notifications & Communication
Persisted notifications, REST list/mark-read, authenticated WebSocket
delivery, priorities, dedupe, emergency alerts, announcements.

## SCRUM-10 — System Administration & Audit Logging
Platform-admin user management and NGO verification, read-only audit log
viewer with filters, audit coverage for all admin actions.

## SCRUM-11 — NGO Management System
NGO-admin dashboard tying together opportunities, campaigns, events,
applications, tasks, attendance, donations and reports for one NGO.
