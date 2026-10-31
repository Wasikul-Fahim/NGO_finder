import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import BACKEND_DIR, get_settings
from app.core.errors import register_error_handlers
from app.ws.notifications import router as ws_router

settings = get_settings()
logger = logging.getLogger(__name__)


def migrate_local_database() -> None:
    """Local SQLite convenience: bring the schema up to date on startup (a no-op when current)."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.db_url.startswith("sqlite") and ":memory:" not in settings.db_url \
            and settings.db_url != "sqlite://":
        try:
            migrate_local_database()
        except Exception:
            logger.exception("Automatic database migration failed")
    yield

LOCAL_DEV_ORIGIN = r"^http://(localhost|127\.0\.0\.1):\d+$"

app = FastAPI(title="VolunteerSync API", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=LOCAL_DEV_ORIGIN if settings.cors_allow_local_dev_ports else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router, prefix="/api/v1")
# The API report documents paths as /api/...; serve the same routes there too (hidden from the docs page).
app.include_router(api_router, prefix="/api", include_in_schema=False)
_logos = settings.upload_path / "logos"
_logos.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/logos", StaticFiles(directory=_logos), name="logos")
app.include_router(ws_router)
