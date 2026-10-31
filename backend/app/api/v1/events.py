from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import (
    CurrentNgo,
    CurrentUser,
    DbSession,
    OptionalUser,
    VerifiedNgo,
)
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import (
    Campaign,
    CampaignStatus,
    Event,
    EventAssignment,
    NotificationPriority,
    NotificationType,
    Role,
    Volunteer,
)
from app.schemas.campaign import (
    AssignmentCreate,
    AssignmentOut,
    EventCreate,
    EventOut,
    EventUpdate,
)
from app.schemas.common import Page
from app.services import campaigns as svc
from app.services import notifications, workflow
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/events", tags=["events"])


def to_out(e: Event, joined: bool = False) -> EventOut:
    return EventOut(
        id=e.id, campaign_id=e.campaign_id, campaign_title=e.campaign.title, event_name=e.event_name,
        event_date=e.event_date, event_time=e.event_time, location=e.location,
        description=e.description, created_at=e.created_at, joined=joined,
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
    page = paginate(db, stmt, params)  # ORM rows, converted below with the volunteer's "joined" flag
    joined = _joined_ids(db, user, [e.id for e in page["items"]])
    page["items"] = [to_out(e, e.id in joined) for e in page["items"]]
    return page


def _joined_ids(db, user, event_ids: list[int]) -> set[int]:
    if user is None or user.role != Role.VOLUNTEER or not event_ids:
        return set()
    vol_id = db.scalar(select(Volunteer.id).where(Volunteer.user_id == user.id))
    return set(db.scalars(select(EventAssignment.event_id).where(
        EventAssignment.volunteer_id == vol_id, EventAssignment.event_id.in_(event_ids)))) if vol_id else set()


@router.get("/me", response_model=Page[EventOut])
def my_events(
    user: VolunteerUser, db: DbSession,
    params: Annotated[PageParams, Depends()], past: bool = False,
):
    """Events the volunteer was assigned to or joined (upcoming by default)."""
    vol = get_volunteer(db, user)
    stmt = (select(Event).join(Event.campaign).options(joinedload(Event.campaign))
            .join(EventAssignment, EventAssignment.event_id == Event.id)
            .where(EventAssignment.volunteer_id == vol.id))
    stmt = stmt.where(Event.event_date < date.today()) if past else stmt.where(Event.event_date >= date.today())
    stmt = stmt.order_by(Event.event_date.desc() if past else Event.event_date, Event.id)
    return paginate(db, stmt, params, lambda e: to_out(e, True))


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, user: OptionalUser, db: DbSession):
    stmt = (
        select(Event).join(Event.campaign).options(joinedload(Event.campaign))
        .where(Event.id == event_id)
    )
    event = db.scalar(svc.restrict_visible(stmt, db, user))
    if event is None:
        raise not_found("Event")
    return to_out(event, event.id in _joined_ids(db, user, [event.id]))


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


# ------------------------------------------------------------ assignments / joining

def _upcoming_open_event(db, event_id: int, ngo) -> Event:
    event = _get_owned_event(db, event_id, ngo)
    _ensure_open(event.campaign)
    if event.event_date < date.today():
        raise conflict("This event has already happened.")
    return event


