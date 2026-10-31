from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CampaignStatus


class ResourceNeed(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)
    unit: str | None = Field(default=None, max_length=30)


def _strip_required(v: str | None) -> str | None:
    if v is not None:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
    return v


class CampaignBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=120)
    start_date: date
    end_date: date
    required_volunteers: int = Field(default=0, ge=0, le=100000)
    required_resources: list[ResourceNeed] = Field(default_factory=list, max_length=50)
    donation_goal: Decimal | None = Field(default=None, ge=0, le=Decimal(1000000000), decimal_places=2)
    is_emergency: bool = False

    _title = field_validator("title")(_strip_required)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date.")
        return self


class CampaignCreate(CampaignBase):
    # A new campaign may be saved as a draft or published straight away.
    status: Literal["DRAFT", "ACTIVE"] = "DRAFT"


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    required_volunteers: int | None = Field(default=None, ge=0, le=100000)
    required_resources: list[ResourceNeed] | None = Field(default=None, max_length=50)
    donation_goal: Decimal | None = Field(default=None, ge=0, le=Decimal(1000000000), decimal_places=2)
    is_emergency: bool | None = None

    _title = field_validator("title")(_strip_required)


class CampaignStatusChange(BaseModel):
    status: CampaignStatus


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ngo_id: int
    ngo_name: str
    title: str
    description: str | None
    location: str | None
    start_date: date
    end_date: date
    status: CampaignStatus
    required_volunteers: int
    required_resources: list[ResourceNeed]
    donation_goal: float | None = None
    donations_received: float = 0
    donation_progress: float | None = None  # percent of the goal received, when a goal is set
    is_emergency: bool = False
    created_at: datetime
    updated_at: datetime


class EventBase(BaseModel):
    event_name: str = Field(min_length=1, max_length=200)
    event_date: date
    event_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    _name = field_validator("event_name")(_strip_required)


class EventCreate(EventBase):
    campaign_id: int


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_name: str | None = Field(default=None, min_length=1, max_length=200)
    event_date: date | None = None
    event_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    _name = field_validator("event_name")(_strip_required)


class AssignmentOut(BaseModel):
    volunteer_id: int
    volunteer_name: str
    assigned_by: str


class AssignmentCreate(BaseModel):
    volunteer_id: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    campaign_title: str
    event_name: str
    event_date: date
    event_time: time | None
    location: str | None
    description: str | None
    created_at: datetime
    joined: bool = False  # the signed-in volunteer is assigned to / has joined this event
