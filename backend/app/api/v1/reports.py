from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession
from app.core.errors import forbidden
from app.models import (
    Application,
    ApplicationStatus,
    Campaign,
    Donation,
    DonationStatus,
    DonationType,
    Event,
    Opportunity,
    Participation,
    Resource,
    Role,
    Task,
    TaskStatus,
    Volunteer,
)
from app.schemas.common import Page
from app.schemas.finance import DonationSummaryRow
from app.schemas.impact import CampaignReportRow, PerformanceRow, ResourceUtilizationRow
from app.services.campaigns import received_by_campaign, user_ngo_id
from app.services.pagination import PageParams, paginate_list

router = APIRouter(prefix="/reports", tags=["reports"])


def _scope(db, user) -> int | None:
    """NGO admins see their own NGO; platform admins see everything (None = unrestricted)."""
    if user.role == Role.PLATFORM_ADMIN:
        return None
    ngo_id = user_ngo_id(db, user)
    if ngo_id is None:
        raise forbidden("Reports are available to NGO and platform admins.")
    return ngo_id


@router.get("/volunteer-performance", response_model=Page[PerformanceRow])
def volunteer_performance(
    user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()],
    campaign_id: int | None = None,
):
    ngo_id = _scope(db, user)

    hours_stmt = (
        select(Participation.volunteer_id, func.sum(Participation.hours), func.count())
        .join(Event, Participation.event_id == Event.id)
        .join(Campaign, Event.campaign_id == Campaign.id)
        .where(Participation.attendance.is_(True))
        .group_by(Participation.volunteer_id)
    )
    tasks_stmt = (
        select(Task.volunteer_id, func.count())
        .join(Campaign, Task.campaign_id == Campaign.id)
        .where(Task.status == TaskStatus.COMPLETED, Task.volunteer_id.is_not(None))
        .group_by(Task.volunteer_id)
    )
    def scoped(stmt):
        if ngo_id is not None:
            stmt = stmt.where(Campaign.ngo_id == ngo_id)
        if campaign_id:
            stmt = stmt.where(Campaign.id == campaign_id)
        return stmt

    hours_stmt, tasks_stmt = scoped(hours_stmt), scoped(tasks_stmt)

    stats: dict[int, dict] = {}
    for vid, hours, events in db.execute(hours_stmt).all():
        stats[vid] = {"hours": float(hours or 0), "events": events, "tasks": 0}
    for vid, count in db.execute(tasks_stmt).all():
        stats.setdefault(vid, {"hours": 0.0, "events": 0, "tasks": 0})["tasks"] = count

    volunteers = {
        v.id: v for v in db.scalars(select(Volunteer).where(Volunteer.id.in_(stats))).all()
    } if stats else {}
    ordered = sorted(
        stats.items(),
        key=lambda kv: (-kv[1]["hours"], -kv[1]["tasks"], volunteers[kv[0]].user.name.lower(), kv[0]),
    )
    rows, first_seen = [], {}
    for i, (vid, s) in enumerate(ordered, start=1):
        key = (s["hours"], s["tasks"])
        first_seen.setdefault(key, i)  # volunteers with identical numbers share a rank
        rows.append(PerformanceRow(
            rank=first_seen[key], volunteer_id=vid, volunteer_name=volunteers[vid].user.name,
            location=volunteers[vid].user.location, total_hours=round(s["hours"], 2),
            events_attended=s["events"], tasks_completed=s["tasks"],
        ))
    return paginate_list(rows, params)


@router.get("/donation-summary", response_model=Page[DonationSummaryRow])
def donation_summary(user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()]):
    ngo_id = _scope(db, user)
    stmt = select(Donation).order_by(Donation.id)
    if ngo_id is not None:
        stmt = stmt.where(Donation.ngo_id == ngo_id)
    campaigns = {c.id: c.title for c in db.scalars(select(Campaign))}
    buckets: dict[int | None, dict] = {}
    for d in db.scalars(stmt):
        b = buckets.setdefault(d.campaign_id, {"received": 0.0, "pending": 0.0, "count": 0,
                                                "donors": set(), "types": {}})
        if d.status == DonationStatus.RECEIVED:
            b["count"] += 1
            b["donors"].add(d.donor_id)
            b["types"][d.donation_type.value] = b["types"].get(d.donation_type.value, 0) + 1
            if d.donation_type == DonationType.MONEY:
                b["received"] += float(d.amount)
        elif d.status == DonationStatus.PENDING and d.donation_type == DonationType.MONEY:
            b["pending"] += float(d.amount)
    rows = [
        DonationSummaryRow(
            campaign_id=cid, campaign_title=campaigns.get(cid, "General fund"),
            money_received=round(b["received"], 2), money_pending=round(b["pending"], 2),
            donation_count=b["count"], donor_count=len(b["donors"]), by_type=b["types"],
        )
        for cid, b in buckets.items()
    ]
    rows.sort(key=lambda r: (-r.money_received, r.campaign_title))
    return paginate_list(rows, params)