@router.post("/{event_id}/assignments", response_model=AssignmentOut, status_code=201)
def assign_volunteer(event_id: int, data: AssignmentCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    """The NGO puts one of its accepted volunteers on an event's roster."""
    event = _upcoming_open_event(db, event_id, ngo)
    vol = workflow.ensure_assignable(db, data.volunteer_id, ngo)
    if db.scalar(select(EventAssignment.id).where(
            EventAssignment.event_id == event.id, EventAssignment.volunteer_id == vol.id)):
        raise conflict("This volunteer is already on the roster.")
    row = EventAssignment(event_id=event.id, volunteer_id=vol.id, assigned_by="NGO")
    db.add(row)
    db.flush()
    log_action(db, user, "ASSIGN_VOLUNTEER_TO_EVENT", "Event", event.id, {"volunteer_id": vol.id})
    notify(db, [vol.user_id], title="You were added to an event",
           message=f'You are on the roster for "{event.event_name}" on {event.event_date}'
                   + (f" in {event.location}." if event.location else "."),
           type=NotificationType.EVENT_REMINDER, link="/events", dedupe_key=f"event-assign:{event.id}:{vol.id}")
    db.commit()
    return AssignmentOut(volunteer_id=vol.id, volunteer_name=vol.user.name, assigned_by="NGO")


@router.get("/{event_id}/assignments", response_model=list[AssignmentOut])
def event_roster(event_id: int, ngo: CurrentNgo, db: DbSession):
    event = _get_owned_event(db, event_id, ngo)
    rows = db.scalars(select(EventAssignment).options(joinedload(EventAssignment.volunteer))
                      .where(EventAssignment.event_id == event.id).order_by(EventAssignment.id))
    return [AssignmentOut(volunteer_id=r.volunteer_id, volunteer_name=r.volunteer.user.name,
                          assigned_by=r.assigned_by) for r in rows]


@router.delete("/{event_id}/assignments/{volunteer_id}")
def remove_from_roster(event_id: int, volunteer_id: int, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    event = _upcoming_open_event(db, event_id, ngo)
    row = db.scalar(select(EventAssignment).where(
        EventAssignment.event_id == event.id, EventAssignment.volunteer_id == volunteer_id))
    if row is None:
        raise not_found("Roster entry")
    vol = db.get(Volunteer, volunteer_id)
    log_action(db, user, "REMOVE_VOLUNTEER_FROM_EVENT", "Event", event.id, {"volunteer_id": volunteer_id})
    notify(db, [vol.user_id], title="Removed from an event",
           message=f'You were taken off the roster for "{event.event_name}".',
           type=NotificationType.EVENT_REMINDER, link="/events", dedupe_key=f"event-remove:{event.id}:{vol.id}")
    db.delete(row)
    db.commit()
    return {"removed": True}


def _joinable(db, event_id: int, user) -> tuple[Event, Volunteer]:
    vol = get_volunteer(db, user)
    event = db.scalar(select(Event).options(joinedload(Event.campaign).joinedload(Campaign.ngo))
                      .where(Event.id == event_id))
    if event is None or event.campaign.status != CampaignStatus.ACTIVE:
        raise not_found("Event")
    if not workflow.has_accepted_application(db, vol.id, event.campaign.ngo_id):
        raise AppError(409, "NOT_ELIGIBLE",
                       "You can join events once this NGO has accepted one of your applications.")
    if event.event_date < date.today():
        raise conflict("This event has already happened.")
    return event, vol


@router.post("/{event_id}/join", status_code=201)
def join_event(event_id: int, user: VolunteerUser, db: DbSession):
    event, vol = _joinable(db, event_id, user)
    if db.scalar(select(EventAssignment.id).where(
            EventAssignment.event_id == event.id, EventAssignment.volunteer_id == vol.id)):
        raise conflict("You are already on this event's roster.")
    db.add(EventAssignment(event_id=event.id, volunteer_id=vol.id, assigned_by="SELF"))
    notify(db, [event.campaign.ngo.user_id], title="Volunteer joined an event",
           message=f'{user.name} joined "{event.event_name}".', type=NotificationType.EVENT_REMINDER,
           priority=NotificationPriority.LOW, link="/admin/events", dedupe_key=f"event-join:{event.id}:{vol.id}")
    db.commit()
    return {"joined": True}


@router.delete("/{event_id}/join")
def leave_event(event_id: int, user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
    row = db.scalar(select(EventAssignment).where(
        EventAssignment.event_id == event_id, EventAssignment.volunteer_id == vol.id))
    if row is None:
        raise not_found("Roster entry")
    db.delete(row)
    db.commit()
    return {"joined": False}
