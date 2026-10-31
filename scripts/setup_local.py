"""One-step local setup (Windows, macOS, Linux): create the database and load demo data.

    python scripts/setup_local.py

Uses SQLite (a single file, backend/volunteersync.db). No Docker or MySQL needed.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=BACKEND, check=True)


def main() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        text = (ROOT / ".env.example").read_text()
        import secrets

        text = text.replace(
            "SECRET_KEY=change-me-to-a-random-string-of-at-least-32-chars",
            f"SECRET_KEY={secrets.token_urlsafe(48)}",
        )
        env_file.write_text(text)
        print("Created .env with a fresh SECRET_KEY")
    os.environ.setdefault("PYTHONPATH", str(BACKEND))
    print("Applying migrations...")
    run("-m", "alembic", "upgrade", "head")
    print("Seeding demo data...")
    run(str(ROOT / "scripts" / "seed.py"))
    print("\nDone. Next:\n  1) backend:  cd backend && python -m uvicorn app.main:app --reload"
          "\n  2) frontend: cd frontend && npm install && npm run dev")


if __name__ == "__main__":
    main()
