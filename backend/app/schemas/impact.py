from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParticipationCreate(BaseModel):
    event_id: int
    volunteer_id: int
    attendance: bool = True
    hours: Decimal = Field(default=Decimal(0), ge=0, le=24, decimal_places=2)

    @model_validator(mode="after")
    def _absent_has_no_hours(self) -> Self:
        if not self.attendance and self.hours > 0:
            raise ValueError("An absent volunteer cannot have hours.")
        return self


class ParticipationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attendance: bool | None = None
    hours: Decimal | None = Field(default=None, ge=0, le=24, decimal_places=2)


class ParticipationOut(BaseModel):
    id: int
    event_id: int
    event_name: str
    campaign_title: str
    volunteer_id: int
    volunteer_name: str
    attendance: bool
    hours: float
    participation_date: date


class MonthlyHours(BaseModel):
    month: str
    hours: float


class ContributionOut(BaseModel):
    total_hours: float
    events_attended: int
    tasks_completed: int
    tasks_total: int
    ngos_supported: int = 0
    people_reached: int = 0  # beneficiaries enrolled in the campaigns the volunteer took part in
    monthly_hours: list[MonthlyHours]
    history: list[ParticipationOut]


class PerformanceRow(BaseModel):
    rank: int
    volunteer_id: int
    volunteer_name: str
    location: str | None
    total_hours: float
    events_attended: int
    tasks_completed: int


class CampaignReportRow(BaseModel):
    campaign_id: int
    campaign_title: str
    ngo_name: str
    status: str
    is_emergency: bool
    required_volunteers: int
    accepted_volunteers: int
    events: int
    volunteer_hours: float
    money_received: float
    donation_goal: float | None
    donation_progress: float | None
    resources_total: int
    resources_distributed: int


class ResourceUtilizationRow(BaseModel):
    resource_id: int
    campaign_id: int
    campaign_title: str
    name: str
    unit: str | None
    quantity_total: int
    quantity_allocated: int
    quantity_remaining: int
    utilization_percent: float
