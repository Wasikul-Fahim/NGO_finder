from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    db_url: str = "sqlite:///./volunteersync.db"
    secret_key: str = "dev-only-change-me-dev-only-change-me"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5173"
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
