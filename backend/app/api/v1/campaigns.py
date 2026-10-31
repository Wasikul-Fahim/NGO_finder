from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, OptionalUser, VerifiedNgo
from app.core.errors import AppError, conflict
from app.models import Campaign, CampaignStatus, NotificationType
from app.schemas.campaign import (
    CampaignCreate,
    CampaignOut,
    CampaignStatusChange,
    CampaignUpdate,
)
from app.schemas.common import Page
from app.services import campaigns as svc
from app.services import notifications
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def to_out(c: Campaign) -> CampaignOut:
    return CampaignOut(
        id=c.id, ngo_id=c.ngo_id, ngo_name=c.ngo.ngo_name, title=c.title, description=c.description,
        location=c.location, start_date=c.start_date, end_date=c.end_date, status=c.status,
        required_volunteers=c.required_volunteers, required_resources=c.required_resources or [],
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.get("", response_model=Page[CampaignOut])
def list_campaigns(
    user: OptionalUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: CampaignStatus | None = None,
    location: Annotated[str | None, Query(max_length=120)] = None,
    ngo_id: int | None = None,
    mine: bool = False,
):
    stmt = select(Campaign).options(joinedload(Campaign.ngo))
    stmt = svc.restrict_visible(stmt, db, user)
    if mine:
        own = svc.user_ngo_id(db, user)
        if own is None:
            raise AppError(403, "FORBIDDEN", "Only NGO admins have their own campaigns.")
        stmt = stmt.where(Campaign.ngo_id == own)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Campaign.title.ilike(like), Campaign.description.ilike(like)))
    if status:
        stmt = stmt.where(Campaign.status == status)
    if location:
        stmt = stmt.where(Campaign.location.ilike(f"%{location.strip()}%"))
    if ngo_id:
        stmt = stmt.where(Campaign.ngo_id == ngo_id)
    stmt = stmt.order_by(Campaign.start_date.desc(), Campaign.id.desc())
    return paginate(db, stmt, params, to_out)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, user: OptionalUser, db: DbSession):
    return to_out(svc.get_visible_campaign(db, campaign_id, user))


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(data: CampaignCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    campaign = Campaign(
        ngo_id=ngo.id,
        status=CampaignStatus.DRAFT,
        **data.model_dump(exclude={"required_resources"}),
        required_resources=[r.model_dump() for r in data.required_resources],
    )
    db.add(campaign)
    db.flush()
    log_action(db, user, "CREATE_CAMPAIGN", "Campaign", campaign.id, {"title": campaign.title})
    db.commit()
    return to_out(campaign)


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int, data: CampaignUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    campaign = svc.get_owned_campaign(db, campaign_id, ngo)
    if campaign.status in svc.LOCKED_STATUSES:
        raise conflict(f"A {campaign.status.value.lower()} campaign can no longer be edited.")
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "start_date", "end_date", "required_volunteers", "required_resources"):
        if required in changes and changes[required] is None:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {required: "This field cannot be empty."})
    start = changes.get("start_date", campaign.start_date)
    end = changes.get("end_date", campaign.end_date)
    if end < start:
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {"end_date": "End date must be on or after the start date."})
    if "required_resources" in changes:
        changes["required_resources"] = [r.model_dump() for r in data.required_resources or []]
    for field, value in changes.items():
        setattr(campaign, field, value)
    log_action(db, user, "UPDATE_CAMPAIGN", "Campaign", campaign.id, {"fields": sorted(changes)})
    db.commit()
    return to_out(campaign)


@router.post("/{campaign_id}/status", response_model=CampaignOut)
def change_status(
    campaign_id: int, data: CampaignStatusChange, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    campaign = svc.get_owned_campaign(db, campaign_id, ngo)
    svc.ensure_transition(campaign.status, data.status)
    previous = campaign.status
    campaign.status = data.status
    log_action(
        db, user, "CHANGE_CAMPAIGN_STATUS", "Campaign", campaign.id,
        {"from": previous.value, "to": data.status.value},
    )
    audience = notifications.volunteer_user_ids(db, ngo.id) | notifications.donor_user_ids(db, ngo.id, campaign.id)
    notify(db, audience, title="Campaign update",
           message=f'"{campaign.title}" is now {data.status.value.lower()}.',
           type=NotificationType.CAMPAIGN_UPDATE, link="/campaigns",
           dedupe_key=f"campaign:{campaign.id}:{data.status.value}")
    db.commit()
    return to_out(campaign)


@router.delete("/{campaign_id}", response_model=CampaignOut)
def archive_campaign(campaign_id: int, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    """Campaigns are archived, never hard-deleted, so history and donations stay intact."""
    campaign = svc.get_owned_campaign(db, campaign_id, ngo)
    svc.ensure_transition(campaign.status, CampaignStatus.ARCHIVED)
    previous = campaign.status
    campaign.status = CampaignStatus.ARCHIVED
    log_action(
        db, user, "ARCHIVE_CAMPAIGN", "Campaign", campaign.id, {"from": previous.value}
    )
    db.commit()
    return to_out(campaign)
