from datetime import date, datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import ApplicationStatus, TaskStatus

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def _clean_tags(values: list[str]) -> list[str]:
    seen, out = set(), []
    for v in values:
        v = v.strip()
        if not v:
            continue
        if len(v) > 50:
            raise ValueError("Each item must be at most 50 characters.")
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _clean_days(values: list[str]) -> list[str]:
    days = []
    for v in values:
        d = v.strip().upper()[:3]
        if d not in DAYS:
            raise ValueError(f"Days must be one of: {', '.join(DAYS)}.")
        if d not in days:
            days.append(d)
    return days


Tags = Annotated[list[str], Field(max_length=30), AfterValidator(_clean_tags)]
Days = Annotated[list[str], Field(max_length=7), AfterValidator(_clean_days)]


def _strip_required(v: str | None) -> str | None:
    if v is not None:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
    return v


# ---- volunteer profile -------------------------------------------------

class VolunteerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str | None
    skills: list[str]
    interests: list[str]
    availability: list[str]
    experience: str | None


class VolunteerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: Tags | None = None
    interests: Tags | None = None
    availability: Days | None = None
    experience: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=120)


# ---- opportunities -----------------------------------------------------

class OpportunityBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=120)
    required_skills: Tags = Field(default_factory=list)
    interests: Tags = Field(default_factory=list)
    availability: Days = Field(default_factory=list)
    campaign_id: int | None = None

    _title = field_validator("title")(_strip_required)


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=120)
    required_skills: Tags | None = None
    interests: Tags | None = None
    availability: Days | None = None
    campaign_id: int | None = None
    is_active: bool | None = None

    _title = field_validator("title")(_strip_required)


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ngo_id: int
    ngo_name: str
    campaign_id: int | None
    campaign_title: str | None
    title: str
    description: str | None
    location: str | None
    required_skills: list[str]
    interests: list[str]
    availability: list[str]
    is_active: bool
    created_at: datetime


class MatchOut(BaseModel):
    score: float
    percentage: int
    breakdown: dict[str, float]
    reasons: list[str]


class RecommendedOut(BaseModel):
    opportunity: OpportunityOut
    match: MatchOut
    has_applied: bool


# ---- applications ------------------------------------------------------

class ApplicationOut(BaseModel):
    id: int
    opportunity_id: int
    opportunity_title: str
    ngo_name: str
    volunteer_id: int
    volunteer_name: str
    volunteer_location: str | None
    volunteer_skills: list[str]
    # Only filled in for the NGO that owns the opportunity: applying shares contact details with it.
    volunteer_email: str | None = None
    volunteer_phone: str | None = None
    status: ApplicationStatus
    application_date: datetime
    review_note: str | None


class ApplicationMessage(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Write a message first.")
        return v


class ApplicationReview(BaseModel):
    status: ApplicationStatus
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _not_submitted(self) -> Self:
        if self.status == ApplicationStatus.SUBMITTED:
            raise ValueError("Cannot move an application back to SUBMITTED.")
        return self


# ---- tasks -------------------------------------------------------------

class TaskCreate(BaseModel):
    campaign_id: int
    opportunity_id: int | None = None
    volunteer_id: int | None = None
    task_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None

    _name = field_validator("task_name")(_strip_required)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None

    _name = field_validator("task_name")(_strip_required)


class TaskAssign(BaseModel):
    volunteer_id: int


class TaskStatusChange(BaseModel):
    status: TaskStatus


class TaskOut(BaseModel):
    id: int
    campaign_id: int
    campaign_title: str
    opportunity_id: int | None
    volunteer_id: int | None
    volunteer_name: str | None
    task_name: str
    description: str | None
    deadline: date | None
    status: TaskStatus
    created_at: datetime