@router.get("/campaigns", response_model=Page[CampaignReportRow])
def campaign_report(user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()]):
    """One row per campaign: volunteers, events, hours, money raised against the goal, stock handed out."""
    ngo_id = _scope(db, user)
    stmt = select(Campaign).options(joinedload(Campaign.ngo)).order_by(Campaign.id.desc())
    if ngo_id is not None:
        stmt = stmt.where(Campaign.ngo_id == ngo_id)
    campaigns = db.scalars(stmt).all()
    ids = [c.id for c in campaigns]
    if not ids:
        return paginate_list([], params)
    volunteers = dict(db.execute(
        select(Opportunity.campaign_id, func.count(distinct(Application.volunteer_id)))
        .join(Application, Application.opportunity_id == Opportunity.id)
        .where(Opportunity.campaign_id.in_(ids), Application.status == ApplicationStatus.ACCEPTED)
        .group_by(Opportunity.campaign_id)).all())
    events = dict(db.execute(select(Event.campaign_id, func.count()).where(Event.campaign_id.in_(ids))
                             .group_by(Event.campaign_id)).all())
    hours = dict(db.execute(
        select(Event.campaign_id, func.coalesce(func.sum(Participation.hours), 0))
        .join(Participation, Participation.event_id == Event.id)
        .where(Event.campaign_id.in_(ids), Participation.attendance.is_(True)).group_by(Event.campaign_id)).all())
    stock = {cid: (int(t), int(a)) for cid, t, a in db.execute(
        select(Resource.campaign_id, func.sum(Resource.quantity_total), func.sum(Resource.quantity_allocated))
        .where(Resource.campaign_id.in_(ids)).group_by(Resource.campaign_id))}
    money = received_by_campaign(db, ids)
    rows = []
    for c in campaigns:
        goal = float(c.donation_goal) if c.donation_goal is not None else None
        got = money.get(c.id, 0.0)
        total, given = stock.get(c.id, (0, 0))
        rows.append(CampaignReportRow(
            campaign_id=c.id, campaign_title=c.title, ngo_name=c.ngo.ngo_name, status=c.status.value,
            is_emergency=bool(c.is_emergency), required_volunteers=c.required_volunteers,
            accepted_volunteers=volunteers.get(c.id, 0), events=events.get(c.id, 0),
            volunteer_hours=round(float(hours.get(c.id, 0)), 2), money_received=round(got, 2),
            donation_goal=goal, donation_progress=round(min(got / goal * 100, 100), 1) if goal else None,
            resources_total=total, resources_distributed=given))
    return paginate_list(rows, params)


@router.get("/resource-utilization", response_model=Page[ResourceUtilizationRow])
def resource_utilization(user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()],
                         campaign_id: int | None = None):
    """How much of each resource has been given out. Aggregate only: no beneficiary information."""
    ngo_id = _scope(db, user)
    stmt = select(Resource, Campaign.title).join(Campaign, Resource.campaign_id == Campaign.id)
    if ngo_id is not None:
        stmt = stmt.where(Campaign.ngo_id == ngo_id)
    if campaign_id:
        stmt = stmt.where(Resource.campaign_id == campaign_id)
    rows = [
        ResourceUtilizationRow(
            resource_id=r.id, campaign_id=r.campaign_id, campaign_title=title, name=r.name, unit=r.unit,
            quantity_total=r.quantity_total, quantity_allocated=r.quantity_allocated,
            quantity_remaining=r.quantity_total - r.quantity_allocated,
            utilization_percent=round(r.quantity_allocated / r.quantity_total * 100, 1) if r.quantity_total else 0.0)
        for r, title in db.execute(stmt.order_by(Resource.id))
    ]
    return paginate_list(rows, params)
