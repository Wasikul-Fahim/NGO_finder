from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VerificationStatus


class NgoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ngo_name: str
    description: str | None
    address: str | None
    contact: str | None
    verification_status: VerificationStatus
    created_at: datetime


class NgoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ngo_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, max_length=300)
    contact: str | None = Field(default=None, max_length=120)


class NgoVerify(BaseModel):
    status: Literal["VERIFIED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)
