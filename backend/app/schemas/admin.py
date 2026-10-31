from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import Role, VerificationStatus
from app.schemas.auth import validate_password_strength


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str | None
    action_type: str
    entity_type: str
    entity_id: int | None
    details: dict[str, Any]
    timestamp: datetime


class AdminUserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: Role
    location: str | None
    is_active: bool
    is_verified: bool
    ngo_id: int | None = None
    ngo_name: str | None = None
    ngo_status: VerificationStatus | None = None
    created_at: datetime


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    is_verified: bool | None = None


class NgoAdminCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str
    ngo_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    verified: bool = False

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("name", "ngo_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
        return v


class PlatformStats(BaseModel):
    users_by_role: dict[str, int]
    active_users: int
    ngos_by_status: dict[str, int]
    campaigns_by_status: dict[str, int]
    opportunities_active: int
    applications_by_status: dict[str, int]
    tasks_by_status: dict[str, int]
    volunteer_hours: float
    donations_received_money: float
    donations_pending: int
    audit_entries: int


class Counter(BaseModel):
    key: str
    label: str
    count: int
    link: str


class UpcomingEvent(BaseModel):
    id: int
    event_name: str
    campaign_title: str
    event_date: str
    location: str | None


class NgoDashboard(BaseModel):
    ngo_name: str
    verification_status: VerificationStatus
    campaigns_by_status: dict[str, int]
    opportunities_active: int
    opportunities_inactive: int
    applications_by_status: dict[str, int]
    tasks_by_status: dict[str, int]
    accepted_volunteers: int
    volunteer_hours: float
    beneficiaries_enrolled: int
    money_received: float
    donations_pending: int
    resources_total: int
    resources_distributed: int
    needs_attention: list[Counter]
    upcoming_events: list[UpcomingEvent]
    recent_activity: list[AuditLogOut]
