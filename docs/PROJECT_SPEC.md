# ROLE
You are a senior full-stack engineer. Build the "Volunteer & NGO Coordination Platform" (a.k.a. Charity & Volunteer Management System), a web app connecting NGO Admins, Volunteers, Donors, and Beneficiaries. Work in phases, commit after each phase, and make sure each phase runs before moving on. Don't ask questions unless truly blocked; make reasonable decisions and note them in README.md.

# MANDATORY TECH STACK
- Frontend: React.js (Vite) + Tailwind CSS, React Router, Axios, responsive/mobile-friendly
- Backend: Python FastAPI (async where sensible), Pydantic v2
- Database: MySQL, accessed only via SQLAlchemy ORM (parameterized queries, no raw SQL), Alembic migrations
- Auth: JWT (access token + rotating refresh token), bcrypt/argon2 password hashing
- Real-time: FastAPI WebSocket for notifications
- Git/GitHub conventions, .env-based config, Docker Compose for local MySQL + backend + frontend
- Deployable to Hostinger (document the steps in README)

# USER ROLES (RBAC enforced by backend dependencies, not just UI)
1. NGO_ADMIN: manage opportunities, campaigns, events, tasks; review applications; assign tasks; record attendance; monitor donations/resources; review contributions; send announcements; view audit logs.
2. VOLUNTEER: manage profile (skills, interests, location, availability, experience); browse/search opportunities; see ranked matches; apply; view/accept/reject/update assigned tasks; view upcoming events; view participation and contribution history.
3. DONOR: view campaigns; make donations (record only, no real payment processing, no raw card data stored); view donation history and resource-utilization info for their campaigns.
4. BENEFICIARY: view campaigns/support available to them and their support status.
(Optional 5th, PLATFORM_ADMIN: verify NGOs, manage users, view reports.)

# DATA MODEL (SQLAlchemy models + Alembic)
Use integer PKs, created_at/updated_at on all tables, proper FKs and indexes.
- User(id, name, email unique, password_hash, phone, role, location, is_active, is_verified)
- Volunteer(id, user_id FK unique, skills JSON/list, interests JSON/list, availability JSON, experience)
- NGO(id, user_id FK, ngo_name, description, address, contact, verification_status)
- Beneficiary(id, user_id FK nullable, name, contact, location, required_assistance, status)
- Campaign(id, ngo_id FK, title, description, location, start_date, end_date, status, required_volunteers, required_resources)
- Opportunity(id, ngo_id FK, campaign_id FK nullable, title, description, location, required_skills, interests, availability, is_active)
- Event(id, campaign_id FK, event_name, date, time, location, description)
- Application(id, volunteer_id FK, opportunity_id FK, application_date, status)
- Task(id, campaign_id FK, opportunity_id FK nullable, volunteer_id FK nullable, task_name, description, deadline, status)
- Participation(id, volunteer_id FK, event_id FK, attendance bool, participation_date, hours)
- Donation(id, donor_id FK, ngo_id FK, campaign_id FK nullable, amount, donation_type [MONEY, FOOD, CLOTHES, MEDICINE, EDUCATIONAL, OTHER], donation_date, status)
- Resource(id, campaign_id FK, name, quantity_total, quantity_allocated, unit) + ResourceDistribution(id, resource_id FK, beneficiary_id FK, quantity, date)
- CampaignBeneficiary (M:N: campaign_id, beneficiary_id, support_status)
- Notification(id, user_id FK, message, notification_type, priority, date, status [UNREAD/READ])
- AuditLog(id, actor_user_id, action_type, entity_type, entity_id, details JSON, timestamp). Append-only: no update/delete endpoints.

# STATE MACHINES (enforce transitions server-side; reject invalid ones with 409)
- Application: SUBMITTED -> UNDER_REVIEW -> ACCEPTED | REJECTED
- Task: PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED (volunteer may also decline: PENDING -> DECLINED)
- Tasks can only be assigned to volunteers whose application is ACCEPTED.

