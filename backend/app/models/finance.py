from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column
from app.models.campaign import Campaign
from app.models.enums import DonationStatus, DonationType, SupportStatus
from app.models.user import NGO, Beneficiary, User


class Donation(TimestampMixin, Base):
    """Bookkeeping only. No card numbers, bank details or payment-processor payloads are stored."""

    __tablename__ = "donations"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_donation_amount"),)

    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ngo_id: Mapped[int] = mapped_column(ForeignKey("ngos.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    donation_type: Mapped[DonationType] = enum_column(DonationType, index=True)
    donation_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[DonationStatus] = enum_column(DonationStatus, default=DonationStatus.PENDING, index=True)
    note: Mapped[str | None] = mapped_column(Text)

    donor: Mapped[User] = relationship()
    ngo: Mapped[NGO] = relationship()
    campaign: Mapped[Campaign | None] = relationship()


class Resource(TimestampMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("quantity_total >= 0", name="ck_resource_total"),
        CheckConstraint("quantity_allocated >= 0", name="ck_resource_allocated"),
        CheckConstraint("quantity_allocated <= quantity_total", name="ck_resource_within_total"),
    )

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    quantity_total: Mapped[int] = mapped_column(Integer, default=0)
    quantity_allocated: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str | None] = mapped_column(String(30))

    campaign: Mapped[Campaign] = relationship()


class CampaignBeneficiary(TimestampMixin, Base):
    __tablename__ = "campaign_beneficiaries"
    __table_args__ = (
        UniqueConstraint("campaign_id", "beneficiary_id", name="uq_campaign_beneficiary"),
    )

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiaries.id", ondelete="CASCADE"), index=True
    )
    support_status: Mapped[SupportStatus] = enum_column(SupportStatus, default=SupportStatus.PENDING)

    campaign: Mapped[Campaign] = relationship()
    beneficiary: Mapped[Beneficiary] = relationship()


class ResourceDistribution(TimestampMixin, Base):
    __tablename__ = "resource_distributions"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_distribution_quantity"),)

    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), index=True)
    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiaries.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    distribution_date: Mapped[date] = mapped_column(Date)

    resource: Mapped[Resource] = relationship()
    beneficiary: Mapped[Beneficiary] = relationship()
