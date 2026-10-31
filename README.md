# VolunteerSync

Volunteer and NGO management platform (FastAPI + MySQL + React/Vite/Tailwind).

This repository starts from the approved UI and the implementation plan. The
backend does not exist yet; it is built phase by phase following the plan.

- UI: `frontend/` (demo data in `frontend/src/data/dashboardData.js`)
- Spec: `docs/PROJECT_SPEC.md`
- Plan and API contract: `docs/FULL_IMPLEMENTATION_PLAN.md`
- **Team workflow, SCRUM ownership, how to commit/push: `docs/TEAM_WORKFLOW.md`**

## Run it locally (macOS or Windows, no Docker)

You need **Python 3.11+** and **Node 18+**. The database is a single SQLite file, so there is
nothing else to install.

**macOS / Linux**
```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python scripts/setup_local.py            # creates .env, the database and demo data
# terminal 1 - API on http://localhost:8000 (docs at /docs)
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload
# terminal 2 - website on http://localhost:5173
cd frontend && npm install && npm run dev
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
.venv\Scripts\python scripts\setup_local.py
# terminal 1
cd backend; ..\.venv\Scripts\python -m uvicorn app.main:app --reload
# terminal 2
cd frontend; npm install; npm run dev
```

Open http://localhost:5173 and log in with a seeded account (password `Demo12345`):

| Email | Role |
|---|---|
| `ngo@example.com` | NGO admin (verified) |
| `volunteer1@example.com` | Volunteer (profile filled in, gets ranked matches) |
| `volunteer2@example.com` | Volunteer |
| `donor1@example.com` | Donor |
| `beneficiary1@example.com` | Beneficiary |
| `admin@example.com` | Platform admin |

Re-running `setup_local.py` is safe (it never duplicates data). To start fresh, delete
`backend/volunteersync.db` and run it again.

**Tests:** `cd backend && ../.venv/bin/python -m pytest app/tests -q` (Windows: `..\.venv\Scripts\python -m pytest app\tests -q`).

Task list: `docs/SCRUM_TASKS.md`.
