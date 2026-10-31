from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import DonationStatus, DonationType, SupportStatus

MAX_AMOUNT = Decimal(1000000000)


def _strip(v: str | None) -> str | None:
    if v is not None:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
    return v


class DonationCreate(BaseModel):
    # forbid: any stray field (card number, CVV, bank details...) is rejected, never stored.
    model_config = ConfigDict(extra="forbid")

    campaign_id: int
    donation_type: DonationType
    amount: Decimal = Field(default=Decimal(0), ge=0, le=MAX_AMOUNT, decimal_places=2)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _money_needs_amount(self) -> Self:
        if self.donation_type == DonationType.MONEY and self.amount <= 0:
            raise ValueError("Enter an amount greater than zero.")
        return self


class DonationUpdate(BaseModel):
    """An NGO correcting a record (e.g. a mistyped amount). Every change is audit-logged with before/after."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(default=None, ge=0, le=MAX_AMOUNT, decimal_places=2)
    donation_type: DonationType | None = None
    note: str | None = Field(default=None, max_length=1000)


class DonationStatusChange(BaseModel):
    status: Literal["RECEIVED", "REJECTED"]


class DonationOut(BaseModel):
    id: int
    donor_name: str
    ngo_id: int
    ngo_name: str
    campaign_id: int | None
    campaign_title: str | None
    amount: float
    donation_type: DonationType
    donation_date: date
    status: DonationStatus
    note: str | None
    created_at: datetime


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity_total: int = Field(ge=0, le=1_000_000_000)
    unit: str | None = Field(default=None, max_length=30)

    _name = field_validator("name")(_strip)


class ResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity_total: int | None = Field(default=None, ge=0, le=1_000_000_000)
    unit: str | None = Field(default=None, max_length=30)

    _name = field_validator("name")(_strip)


class ResourceOut(BaseModel):
    id: int
    campaign_id: int
    name: str
    quantity_total: int
    quantity_allocated: int
    quantity_remaining: int
    unit: str | None


class DistributionCreate(BaseModel):
    beneficiary_id: int
    quantity: int = Field(ge=1, le=1_000_000_000)
    distribution_date: date | None = None


class DistributionOut(BaseModel):
    id: int
    resource_id: int
    resource_name: str
    beneficiary_id: int
    beneficiary_name: str
    quantity: int
    distribution_date: date


class BeneficiaryEnroll(BaseModel):
    """Either link an already-registered beneficiary by email, or record a new person."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=120)
    contact: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    required_assistance: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _one_or_other(self) -> Self:
        if self.email is None and not (self.name and self.name.strip()):
            raise ValueError("Provide the registered beneficiary's email, or a name for a new record.")
        return self


class SupportUpdate(BaseModel):
    support_status: SupportStatus


class ResourceCreateTop(ResourceCreate):
    campaign_id: int


class BeneficiaryCreateTop(BeneficiaryEnroll):
    campaign_id: int
    support_status: SupportStatus = SupportStatus.PENDING


class BeneficiaryUpdate(BaseModel):
    """`campaign_id` says which of your campaigns' enrolments you are updating."""

    model_config = ConfigDict(extra="forbid")

    campaign_id: int
    name: str | None = Field(default=None, min_length=1, max_length=120)
    contact: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    required_assistance: str | None = Field(default=None, max_length=2000)
    support_status: SupportStatus | None = None


class CampaignBeneficiaryOut(BaseModel):
    campaign_id: int | None = None
    beneficiary_id: int
    name: str
    contact: str | None
    location: str | None
    required_assistance: str | None
    support_status: SupportStatus


class MySupportOut(BaseModel):
    campaign_id: int
    campaign_title: str
    ngo_name: str
    support_status: SupportStatus
    received: list[dict]


class UtilizationOut(BaseModel):
    campaign_id: int
    campaign_title: str
    money_received: float
    donation_count: int
    resources: list[ResourceOut]


class DonationSummaryRow(BaseModel):
    campaign_id: int | None
    campaign_title: str
    money_received: float
    money_pending: float
    donation_count: int
    donor_count: int
    by_type: dict[str, int]
