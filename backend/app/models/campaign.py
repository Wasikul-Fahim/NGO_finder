from datetime import date, time

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import CampaignStatus
from app.models.user import NGO


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_campaign_dates"),
        CheckConstraint("required_volunteers >= 0", name="ck_campaign_volunteers"),
    )

    ngo_id: Mapped[int] = mapped_column(ForeignKey("ngos.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[CampaignStatus] = enum_column(CampaignStatus, default=CampaignStatus.DRAFT, index=True)
    required_volunteers: Mapped[int] = mapped_column(Integer, default=0)
    required_resources: Mapped[list] = mapped_column(JSON, default=list)

    ngo: Mapped[NGO] = relationship(back_populates="campaigns")
    events: Mapped[list["Event"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    event_name: Mapped[str] = mapped_column(String(200), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    event_time: Mapped[time | None] = mapped_column(Time)
    location: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    campaign: Mapped[Campaign] = relationship(back_populates="events")
