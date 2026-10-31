from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, forbidden, not_found
from app.models import (
    Campaign,
    CampaignStatus,
    Donation,
    DonationStatus,
    DonationType,
    Role,
    User,
)
from app.models.user import NGO

PUBLIC_STATUSES = (CampaignStatus.ACTIVE, CampaignStatus.COMPLETED)

ALLOWED_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.ACTIVE, CampaignStatus.ARCHIVED},
    CampaignStatus.ACTIVE: {CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED},
    CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
    CampaignStatus.ARCHIVED: set(),
}
LOCKED_STATUSES = (CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED)


def user_ngo_id(db: Session, user: User | None) -> int | None:
    if user is None or user.role != Role.NGO_ADMIN:
        return None
    return db.query(NGO.id).filter(NGO.user_id == user.id).scalar()


def restrict_visible(stmt: Select, db: Session, user: User | None) -> Select:
    """Public sees ACTIVE/COMPLETED; an NGO admin also sees all of their own; platform admin sees all."""
    if user is not None and user.role == Role.PLATFORM_ADMIN:
        return stmt
    clause = Campaign.status.in_(PUBLIC_STATUSES)
    ngo_id = user_ngo_id(db, user)
    if ngo_id is not None:
        clause = or_(clause, Campaign.ngo_id == ngo_id)
    return stmt.where(clause)


def get_visible_campaign(db: Session, campaign_id: int, user: User | None) -> Campaign:
    campaign = db.scalar(restrict_visible(select(Campaign).where(Campaign.id == campaign_id), db, user))
    if campaign is None:
        raise not_found("Campaign")
    return campaign


def get_owned_campaign(db: Session, campaign_id: int, ngo: NGO) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise not_found("Campaign")
    if campaign.ngo_id != ngo.id:
        raise forbidden("This campaign belongs to another NGO.")
    return campaign


def ensure_transition(current: CampaignStatus, target: CampaignStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise AppError(
            409, "INVALID_TRANSITION", f"Cannot move a campaign from {current.value} to {target.value}."
        )


def received_by_campaign(db: Session, campaign_ids: list[int]) -> dict[int, float]:
    """Confirmed money donations per campaign (what the donation-progress bar is based on)."""
    if not campaign_ids:
        return {}
    rows = db.execute(
        select(Donation.campaign_id, func.coalesce(func.sum(Donation.amount), 0))
        .where(Donation.campaign_id.in_(campaign_ids), Donation.status == DonationStatus.RECEIVED,
               Donation.donation_type == DonationType.MONEY)
        .group_by(Donation.campaign_id))
    return {cid: float(total) for cid, total in rows}
