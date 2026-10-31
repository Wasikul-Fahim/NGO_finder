from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select

from app.api.deps import CurrentNgo, DbSession
from app.api.v1.admin import audit_out
from app.models import (
    Application,
    ApplicationStatus,
    AuditLog,
    Campaign,
    CampaignBeneficiary,
    Donation,
    DonationStatus,
    DonationType,
    Event,
    Opportunity,
    Participation,
    Resource,
    Task,
    TaskStatus,
    User,
)
from app.schemas.admin import AuditLogOut, Counter, NgoDashboard, UpcomingEvent
from app.schemas.common import Page
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/ngos/me", tags=["ngo-dashboard"])


def _by_status(db, column, *joins_where) -> dict[str, int]:
    stmt = select(column, func.count()).group_by(column)
    for clause in joins_where:
        stmt = stmt.where(clause)
    return {getattr(k, "value", k): n for k, n in db.execute(stmt)}


@router.get("/dashboard", response_model=NgoDashboard)
def dashboard(ngo: CurrentNgo, db: DbSession):
    """One screen for the whole NGO: counts across every module plus what needs attention now."""
    own_campaign = Campaign.ngo_id == ngo.id
    own_opp = Opportunity.ngo_id == ngo.id

    campaigns = _by_status(db, Campaign.status, own_campaign)
    applications = {
        k: n for k, n in db.execute(
            select(Application.status, func.count()).join(Opportunity, Application.opportunity_id == Opportunity.id)
            .where(own_opp).group_by(Application.status))
    }
    applications = {getattr(k, "value", k): n for k, n in applications.items()}
    tasks = {
        getattr(k, "value", k): n for k, n in db.execute(
            select(Task.status, func.count()).join(Campaign, Task.campaign_id == Campaign.id)
            .where(own_campaign).group_by(Task.status))
    }
    opp_active = db.scalar(select(func.count()).where(own_opp, Opportunity.is_active.is_(True))) or 0
    opp_inactive = db.scalar(select(func.count()).where(own_opp, Opportunity.is_active.is_(False))) or 0

    accepted_volunteers = db.scalar(
        select(func.count(distinct(Application.volunteer_id)))
        .join(Opportunity, Application.opportunity_id == Opportunity.id)
        .where(own_opp, Application.status == ApplicationStatus.ACCEPTED)) or 0
    hours = db.scalar(
        select(func.coalesce(func.sum(Participation.hours), 0))
        .join(Event, Participation.event_id == Event.id).join(Campaign, Event.campaign_id == Campaign.id)
        .where(own_campaign, Participation.attendance.is_(True))) or 0
    beneficiaries = db.scalar(
        select(func.count(distinct(CampaignBeneficiary.beneficiary_id)))
        .join(Campaign, CampaignBeneficiary.campaign_id == Campaign.id).where(own_campaign)) or 0
    money = db.scalar(select(func.coalesce(func.sum(Donation.amount), 0)).where(
        Donation.ngo_id == ngo.id, Donation.status == DonationStatus.RECEIVED,
        Donation.donation_type == DonationType.MONEY)) or 0
    pending_donations = db.scalar(select(func.count()).where(
        Donation.ngo_id == ngo.id, Donation.status == DonationStatus.PENDING)) or 0
    total, allocated = db.execute(
        select(func.coalesce(func.sum(Resource.quantity_total), 0),
               func.coalesce(func.sum(Resource.quantity_allocated), 0))
        .join(Campaign, Resource.campaign_id == Campaign.id).where(own_campaign)).one()

    today = date.today()
    unassigned = db.scalar(select(func.count()).select_from(Task).join(Campaign, Task.campaign_id == Campaign.id)
                           .where(own_campaign, Task.volunteer_id.is_(None), Task.status == TaskStatus.PENDING)) or 0
    awaiting_attendance = db.scalar(
        select(func.count()).select_from(Event).join(Campaign, Event.campaign_id == Campaign.id)
        .where(own_campaign, Event.event_date < today,
               ~select(Participation.id).where(Participation.event_id == Event.id).exists())) or 0
    attention = [
        Counter(key="applications_new", label="Applications waiting for review",
                count=applications.get("SUBMITTED", 0), link="/admin/applications"),
        Counter(key="applications_in_review", label="Applications in review",
                count=applications.get("UNDER_REVIEW", 0), link="/admin/applications"),
        Counter(key="donations_pending", label="Donations to confirm", count=pending_donations,
                link="/admin/donations"),
        Counter(key="tasks_unassigned", label="Unassigned tasks", count=unassigned, link="/admin/tasks"),
        Counter(key="tasks_declined", label="Declined tasks to reassign", count=tasks.get("DECLINED", 0),
                link="/admin/tasks"),
        Counter(key="events_attendance", label="Past events without attendance",
                count=awaiting_attendance, link="/admin/attendance"),
    ]
    upcoming = db.execute(
        select(Event, Campaign.title).join(Campaign, Event.campaign_id == Campaign.id)
        .where(own_campaign, Event.event_date >= today).order_by(Event.event_date, Event.id).limit(5)).all()
    recent = db.execute(
        select(AuditLog, User.name).outerjoin(User, User.id == AuditLog.actor_user_id)
        .where(AuditLog.actor_user_id == ngo.user_id).order_by(AuditLog.id.desc()).limit(10)).all()

    return NgoDashboard(
        ngo_name=ngo.ngo_name, verification_status=ngo.verification_status, campaigns_by_status=campaigns,
        opportunities_active=opp_active, opportunities_inactive=opp_inactive,
        applications_by_status=applications, tasks_by_status=tasks, accepted_volunteers=accepted_volunteers,
        volunteer_hours=round(float(hours), 2), beneficiaries_enrolled=beneficiaries,
        money_received=float(money), donations_pending=pending_donations,
        resources_total=int(total), resources_distributed=int(allocated),
        needs_attention=[c for c in attention if c.count > 0],
        upcoming_events=[UpcomingEvent(id=e.id, event_name=e.event_name, campaign_title=title,
                                       event_date=e.event_date.isoformat(), location=e.location)
                         for e, title in upcoming],
        recent_activity=[audit_out(log, name) for log, name in recent],
    )


@router.get("/activity", response_model=Page[AuditLogOut])
def activity(ngo: CurrentNgo, db: DbSession, params: Annotated[PageParams, Depends()]):
    """This NGO's own change history (read-only)."""
    stmt = (select(AuditLog).where(AuditLog.actor_user_id == ngo.user_id).order_by(AuditLog.id.desc()))
    return paginate(db, stmt, params, lambda log: audit_out(log, ngo.user.name))


