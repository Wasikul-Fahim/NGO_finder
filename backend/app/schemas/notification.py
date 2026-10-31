from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import NotificationPriority, NotificationStatus, NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    status: NotificationStatus
    link: str | None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
    high_priority_unread: int


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    audience: Literal["VOLUNTEERS", "DONORS", "ALL"] = "ALL"
    priority: Literal["NORMAL", "HIGH"] = "NORMAL"
    campaign_id: int | None = None

    @field_validator("title", "message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
        return v


class AnnouncementResult(BaseModel):
    recipients: int
    audience_size: int
    emergency: bool
