from datetime import date, datetime, time
from typing import Self

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

    _title = field_validator("title")(_strip_required)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date.")
        return self


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    required_volunteers: int | None = Field(default=None, ge=0, le=100000)
    required_resources: list[ResourceNeed] | None = Field(default=None, max_length=50)

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
