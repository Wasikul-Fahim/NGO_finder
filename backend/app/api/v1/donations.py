from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentNgo, CurrentUser, DbSession, VerifiedNgo, require_roles
from app.core.errors import AppError, forbidden, not_found
from app.models import (
    Campaign,
    CampaignStatus,
    Donation,
    DonationStatus,
    DonationType,
    NotificationType,
    Resource,
    Role,
    User,
    VerificationStatus,
)
from app.schemas.common import Page
from app.schemas.finance import (
    DonationCreate,
    DonationOut,
    DonationStatusChange,
    ResourceOut,
    UtilizationOut,
)
from app.services.audit import log_action
from app.services.campaigns import user_ngo_id
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["donations"])
DonorUser = Annotated[User, Depends(require_roles(Role.DONOR))]


def to_out(d: Donation) -> DonationOut:
    return DonationOut(
        id=d.id, donor_name=d.donor.name, ngo_id=d.ngo_id, ngo_name=d.ngo.ngo_name,
        campaign_id=d.campaign_id, campaign_title=d.campaign.title if d.campaign else None,
        amount=float(d.amount), donation_type=d.donation_type, donation_date=d.donation_date,
        status=d.status, note=d.note, created_at=d.created_at,
    )


def _base():
    return select(Donation).options(
        joinedload(Donation.donor), joinedload(Donation.ngo), joinedload(Donation.campaign)
    )


def resource_out(r: Resource) -> ResourceOut:
    return ResourceOut(
        id=r.id, campaign_id=r.campaign_id, name=r.name, quantity_total=r.quantity_total,
        quantity_allocated=r.quantity_allocated,
        quantity_remaining=r.quantity_total - r.quantity_allocated, unit=r.unit,
    )


@router.post("/donations", response_model=DonationOut, status_code=201)
def donate(data: DonationCreate, donor: DonorUser, db: DbSession):
    campaign = db.get(Campaign, data.campaign_id)
    if campaign is None or campaign.ngo.verification_status != VerificationStatus.VERIFIED \
            or campaign.status not in (CampaignStatus.ACTIVE, CampaignStatus.COMPLETED):
        raise not_found("Campaign")
    if campaign.status != CampaignStatus.ACTIVE:
        raise AppError(409, "CONFLICT", "This campaign is no longer accepting donations.")
    d = Donation(
        donor_id=donor.id, ngo_id=campaign.ngo_id, campaign_id=campaign.id, amount=data.amount,
        donation_type=data.donation_type, donation_date=date.today(), note=data.note,
        status=DonationStatus.PENDING,
    )
    db.add(d)
    db.flush()
    notify(db, [campaign.ngo.user_id], title="New donation pledge",
           message=f"{donor.name} pledged a {d.donation_type.value.lower()} donation to {campaign.title}.",
           type=NotificationType.DONATION_UPDATE, link="/admin/donations", dedupe_key=f"donation-new:{d.id}")
    db.commit()
    return to_out(db.scalar(_base().where(Donation.id == d.id)))


@router.get("/donations/me", response_model=Page[DonationOut])
def my_donations(
    donor: DonorUser, db: DbSession, params: Annotated[PageParams, Depends()],
    status: DonationStatus | None = None, donation_type: DonationType | None = None,
):
    stmt = _base().where(Donation.donor_id == donor.id)
    if status:
        stmt = stmt.where(Donation.status == status)
    if donation_type:
        stmt = stmt.where(Donation.donation_type == donation_type)
    return paginate(db, stmt.order_by(Donation.created_at.desc(), Donation.id.desc()), params, to_out)


@router.get("/donations", response_model=Page[DonationOut])
def ngo_donations(
    ngo: CurrentNgo, db: DbSession, params: Annotated[PageParams, Depends()],
    status: DonationStatus | None = None, campaign_id: int | None = None,
    donation_type: DonationType | None = None,
):
    stmt = _base().where(Donation.ngo_id == ngo.id)
    if status:
        stmt = stmt.where(Donation.status == status)
    if campaign_id:
        stmt = stmt.where(Donation.campaign_id == campaign_id)
    if donation_type:
        stmt = stmt.where(Donation.donation_type == donation_type)
    return paginate(db, stmt.order_by(Donation.created_at.desc(), Donation.id.desc()), params, to_out)


@router.patch("/donations/{donation_id}/status", response_model=DonationOut)
def change_status(
    donation_id: int, data: DonationStatusChange, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    d = db.scalar(_base().where(Donation.id == donation_id))
    if d is None:
        raise not_found("Donation")
    if d.ngo_id != ngo.id:
        raise forbidden("This donation belongs to another NGO.")
    if d.status != DonationStatus.PENDING:
        raise AppError(409, "INVALID_TRANSITION",
                       f"Cannot move a donation from {d.status.value} to {data.status}.")
    previous = d.status
    d.status = DonationStatus(data.status)
    log_action(db, user, f"DONATION_{data.status}", "Donation", d.id,
               {"from": previous.value, "to": data.status, "amount": float(d.amount),
                "type": d.donation_type.value})
    notify(db, [d.donor_id], title="Donation update",
           message=f"Your donation to {d.campaign.title if d.campaign else d.ngo.ngo_name} was "
                   f"{data.status.lower()}.",
           type=NotificationType.DONATION_UPDATE, link="/donations",
           dedupe_key=f"donation:{d.id}:{data.status}")
    db.commit()
    return to_out(d)


@router.get("/campaigns/{campaign_id}/utilization", response_model=UtilizationOut)
def utilization(campaign_id: int, user: CurrentUser, db: DbSession):
    """Aggregate view of how a campaign's resources are used. No beneficiary data in here."""
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise not_found("Campaign")
    allowed = user.role == Role.PLATFORM_ADMIN or (
        user.role == Role.NGO_ADMIN and user_ngo_id(db, user) == campaign.ngo_id
    )
    if not allowed and user.role == Role.DONOR:
        allowed = db.scalar(select(Donation.id).where(
            Donation.donor_id == user.id, Donation.campaign_id == campaign_id,
            Donation.status == DonationStatus.RECEIVED,
        ).limit(1)) is not None
    if not allowed:
        raise forbidden("Utilization is shown to donors whose donation to this campaign was received.")
    money, count = db.execute(
        select(func.coalesce(func.sum(Donation.amount), 0), func.count()).where(
            Donation.campaign_id == campaign_id, Donation.status == DonationStatus.RECEIVED,
            Donation.donation_type == DonationType.MONEY,
        )
    ).one()
    resources = db.scalars(select(Resource).where(Resource.campaign_id == campaign_id).order_by(Resource.id))
    return UtilizationOut(
        campaign_id=campaign.id, campaign_title=campaign.title, money_received=float(money),
        donation_count=count, resources=[resource_out(r) for r in resources],
    )
