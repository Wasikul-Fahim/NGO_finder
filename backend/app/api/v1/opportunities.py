from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, OptionalUser, VerifiedNgo
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import (
    NGO,
    Application,
    Campaign,
    Opportunity,
    Role,
    VerificationStatus,
)
from app.schemas.common import Page
from app.schemas.opportunity import (
    MatchOut,
    OpportunityCreate,
    OpportunityOut,
    OpportunityUpdate,
    RecommendedOut,
)
from app.services import campaigns as campaign_svc
from app.services import matching
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def to_out(o: Opportunity) -> OpportunityOut:
    return OpportunityOut(
        id=o.id, ngo_id=o.ngo_id, ngo_name=o.ngo.ngo_name, campaign_id=o.campaign_id,
        campaign_title=o.campaign.title if o.campaign else None, title=o.title,
        description=o.description, location=o.location, required_skills=o.required_skills or [],
        interests=o.interests or [], availability=o.availability or [], is_active=o.is_active,
        created_at=o.created_at,
    )


def _base():
    return select(Opportunity).join(Opportunity.ngo).options(
        joinedload(Opportunity.ngo), joinedload(Opportunity.campaign)
    )


def _public(stmt):
    """What anyone may browse: active postings of verified NGOs."""
    return stmt.where(
        Opportunity.is_active.is_(True), NGO.verification_status == VerificationStatus.VERIFIED
    )


def _visible(stmt, db, user):
    if user is not None and user.role == Role.PLATFORM_ADMIN:
        return stmt
    own = campaign_svc.user_ngo_id(db, user)
    public = (Opportunity.is_active.is_(True)) & (NGO.verification_status == VerificationStatus.VERIFIED)
    return stmt.where(or_(public, Opportunity.ngo_id == own) if own is not None else public)


def _check_campaign(db, campaign_id: int | None, ngo) -> None:
    if campaign_id is None:
        return
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.ngo_id != ngo.id:
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {"campaign_id": "Pick one of your own campaigns."})
    if campaign.status in campaign_svc.LOCKED_STATUSES:
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {"campaign_id": "That campaign is closed."})


def _get_owned(db, opportunity_id: int, ngo) -> Opportunity:
    opp = db.scalar(_base().where(Opportunity.id == opportunity_id))
    if opp is None:
        raise not_found("Opportunity")
    if opp.ngo_id != ngo.id:
        raise forbidden("This opportunity belongs to another NGO.")
    return opp


@router.get("/recommended", response_model=list[RecommendedOut])
def recommended(
    user: VolunteerUser, db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 10
):
    vol = get_volunteer(db, user)
    opps = {o.id: o for o in db.scalars(_public(_base())).unique()}
    profile = matching.VolunteerProfile(
        skills=vol.skills or [], interests=vol.interests or [],
        availability=vol.availability or [], location=user.location,
    )
    ranked = matching.rank_opportunities(
        profile,
        [matching.OpportunityProfile(o.id, o.required_skills or [], o.interests or [],
                                     o.availability or [], o.location) for o in opps.values()],
    )[:limit]
    applied = set(db.scalars(select(Application.opportunity_id).where(Application.volunteer_id == vol.id)))
    return [
        RecommendedOut(
            opportunity=to_out(opps[r.opportunity_id]),
            match=MatchOut(score=r.score, percentage=r.percentage, breakdown=r.breakdown, reasons=r.reasons),
            has_applied=r.opportunity_id in applied,
        )
        for r in ranked
    ]


@router.get("", response_model=Page[OpportunityOut])
def list_opportunities(
    user: OptionalUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=100)] = None,
    location: Annotated[str | None, Query(max_length=120)] = None,
    skill: Annotated[str | None, Query(max_length=50)] = None,
    campaign_id: int | None = None,
    ngo_id: int | None = None,
    is_active: bool | None = None,
    mine: bool = False,
    sort: Literal["newest", "title"] = "newest",
):
    stmt = _visible(_base(), db, user)
    if mine:
        own = campaign_svc.user_ngo_id(db, user)
        if own is None:
            raise forbidden("Only NGO admins have their own opportunities.")
        stmt = stmt.where(Opportunity.ngo_id == own)
    if is_active is not None:
        stmt = stmt.where(Opportunity.is_active.is_(is_active))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Opportunity.title.ilike(like), Opportunity.description.ilike(like)))
    if location:
        stmt = stmt.where(Opportunity.location.ilike(f"%{location.strip()}%"))
    if skill:
        stmt = stmt.where(cast(Opportunity.required_skills, String).ilike(f'%"{skill.strip()}"%'))
    if campaign_id:
        stmt = stmt.where(Opportunity.campaign_id == campaign_id)
    if ngo_id:
        stmt = stmt.where(Opportunity.ngo_id == ngo_id)
    stmt = stmt.order_by(
        Opportunity.title, Opportunity.id) if sort == "title" else stmt.order_by(
        Opportunity.created_at.desc(), Opportunity.id.desc())
    return paginate(db, stmt, params, to_out)


@router.get("/{opportunity_id}", response_model=OpportunityOut)
def get_opportunity(opportunity_id: int, user: OptionalUser, db: DbSession):
    opp = db.scalar(_visible(_base(), db, user).where(Opportunity.id == opportunity_id))
    if opp is None:
        raise not_found("Opportunity")
    return to_out(opp)


@router.post("", response_model=OpportunityOut, status_code=201)
def create_opportunity(data: OpportunityCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    _check_campaign(db, data.campaign_id, ngo)
    opp = Opportunity(ngo_id=ngo.id, **data.model_dump())
    db.add(opp)
    db.flush()
    log_action(db, user, "CREATE_OPPORTUNITY", "Opportunity", opp.id, {"title": opp.title})
    db.commit()
    db.refresh(opp)
    return to_out(opp)


@router.patch("/{opportunity_id}", response_model=OpportunityOut)
def update_opportunity(
    opportunity_id: int, data: OpportunityUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    opp = _get_owned(db, opportunity_id, ngo)
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "required_skills", "interests", "availability", "is_active"):
        if required in changes and changes[required] is None:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {required: "This field cannot be empty."})
    if "campaign_id" in changes and changes["campaign_id"] != opp.campaign_id:
        _check_campaign(db, changes.get("campaign_id"), ngo)
    for field, value in changes.items():
        setattr(opp, field, value)
    log_action(db, user, "UPDATE_OPPORTUNITY", "Opportunity", opp.id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(opp)
    return to_out(opp)


@router.delete("/{opportunity_id}", response_model=OpportunityOut)
def deactivate_opportunity(opportunity_id: int, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    """Opportunities are deactivated, not deleted, so applications and tasks keep their history."""
    opp = _get_owned(db, opportunity_id, ngo)
    if not opp.is_active:
        raise conflict("Opportunity is already inactive.")
    opp.is_active = False
    log_action(db, user, "DEACTIVATE_OPPORTUNITY", "Opportunity", opp.id, {})
    db.commit()
    db.refresh(opp)
    return to_out(opp)
