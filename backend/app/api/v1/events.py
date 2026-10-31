from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, OptionalUser, VerifiedNgo
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import Campaign, Event, NotificationPriority, NotificationType
from app.schemas.campaign import EventCreate, EventOut, EventUpdate
from app.schemas.common import Page
from app.services import campaigns as svc
from app.services import notifications
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/events", tags=["events"])


def to_out(e: Event) -> EventOut:
    return EventOut(
        id=e.id, campaign_id=e.campaign_id, campaign_title=e.campaign.title, event_name=e.event_name,
        event_date=e.event_date, event_time=e.event_time, location=e.location,
        description=e.description, created_at=e.created_at,
    )


def _check_date_in_campaign(event_date: date, campaign: Campaign) -> None:
    if not campaign.start_date <= event_date <= campaign.end_date:
        raise AppError(
            422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
            {"event_date": f"Must fall within the campaign ({campaign.start_date} to {campaign.end_date})."},
        )


def _get_owned_event(db, event_id: int, ngo) -> Event:
    event = db.scalar(select(Event).options(joinedload(Event.campaign)).where(Event.id == event_id))
    if event is None:
        raise not_found("Event")
    if event.campaign.ngo_id != ngo.id:
        raise forbidden("This event belongs to another NGO.")
    return event


def _ensure_open(campaign: Campaign) -> None:
    if campaign.status in svc.LOCKED_STATUSES:
        raise conflict(f"Events cannot be changed on a {campaign.status.value.lower()} campaign.")


@router.get("", response_model=Page[EventOut])
def list_events(
    user: OptionalUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    campaign_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    from_date: date | None = None,
    to_date: date | None = None,
    upcoming: bool = False,
):
    stmt = select(Event).join(Event.campaign).options(joinedload(Event.campaign))
    stmt = svc.restrict_visible(stmt, db, user)
    if campaign_id:
        stmt = stmt.where(Event.campaign_id == campaign_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Event.event_name.ilike(like), Event.location.ilike(like)))
    if upcoming:
        from_date = max(from_date, date.today()) if from_date else date.today()
    if from_date:
        stmt = stmt.where(Event.event_date >= from_date)
    if to_date:
        stmt = stmt.where(Event.event_date <= to_date)
    stmt = stmt.order_by(Event.event_date, Event.event_time, Event.id)
    return paginate(db, stmt, params, to_out)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, user: OptionalUser, db: DbSession):
    stmt = (
        select(Event).join(Event.campaign).options(joinedload(Event.campaign))
        .where(Event.id == event_id)
    )
    event = db.scalar(svc.restrict_visible(stmt, db, user))
    if event is None:
        raise not_found("Event")
    return to_out(event)


@router.post("", response_model=EventOut, status_code=201)
def create_event(data: EventCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    campaign = svc.get_owned_campaign(db, data.campaign_id, ngo)
    _ensure_open(campaign)
    _check_date_in_campaign(data.event_date, campaign)
    event = Event(**data.model_dump())
    db.add(event)
    db.flush()
    log_action(db, user, "CREATE_EVENT", "Event", event.id,
               {"campaign_id": campaign.id, "event_name": event.event_name})
    db.commit()
    return to_out(event)


@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: int, data: EventUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    event = _get_owned_event(db, event_id, ngo)
    _ensure_open(event.campaign)
    changes = data.model_dump(exclude_unset=True)
    for required in ("event_name", "event_date"):
        if required in changes and changes[required] is None:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {required: "This field cannot be empty."})
    if "event_date" in changes:
        _check_date_in_campaign(changes["event_date"], event.campaign)
    for field, value in changes.items():
        setattr(event, field, value)
    log_action(db, user, "UPDATE_EVENT", "Event", event.id, {"fields": sorted(changes)})
    db.commit()
    return to_out(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    event = _get_owned_event(db, event_id, ngo)
    _ensure_open(event.campaign)
    log_action(db, user, "DELETE_EVENT", "Event", event.id,
               {"campaign_id": event.campaign_id, "event_name": event.event_name})
    db.delete(event)
    db.commit()


@router.post("/{event_id}/reminders")
def send_reminder(event_id: int, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    """Remind the NGO's accepted volunteers about an upcoming event (once per event per day)."""
    event = _get_owned_event(db, event_id, ngo)
    _ensure_open(event.campaign)
    if event.event_date < date.today():
        raise conflict("This event has already happened.")
    audience = notifications.volunteer_user_ids(db, ngo.id)
    when = f"{event.event_date}" + (f" at {event.event_time:%H:%M}" if event.event_time else "")
    created = notify(
        db, audience, title="Event reminder",
        message=f'"{event.event_name}" ({event.campaign.title}) is on {when}'
                + (f" in {event.location}." if event.location else "."),
        type=NotificationType.EVENT_REMINDER, priority=NotificationPriority.NORMAL, link="/events",
        dedupe_key=f"reminder:{event.id}:{date.today()}")
    log_action(db, user, "SEND_EVENT_REMINDER", "Event", event.id,
               {"audience_size": len(audience), "recipients": created})
    db.commit()
    return {"recipients": created, "audience_size": len(audience)}
