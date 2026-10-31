# API Reference

How the API in Chapter 6 of the project report (`CSE314_Report_Overleaf.pdf`) maps to the running backend.

- Base URL: `http://localhost:8000`. Every route works under **`/api/v1/...`** and, exactly as the report writes
  them, under **`/api/...`** (e.g. `/api/auth/register` and `/api/v1/auth/register` are the same endpoint).
- Interactive docs (all routes, try-it-out): `http://localhost:8000/docs`.
- Authentication: `Authorization: Bearer <access token>` from `POST /auth/login`. The refresh token is an HTTP-only cookie.
- Updates: where the report says `PUT`, both `PUT` and `PATCH` are accepted.
- Errors: `{"error": {"code", "message", "fields"?}}`. Invalid state changes return **409**, wrong role **403**, bad input **422**.
- Lists: `?page=1&page_size=20` and the envelope `{items, page, page_size, total, pages}`.
- Roles: `NGO_ADMIN`, `VOLUNTEER`, `DONOR`, `BENEFICIARY`, `PLATFORM_ADMIN` (the report's "system administrator").

Legend: ✅ as in the report · ➕ extra beyond the report · ⚠️ deliberate difference (reason given).

## 6.2 Authentication and user management

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/auth/register` (name, email, password, **phone**, role) | `POST /auth/register` ✅ | Roles: `VOLUNTEER`, `DONOR`, `BENEFICIARY`. Also takes `confirm_password`, `location`. Phone is validated (7–15 digits, optional `+`). |
| – | `POST /auth/register-ngo` ➕ and `POST /ngos` ✅ | Organisations sign up here; the NGO starts **PENDING**. |
| `POST /api/auth/login` | `POST /auth/login` ✅ | Returns `access_token`; sets the refresh cookie. Rate-limited. |
| – | `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/change-password` ➕ | Refresh tokens rotate; reuse revokes the session. |
| `GET /api/users/profile` | `GET /users/profile` ✅ (same as `GET /auth/me`) | |
| `PUT /api/users/profile/update` | `PUT\|PATCH /users/profile/update` ✅ (same as `PATCH /auth/me`) | name, **phone**, location. The role cannot be changed here. |

## 6.3 Volunteer management

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/volunteers` | `POST /volunteers` ✅ | Sign-up already creates an empty profile; this recreates one after deletion (409 if it exists). Fields: skills, interests, availability (`MON`..`SUN`), experience, location, **phone**. |
| `GET /api/volunteers` | `GET /volunteers` ✅ | NGO admins see volunteers who applied to *their* opportunities; platform admins see all. Filters `q`, `skill`. |
| – | `GET /volunteers/me`, `PUT\|PATCH /volunteers/me` ➕ | The volunteer's own profile; `profile_complete` is true once mobile number, city and a skill are set. **A mobile number is required before applying** (409 `PROFILE_INCOMPLETE`). |
| – | `GET /volunteers/{id}`, `GET /volunteers/{id}/contributions` ➕ | Owner, platform admin, or an NGO the volunteer applied to (contributions limited to that NGO). |
| `PUT /api/volunteers/{volunteer_id}` | `PUT\|PATCH /volunteers/{id}` ✅ | Owner or platform admin. |
| `DELETE /api/volunteers/{volunteer_id}` | `DELETE /volunteers/{id}` ⚠️ | Owner or platform admin. Refused with 409 (and a reason) if the profile has applications, attendance or tasks, so NGO records stay accountable. |

## 6.4 NGO management

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/ngos` (name, email, contact number, address, description, registration information, logo) | `POST /ngos` ✅ | Fields: `ngo_name`, `contact` (public email), `contact_number`, `address`, `description`, `registration_info`, plus the admin's account (`name`, `email`, `password`, `confirm_password`). Returns the new account with `ngo.verification_status = PENDING`. |
| (logo) | `POST /ngos/me/logo`, `DELETE /ngos/me/logo` ✅ | `multipart/form-data` field `file`. PNG/JPG/WEBP, max 2 MB, type checked from the file's bytes (not its name); SVG refused. Served from `/uploads/logos/<file>`. |
| `GET /api/ngos` | `GET /ngos` ✅ | Verified NGOs for everyone signed in; platform admins also see pending/rejected (`?status=`). `GET /ngos/{id}` ➕, `GET /ngos/me` ➕. |
| `PUT /api/ngos/{ngo_id}` | `PUT\|PATCH /ngos/{id}` ✅ (and `/ngos/me`) | The NGO's own admin or a platform admin. |
| `DELETE /api/ngos/{ngo_id}` | `DELETE /ngos/{id}` ✅ | Own admin or platform admin; refused with 409 and an explanation if it has campaigns, opportunities or donations (the report allows exactly this). |
| `PATCH /api/ngos/{ngo_id}/verification` (status, admin remarks) | `PATCH /ngos/{id}/verification` ✅ (alias `/verify`) | Body `{"status": "VERIFIED"\|"REJECTED", "remarks": "..."}`. Remarks are stored, shown to the NGO and sent in a notification. Platform admin only. |

## 6.5 Campaigns and events

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/campaigns` (NGO id, title, description, location, dates, required volunteers, **status**) | `POST /campaigns` ✅ | NGO id comes from the login (cannot create for another NGO). `status`: `DRAFT` (default) or `ACTIVE`. ➕ `donation_goal`, `is_emergency`, `required_resources`. Verified NGO only. |
| `GET /api/campaigns` | `GET /campaigns` ✅ | Public sees ACTIVE/COMPLETED; owners see their drafts. Each campaign has `donations_received`, `donation_progress` (% of goal) and `is_emergency`; emergencies sort first. Filters `q`, `status`, `location`, `ngo_id`, `emergency`, `mine`. |
| `PUT /api/campaigns/{id}` | `PUT\|PATCH /campaigns/{id}` ✅ | Not editable once completed/archived. |
| `DELETE /api/campaigns/{id}` | `DELETE /campaigns/{id}` ⚠️ | **Archives** instead of deleting, so donations, events and history stay intact. Status changes: `POST /campaigns/{id}/status` (DRAFT→ACTIVE→COMPLETED, →ARCHIVED; else 409). |
| (events, design 5.1.4) | `GET/POST /events`, `GET/PUT/PATCH/DELETE /events/{id}` ➕ | Event date must be inside the campaign. |
| "assign volunteers to events" (3.1.3) | `POST /events/{id}/assignments`, `GET …/assignments`, `DELETE …/assignments/{volunteer_id}` ➕ | Only accepted volunteers of that NGO, only for upcoming events. |
| "view upcoming events", "apply for events" | `GET /events?upcoming=true`, `GET /events/me`, `POST/DELETE /events/{id}/join` ➕ | A volunteer accepted by the NGO can join/leave. `joined` flag on each event. |
| – | `POST /events/{id}/reminders` ➕ | Reminds the NGO's accepted volunteers. |

## 6.6 Applications and matching

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/applications` | `POST /applications` ✅ body `{"opportunity_id": n}` (also `POST /opportunities/{id}/applications`) | Volunteer comes from the login; application date and status (`SUBMITTED`) are set by the server. One per opportunity. Needs a mobile number. ⚠️ Applications attach to an *opportunity* (which may belong to a campaign), not directly to a campaign. |
| `GET /api/applications` | `GET /applications` (NGO review queue, with applicant name, email, **phone**) and `GET /applications/me` ✅ | Contact details are visible only to the NGO that owns the opportunity. |
| `PATCH /api/applications/{id}/status` | `PATCH /applications/{id}/status` ✅ (alias `/review`) | `SUBMITTED→UNDER_REVIEW→ACCEPTED\|REJECTED`; anything else 409. |
| `GET /api/matching/opportunities` | `GET /matching/opportunities` ✅ (alias `/opportunities/recommended`) | Ranked by 0.45 skills + 0.20 interests + 0.20 location + 0.15 availability, with `percentage`, `breakdown`, `reasons`. |
| – | `POST /applications/{id}/messages` (NGO→applicant), `POST /applications/{id}/reply` (applicant→NGO) ➕ | In-app messages delivered as notifications. |
| – | Opportunities: `GET/POST /opportunities`, `GET/PATCH/DELETE /opportunities/{id}` ➕ | `DELETE` deactivates. |

## 6.7 Tasks and participation

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/tasks` (campaign, volunteer, name, description, deadline, status) | `POST /tasks` ✅ | Status starts `PENDING`. A volunteer can be assigned only if they have an ACCEPTED application with the NGO (409 `NOT_ELIGIBLE`). Also `POST /tasks/{id}/assign`, `PATCH /tasks/{id}`. |
| `GET /api/tasks` | `GET /tasks` ✅ | Volunteers: their tasks. NGO admins: their NGO's. Platform admin: all. (`GET /tasks/me` ➕) |
| `PATCH /api/tasks/{id}/status` | `PATCH /tasks/{id}/status` ✅ | Volunteer only: `PENDING→ACCEPTED→IN_PROGRESS→COMPLETED`, or `PENDING→DECLINED`. Else 409. |
| `POST /api/participations` | `POST /participations` ✅ (also `/participation`) | Attendance + hours (0–24); only for accepted volunteers, own events, after the event date. `GET`/`PATCH` too. |
| – | `GET /contributions/me` ➕ | Hours, events, tasks, monthly hours, **NGOs supported, people reached**. |

## 6.8 Donations and resources

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/donations` (donor, NGO, campaign, amount, type, date, payment status) | `POST /donations` ✅ | Donor from the login; NGO from the campaign; date today; status `PENDING`. Types `MONEY/FOOD/CLOTHES/MEDICINE/EDUCATIONAL/OTHER`. ⚠️ **No payment data is accepted or stored** (unknown fields such as card numbers are rejected with 422). |
| `GET /api/donations` | `GET /donations` ✅ | Donors: their own. NGO admins: their NGO's. Platform admin: all. |
| `PUT /api/donations/{id}` | `PUT\|PATCH /donations/{id}` ✅ | NGO corrects amount/type/note; before/after saved in the audit log; the donor is notified. Payment status: `PATCH /donations/{id}/status` (`PENDING→RECEIVED\|REJECTED`). |
| `POST/GET/PUT/DELETE /api/resources` | `POST /resources`, `GET /resources`, `PUT\|PATCH /resources/{id}`, `DELETE /resources/{id}` ✅ | `DELETE` refused (409) once units have been distributed. Distribution: `POST /resources/{id}/distributions` (cannot exceed stock). |
| – | `GET /campaigns/{id}/utilization` ➕ | Aggregate usage for the NGO, platform admin, and donors whose donation was received. |

## 6.9 Beneficiaries

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/beneficiaries` (name, contact, location, required assistance, campaign, support status) | `POST /beneficiaries` ✅ | Body also accepts `email` to enrol an already-registered beneficiary. |
| `GET /api/beneficiaries` | `GET /beneficiaries` ✅ | **NGO admins only**, and only people enrolled in their campaigns (volunteers/donors get 403). |
| `PUT /api/beneficiaries/{id}` | `PUT\|PATCH /beneficiaries/{id}` ✅ | Body needs `campaign_id`. People with their own account manage their own details; the NGO can change only their support status. |
| – | `GET /support/me` ➕ | A beneficiary sees only their own enrolments and what they received. |

## 6.10 Notifications

| Report | Implemented | Notes |
|---|---|---|
| `POST /api/notifications` | `POST /notifications` ✅ (alias `/announcements`) | Verified NGO admin → its volunteers/donors; `priority: "HIGH"` = emergency alert. Notifications for applications, tasks, events, campaigns and donations are created automatically. |
| `GET /api/notifications` | `GET /notifications` ✅ | Filters `status`, `priority`, `notification_type`. ➕ `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`. |
| WebSocket `/ws/notifications` | `WS /ws/notifications?token=<JWT>` ✅ | Token checked **before** the socket is accepted. |
| (notification fatigue, 3.1.3) | `GET/PUT /notifications/settings` ➕ | Mute notification types; HIGH-priority and emergency alerts can't be muted. Identical unread notifications are not repeated. |

## 6.11 Administration and auditing (platform admin only)

| Report | Implemented | Notes |
|---|---|---|
| `GET, PATCH, DELETE /api/admin/users` | `GET /admin/users`, `GET\|PATCH\|DELETE /admin/users/{id}` ✅ | `PATCH {"is_active": false}` deactivates and signs the user out. `DELETE` works only for accounts with no history (otherwise 409 → deactivate). You can't deactivate/delete yourself. |
| – | `POST /admin/ngo-admins`, `GET /admin/stats` ➕ | |
| `GET /api/admin/audit-logs` | `GET /admin/audit-logs` ✅ | Filters actor, action, entity, date range, text. **Read-only** (no write routes; the ORM refuses updates/deletes). |
| `GET /api/admin/reports` | `GET /admin/reports` ✅ | Volunteers (top 10), campaigns, donations, resource utilization in one response. NGO-scoped versions: `GET /reports/volunteer-performance`, `/reports/campaigns`, `/reports/donation-summary`, `/reports/resource-utilization`. |

## 6.12 API security

| Report | Status |
|---|---|
| JWT authentication | Access token 20 min + rotating refresh cookie (HttpOnly, SameSite). |
| Role-based access control | Enforced by backend dependencies on every route (not just hidden links). |
| Request validation | Pydantic on every body; field-level errors. |
| Secure password hashing | bcrypt; identical error for unknown email and wrong password; login rate-limited. |
| Restricted access to sensitive information | Applicant contact details → owning NGO only; beneficiary data → owning NGO and the beneficiary; no payment data stored. |
| Proper error handling | One error format; notification failures never fail the main action. |
| Secure file upload validation | Logo type (by content) and size checked; SVG refused; random file names. |
| HTTPS/TLS | Configure at deployment (`REFRESH_COOKIE_SECURE=true` behind HTTPS). Local development uses plain HTTP. |
| Audit logging | Every admin action is recorded (actor, action, entity, details, time). |

## Not done / out of scope (be aware)

- **Encryption at rest** (report 3.9) and **MySQL**: local runs use SQLite; the code is database-agnostic but the migrations were only run on SQLite here. Use full-disk encryption locally and MySQL with encrypted storage in production.
- **Email verification / "account verification"** and sending real emails or SMS: `is_verified` exists and platform admins can set it, but no email is sent.
- **"Manage reported content"** (admin function in 5.1.10): there is no content-reporting feature to moderate.
- **Online payment gateway** (listed under future development in the report) is intentionally absent.
- **Backups:** `python scripts/backup_local.py` (and `--restore`) covers the local database and uploaded logos; a scheduled backup and a written incident-response process are operational tasks outside the code.
