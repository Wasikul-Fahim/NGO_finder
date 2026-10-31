from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import BeneficiaryStatus, Role, VerificationStatus


class User(TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[Role] = enum_column(Role, index=True)
    location: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    volunteer: Mapped["Volunteer | None"] = relationship(back_populates="user", uselist=False)
    ngo: Mapped["NGO | None"] = relationship(back_populates="user", uselist=False)


class Volunteer(TimestampMixin, Base):
    __tablename__ = "volunteers"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[dict] = mapped_column(JSON, default=dict)
    experience: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="volunteer")


class NGO(TimestampMixin, Base):
    __tablename__ = "ngos"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ngo_name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(300))
    contact: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[VerificationStatus] = enum_column(
        VerificationStatus, default=VerificationStatus.PENDING, index=True
    )

    user: Mapped[User] = relationship(back_populates="ngo")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="ngo")  # noqa: F821


class Beneficiary(TimestampMixin, Base):
    __tablename__ = "beneficiaries"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    required_assistance: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BeneficiaryStatus] = enum_column(BeneficiaryStatus, default=BeneficiaryStatus.PENDING)


class RefreshToken(TimestampMixin, Base):
    """Only the SHA-256 of the opaque token is stored. `family_id` ties a rotation chain together."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replaced_by_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_tokens.id"))
    user_agent: Mapped[str | None] = mapped_column(String(255))
