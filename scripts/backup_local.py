"""Back up the local SQLite database (and uploaded logos) into backend/backups/<timestamp>/.

    python scripts/backup_local.py              # make a backup
    python scripts/backup_local.py --restore backend/backups/<timestamp>   # restore one (stop the API first)

Uses SQLite's online-backup API, so it is safe to run while the site is running.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import BACKEND_DIR, get_settings


def sqlite_file() -> Path:
    url = get_settings().db_url
    if not url.startswith("sqlite:///"):
        sys.exit("This script only backs up the local SQLite database. For MySQL use mysqldump.")
    return Path(url.removeprefix("sqlite:///"))


def backup() -> Path:
    src = sqlite_file()
    if not src.exists():
        sys.exit(f"No database found at {src}")
    dest = BACKEND_DIR / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    dest.mkdir(parents=True)
    with sqlite3.connect(src) as live, sqlite3.connect(dest / src.name) as copy:
        live.backup(copy)
    uploads = get_settings().upload_path
    if uploads.exists():
        shutil.copytree(uploads, dest / "uploads")
    return dest


def restore(folder: Path) -> None:
    src = sqlite_file()
    saved = folder / src.name
    if not saved.exists():
        sys.exit(f"{saved} not found - pass a folder created by this script.")
    src.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved, src)
    if (folder / "uploads").exists():
        shutil.copytree(folder / "uploads", get_settings().upload_path, dirs_exist_ok=True)
    print(f"Restored {src} from {folder}. Restart the API.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", type=Path, help="backup folder to restore")
    args = parser.parse_args()
    if args.restore:
        restore(args.restore)
    else:
        print("Backup written to", backup())