# VOLUNTEER MATCHING (service module, unit-tested)
Score each active opportunity against a volunteer, 0 to 1, then sort descending:
score = 0.45*skills_similarity (Jaccard/cosine) + 0.20*interest_similarity + 0.20*location_match (same city = 1, same region = 0.5, else 0) + 0.15*availability_overlap
Weights live in config. Return the score plus a short "why matched" breakdown. Endpoint: GET /opportunities/recommended. Include a test file with fixtures proving ranking behavior.

# API (REST, versioned /api/v1, OpenAPI docs enabled)
Auth: register, login, refresh, logout, me, change password.
CRUD with role guards for: volunteers, ngos, opportunities (search + filters), campaigns, events, applications (apply, list, review, accept/reject), tasks (create, assign, status update), participation/attendance, contributions (aggregated hours/tasks per volunteer), donations, resources/distributions, beneficiaries, notifications (list, mark read), audit logs (admin-only, read-only), reports (volunteer performance ranking by hours + completed tasks; donation summary per campaign).
Use pagination, consistent error format, and clear validation messages.

# REAL-TIME NOTIFICATIONS
- WS endpoint /ws/notifications?token=<JWT> must authenticate before accepting.
- Push notifications for: application status changes, task assignment, event reminders, campaign updates, donation updates, emergency alerts (priority=HIGH, broadcast to targeted users).
- Persist every notification; deliver live when connected. Reduce fatigue: dedupe, priority levels, user can filter. Core flows must still work if the WebSocket/notification service fails (wrap in try/except, never block the main transaction).

# SECURITY (from SRS section 3.9)
- Hash passwords; JWT with short expiry and refresh rotation; rate-limit login attempts
- Strict Pydantic validation, ORM-only DB access, XSS-safe rendering, CORS whitelist, CSRF-safe design
- HTTPS/TLS assumed in production config; secrets only from env
- Mask PII in dashboards unless needed; beneficiary data visible only to the owning NGO/admin, never to volunteers or donors
- Audit-log every admin action (approve/reject application, edit donation/resource, assign task, verify NGO) with timestamp, user id, action type
- Never store raw payment data

# FRONTEND PAGES (role-based routing + protected routes)
Public: Landing, Login, Register (role select).
Volunteer: Dashboard, Profile, Opportunities (search/filter + "Recommended for you" with match %), Opportunity detail/Apply, My Applications, My Tasks (status updates), Events, Contribution History.
NGO Admin: Dashboard, Opportunities CRUD, Campaigns CRUD, Events CRUD, Applications review queue, Task assignment, Attendance recording, Donations and Resources monitor, Volunteer performance report, Audit Log, Announcements/Emergency alert.
Donor: Campaign list/detail, Donate, My Donations, Utilization view.
Beneficiary: Campaigns/Support status.
Shared: notification bell with live WebSocket updates, loading/empty/error states, form validation messages, mobile-responsive layout.

# PROJECT STRUCTURE
/backend (app/{api,core,models,schemas,services,ws,tests}, alembic)
/frontend (src/{pages,components,hooks,api,context})
docker-compose.yml, .env.example, README.md, seed script

# PHASES (stop and verify at the end of each)
1. Scaffold repo, Docker Compose, DB connection, Alembic, all models + initial migration, seed script (1 admin NGO, 5 volunteers, 2 donors, 2 beneficiaries, sample campaigns/opportunities).
2. Auth + RBAC + audit-log utility + tests.
3. Opportunities, campaigns, events, volunteer profile APIs + UI.
4. Applications + tasks + state machines + participation/attendance + contribution tracking, API + UI.
5. Matching service + recommended endpoint + UI + unit tests.
6. Donations, resources, distribution, beneficiaries + dashboards + reports.
7. WebSocket notifications + emergency alerts.
8. Hardening: security checklist, validation pass, pytest coverage on core flows, frontend smoke tests, README with setup/deploy (Hostinger) instructions and API summary.

# DEFINITION OF DONE
`docker compose up` starts everything; the seed script populates demo data; a volunteer can register -> see ranked matches -> apply -> get accepted by the NGO admin -> receive a task and a live notification -> complete it -> be marked present at an event -> see updated contribution history; a donor can donate and see utilization; audit logs record all admin actions; tests pass.