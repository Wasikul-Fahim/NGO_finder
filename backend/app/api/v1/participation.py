from collections import defaultdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentNgo, CurrentUser, DbSession, VerifiedNgo
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import Campaign, Event, Participation, Task, TaskStatus
from app.schemas.common import Page
from app.schemas.impact import (
    ContributionOut,
    MonthlyHours,
    ParticipationCreate,
    ParticipationOut,
    ParticipationUpdate,
)
from app.services import workflow
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["participation"])


def to_out(p: Participation) -> ParticipationOut:
    return ParticipationOut(
        id=p.id, event_id=p.event_id, event_name=p.event.event_name,
        campaign_title=p.event.campaign.title, volunteer_id=p.volunteer_id,
        volunteer_name=p.volunteer.user.name, attendance=p.attendance, hours=float(p.hours or 0),
        participation_date=p.participation_date,
    )


def _base():
    return select(Participation).options(
        joinedload(Participation.event).joinedload(Event.campaign),
        joinedload(Participation.volunteer),
    )


def _owned_event(db, event_id: int, ngo) -> Event:
    event = db.scalar(select(Event).options(joinedload(Event.campaign)).where(Event.id == event_id))
    if event is None:
        raise not_found("Event")
    if event.campaign.ngo_id != ngo.id:
        raise forbidden("This event belongs to another NGO.")
    return event


@router.post("/participation", response_model=ParticipationOut, status_code=201)
def record(data: ParticipationCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    event = _owned_event(db, data.event_id, ngo)
    if event.event_date > date.today():
        raise conflict("Attendance can only be recorded once the event has happened.")
    workflow.ensure_assignable(db, data.volunteer_id, ngo)
    if db.scalar(select(Participation.id).where(
        Participation.volunteer_id == data.volunteer_id, Participation.event_id == event.id
    )):
        raise conflict("Attendance is already recorded for this volunteer. Edit the existing record.")
    p = Participation(
        volunteer_id=data.volunteer_id, event_id=event.id, attendance=data.attendance,
        hours=data.hours, participation_date=event.event_date,
    )
    db.add(p)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise conflict("Attendance is already recorded for this volunteer.") from None
    log_action(db, user, "RECORD_ATTENDANCE", "Participation", p.id,
               {"event_id": event.id, "volunteer_id": p.volunteer_id,
                "attendance": p.attendance, "hours": float(p.hours)})
    db.commit()
    return to_out(db.scalar(_base().where(Participation.id == p.id)))


@router.patch("/participation/{participation_id}", response_model=ParticipationOut)
def update(participation_id: int, data: ParticipationUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    p = db.scalar(_base().where(Participation.id == participation_id))
    if p is None:
        raise not_found("Participation record")
    if p.event.campaign.ngo_id != ngo.id:
        raise forbidden("This record belongs to another NGO.")
    changes = data.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {k: "This field cannot be empty." for k, v in changes.items() if v is None})
    attendance = changes.get("attendance", p.attendance)
    hours = changes.get("hours", p.hours)
    if not attendance:
        if hours and hours > 0 and "hours" in changes:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {"hours": "An absent volunteer cannot have hours."})
        changes["hours"] = 0
    for field, value in changes.items():
        setattr(p, field, value)
    log_action(db, user, "UPDATE_ATTENDANCE", "Participation", p.id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(p)
    return to_out(p)


@router.get("/participation", response_model=Page[ParticipationOut])
def list_participation(
    ngo: CurrentNgo, db: DbSession, params: Annotated[PageParams, Depends()],
    event_id: int | None = None, volunteer_id: int | None = None,
):
    stmt = _base().join(Participation.event).join(Event.campaign).where(Campaign.ngo_id == ngo.id)
    if event_id:
        stmt = stmt.where(Participation.event_id == event_id)
    if volunteer_id:
        stmt = stmt.where(Participation.volunteer_id == volunteer_id)
    return paginate(db, stmt.order_by(Participation.participation_date.desc(), Participation.id.desc()),
                    params, to_out)


@router.get("/contributions/me", response_model=ContributionOut)
def my_contributions(user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
    records = db.scalars(
        _base().where(Participation.volunteer_id == vol.id)
        .order_by(Participation.participation_date.desc(), Participation.id.desc())
    ).unique().all()
    attended = [r for r in records if r.attendance]
    monthly: dict[str, float] = defaultdict(float)
    for r in attended:
        monthly[r.participation_date.strftime("%Y-%m")] += float(r.hours or 0)
    task_counts = dict(db.execute(
        select(Task.status, func.count()).where(Task.volunteer_id == vol.id).group_by(Task.status)
    ).all())
    return ContributionOut(
        total_hours=round(sum(float(r.hours or 0) for r in attended), 2),
        events_attended=len(attended),
        tasks_completed=task_counts.get(TaskStatus.COMPLETED, 0),
        tasks_total=sum(task_counts.values()),
        monthly_hours=[MonthlyHours(month=m, hours=round(h, 2)) for m, h in sorted(monthly.items())],
        history=[to_out(r) for r in records[:50]],
    )
