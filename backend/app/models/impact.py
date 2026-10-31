from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.campaign import Event
from app.models.user import Volunteer


class Participation(TimestampMixin, Base):
    __tablename__ = "participations"
    __table_args__ = (
        UniqueConstraint("volunteer_id", "event_id", name="uq_participation_volunteer_event"),
        CheckConstraint("hours >= 0 AND hours <= 24", name="ck_participation_hours"),
    )

    volunteer_id: Mapped[int] = mapped_column(ForeignKey("volunteers.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    attendance: Mapped[bool] = mapped_column(Boolean, default=True)
    participation_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))

    volunteer: Mapped[Volunteer] = relationship()
    event: Mapped[Event] = relationship()
