from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column, utcnow
from app.models.campaign import Campaign
from app.models.enums import ApplicationStatus, TaskStatus
from app.models.user import NGO, Volunteer


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"

    ngo_id: Mapped[int] = mapped_column(ForeignKey("ngos.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120), index=True)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    ngo: Mapped[NGO] = relationship()
    campaign: Mapped[Campaign | None] = relationship()


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("volunteer_id", "opportunity_id", name="uq_application_volunteer_opportunity"),
    )

    volunteer_id: Mapped[int] = mapped_column(
        ForeignKey("volunteers.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    application_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[ApplicationStatus] = enum_column(
        ApplicationStatus, default=ApplicationStatus.SUBMITTED, index=True
    )
    review_note: Mapped[str | None] = mapped_column(String(500))

    volunteer: Mapped[Volunteer] = relationship()
    opportunity: Mapped[Opportunity] = relationship()


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id", ondelete="SET NULL"), index=True
    )
    volunteer_id: Mapped[int | None] = mapped_column(
        ForeignKey("volunteers.id", ondelete="SET NULL"), index=True
    )
    task_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[TaskStatus] = enum_column(TaskStatus, default=TaskStatus.PENDING, index=True)

    campaign: Mapped[Campaign] = relationship()
    opportunity: Mapped[Opportunity | None] = relationship()
    volunteer: Mapped[Volunteer | None] = relationship()
