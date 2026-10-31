# Team Workflow

Three contributors, one repo. Everyone commits and pushes **their own work from
their own GitHub account** so the contribution graph and `git blame` are honest.

## 1. SCRUM ownership (suggested split — edit names and agree as a team)

| Owner | Tickets | Backend area (`backend/app/...`) | Frontend area |
|---|---|---|---|
| Member A — platform | SCRUM-1 Auth & RBAC, SCRUM-10 Admin & Audit, SCRUM-9 Notifications | `core/security`, `api/v1/auth`, `api/v1/admin`, `services/audit`, `ws/` | `pages/Login`, `pages/Register`, `context/`, `routes/` |
| Member B — NGO side | SCRUM-2 NGO/Campaign/Event, SCRUM-11 NGO Management, SCRUM-8 Donations | `api/v1/ngos`, `campaigns`, `events`, `donations` | `pages/Campaigns`, `pages/Donations` |
| Member C — volunteer side | SCRUM-5 Opportunities & Matching, SCRUM-6 Applications & Tasks, SCRUM-7 Attendance & Reporting | `api/v1/opportunities`, `applications`, `tasks`, `attendance`, `services/matching` | `pages/Opportunities`, `pages/Tasks`, `pages/Impact` |

Keep to your own folders/files to avoid merge conflicts. Shared files
(`models/__init__.py`, `api/v1/router.py`, Alembic revisions, `package.json`)
are edited in small PRs and merged quickly. Phase 1 (database models and
migrations) is a prerequisite for everyone: agree who builds it first.

## 2. One-time setup (each person, on their own machine)

1. Accept the GitHub invitation (repo owner: Settings → Collaborators → add the
   other two with Write access).
2. Clone and set **your own** identity for this repo:

   ```bash
   git clone git@github.com:<owner>/<repo>.git
   cd <repo>
   git config user.name  "Your Real Name"
   git config user.email "<email verified on YOUR GitHub account>"
   ```

   The email must be one added under GitHub → Settings → Emails, or your
   `ID+username@users.noreply.github.com` address. Otherwise commits are not
   linked to your profile.
3. Authenticate as yourself (SSH key or `gh auth login`) — never reuse another
   person's login or token.
4. Check before your first commit: `git config user.email` and, after
   committing, `git log -1 --format='%an <%ae>'`.

## 3. Daily flow

```bash
git switch main && git pull
git switch -c scrum-1/login-endpoint        # branch per ticket: scrum-<n>/<short-name>
# ...work...
git add <files>
git commit -m "feat(auth): add login endpoint (SCRUM-1)"
git push -u origin scrum-1/login-endpoint
```

Open a Pull Request into `main`, have a teammate review, then merge (squash or
merge commit — either keeps the author). Recommended: enable branch protection
on `main` (require PR + 1 approval).

Commit style: conventional commits with the ticket id, e.g.
`feat(campaigns): create campaign API (SCRUM-2)`. Commit small and often.

## 4. Rules that keep attribution honest

- Each person commits their own work from their own account/machine.
- Do not set another person's name/email on your commits, and do not push with
  someone else's credentials.
- Two people on one change: add a `Co-authored-by: Name <email>` trailer.
- If you did work locally under the wrong identity, fix **before pushing**:
  `git commit --amend --reset-author --no-edit` (last commit) or
  `git rebase -r <base> --exec 'git commit --amend --reset-author --no-edit'`.
  Never rewrite history on `main` after others have pulled.
- Check the Insights → Contributors page on GitHub after a few merges.

## 5. Definition of done (from the plan)

Tests added for every new user-visible flow, roles enforced in backend
dependencies, invalid state transitions return 409, and checks pass before
merging. See `docs/FULL_IMPLEMENTATION_PLAN.md` → Verification gates.
