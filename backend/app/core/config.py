from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    db_url: str = "sqlite:///./volunteersync.db"
    secret_key: str = "dev-only-change-me-dev-only-change-me"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Local development: also accept http://localhost:<any port> and http://127.0.0.1:<any port>
    # (Vite moves to 5174+ when 5173 is busy). Set to false in production.
    cors_allow_local_dev_ports: bool = True
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"

    # Brute-force protection for /auth/login (failed attempts per window).
    login_max_attempts: int = 5
    login_window_seconds: int = 300

    matching_skills_weight: float = 0.45
    matching_interest_weight: float = 0.20
    matching_location_weight: float = 0.20
    matching_availability_weight: float = 0.15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _check(self) -> "Settings":
        # A relative SQLite path would depend on the folder the server was started from, silently
        # giving a different (empty) database. Anchor it to the backend folder instead.
        prefix = "sqlite:///"
        rest = self.db_url[len(prefix):] if self.db_url.startswith(prefix) else None
        if rest and not rest.startswith(("/", ":")) and not Path(rest).is_absolute():
            self.db_url = f"{prefix}{(BACKEND_DIR / rest).as_posix()}"
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        total = (
            self.matching_skills_weight
            + self.matching_interest_weight
            + self.matching_location_weight
            + self.matching_availability_weight
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError("Matching weights must sum to 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
