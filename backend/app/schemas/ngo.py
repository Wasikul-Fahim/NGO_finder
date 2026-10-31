from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import VerificationStatus
from app.schemas.auth import normalize_phone


class NgoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ngo_name: str
    description: str | None
    address: str | None
    contact: str | None
    contact_number: str | None = None
    registration_info: str | None = None
    logo_url: str | None = None
    verification_status: VerificationStatus
    verification_remarks: str | None = None
    created_at: datetime


class NgoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ngo_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, max_length=300)
    contact: str | None = Field(default=None, max_length=120)
    contact_number: str | None = Field(default=None, max_length=30)
    registration_info: str | None = Field(default=None, max_length=5000)

    _phone = field_validator("contact_number")(normalize_phone)


class NgoVerify(BaseModel):
    status: Literal["VERIFIED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)
    remarks: str | None = Field(default=None, max_length=500)  # the report calls the reason "admin remarks"

    @model_validator(mode="after")
    def _merge(self) -> Self:
        self.remarks = self.remarks or self.reason
        return self
