# VolunteerSync

Volunteer and NGO management platform (FastAPI + MySQL + React/Vite/Tailwind).

This repository starts from the approved UI and the implementation plan. The
backend does not exist yet; it is built phase by phase following the plan.

- UI: `frontend/` (demo data in `frontend/src/data/dashboardData.js`)
- Spec: `docs/PROJECT_SPEC.md`
- Plan and API contract: `docs/FULL_IMPLEMENTATION_PLAN.md`
- **Team workflow, SCRUM ownership, how to commit/push: `docs/TEAM_WORKFLOW.md`**

## Run the UI

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Run the API (SCRUM-1 / SCRUM-2)

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env                 # set SECRET_KEY (32+ chars)
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python ../scripts/seed.py      # demo users, password from SEED_PASSWORD (default Demo12345)
../.venv/bin/uvicorn app.main:app --reload  # http://localhost:8000/docs
../.venv/bin/python -m pytest app/tests -q
```

Seeded logins (all use the seed password): `ngo@example.com` (verified NGO admin),
`admin@example.com` (platform admin), `volunteer1@example.com`, `donor1@example.com`,
`beneficiary1@example.com`. Task list: `docs/SCRUM_TASKS.md`.
