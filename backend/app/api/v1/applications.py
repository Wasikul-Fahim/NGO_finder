from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentNgo, CurrentUser, DbSession, VerifiedNgo
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import (
    Application,
    ApplicationStatus,
    NotificationPriority,
    NotificationType,
    Opportunity,
    VerificationStatus,
)
from app.schemas.common import Page
from app.schemas.opportunity import (
    ApplicationCreate,
    ApplicationMessage,
    ApplicationOut,
    ApplicationReview,
)
from app.services import workflow
from app.services.audit import log_action
from app.services.notifications import dedupe_hash, notify
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["applications"])


def to_out(a: Application, contact: bool = False) -> ApplicationOut:
    return ApplicationOut(
        id=a.id, opportunity_id=a.opportunity_id, opportunity_title=a.opportunity.title,
        ngo_name=a.opportunity.ngo.ngo_name, volunteer_id=a.volunteer_id,
        volunteer_name=a.volunteer.user.name, volunteer_location=a.volunteer.user.location,
        volunteer_skills=a.volunteer.skills or [], status=a.status,
        application_date=a.application_date, review_note=a.review_note,
        volunteer_email=a.volunteer.user.email if contact else None,
        volunteer_phone=a.volunteer.user.phone if contact else None,
    )


def _base():
    return select(Application).options(
        joinedload(Application.opportunity).joinedload(Opportunity.ngo),
        joinedload(Application.volunteer),
    )


def _apply(db, user, opportunity_id: int) -> ApplicationOut:
    vol = get_volunteer(db, user)
    if not user.phone:
        # The NGO's only way to reach an applicant is the contact details on the profile.
        raise AppError(409, "PROFILE_INCOMPLETE",
                       "Add your mobile number to your profile before applying, so the NGO can reach you.",
                       {"phone": "Mobile number required."})
    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.ngo.verification_status != VerificationStatus.VERIFIED:
        raise not_found("Opportunity")
    if not opp.is_active:
        raise conflict("This opportunity is no longer open.")
    if db.scalar(select(Application.id).where(
        Application.volunteer_id == vol.id, Application.opportunity_id == opp.id
    )):
        raise conflict("You have already applied to this opportunity.")
    app = Application(volunteer_id=vol.id, opportunity_id=opp.id)
    db.add(app)
    try:
        db.flush()
    except IntegrityError:  # concurrent double-submit hit the unique constraint
        db.rollback()
        raise conflict("You have already applied to this opportunity.") from None
    notify(db, [opp.ngo.user_id], title="New application",
           message=f'{user.name} applied for "{opp.title}".', type=NotificationType.APPLICATION_UPDATE,
           link="/admin/applications", dedupe_key=f"newapp:{app.id}")
    db.commit()
    return to_out(db.scalar(_base().where(Application.id == app.id)))


@router.post("/opportunities/{opportunity_id}/applications", response_model=ApplicationOut, status_code=201)
def apply(opportunity_id: int, user: VolunteerUser, db: DbSession):
    return _apply(db, user, opportunity_id)


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def submit_application(data: ApplicationCreate, user: VolunteerUser, db: DbSession):
    """Report-style submit: the volunteer comes from the login, the opportunity from the body."""
    return _apply(db, user, data.opportunity_id)


@router.get("/applications/me", response_model=Page[ApplicationOut])
def my_applications(
    user: VolunteerUser, db: DbSession, params: Annotated[PageParams, Depends()],
    status: ApplicationStatus | None = None,
):
    vol = get_volunteer(db, user)
    stmt = _base().where(Application.volunteer_id == vol.id)
    if status:
        stmt = stmt.where(Application.status == status)
    return paginate(db, stmt.order_by(Application.application_date.desc(), Application.id.desc()), params, to_out)


@router.get("/applications", response_model=Page[ApplicationOut])
def review_queue(
    ngo: CurrentNgo, db: DbSession, params: Annotated[PageParams, Depends()],
    status: ApplicationStatus | None = None, opportunity_id: int | None = None,
):
    stmt = _base().join(Application.opportunity).where(Opportunity.ngo_id == ngo.id)
    if status:
        stmt = stmt.where(Application.status == status)
    if opportunity_id:
        stmt = stmt.where(Application.opportunity_id == opportunity_id)
    return paginate(db, stmt.order_by(Application.application_date, Application.id), params,
                    lambda a: to_out(a, contact=True))


@router.patch("/applications/{application_id}/review", response_model=ApplicationOut)
@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
def review(
    application_id: int, data: ApplicationReview, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    app = db.scalar(_base().where(Application.id == application_id))
    if app is None:
        raise not_found("Application")
    if app.opportunity.ngo_id != ngo.id:
        raise forbidden("This application belongs to another NGO.")
    workflow.ensure_application_transition(app.status, data.status)
    previous = app.status
    app.status = data.status
    app.review_note = data.note
    log_action(
        db, user, f"APPLICATION_{data.status.value}", "Application", app.id,
        {"from": previous.value, "to": data.status.value, "opportunity_id": app.opportunity_id,
         "volunteer_id": app.volunteer_id},
    )
    notify(db, [app.volunteer.user_id], title="Application update",
           message=f'Your application for "{app.opportunity.title}" is now {data.status.value.replace("_", " ").lower()}.',
           type=NotificationType.APPLICATION_UPDATE, link="/applications",
           priority=NotificationPriority.HIGH if data.status == ApplicationStatus.ACCEPTED
           else NotificationPriority.NORMAL,
           dedupe_key=f"application:{app.id}:{data.status.value}")
    db.commit()
    return to_out(app, contact=True)


@router.post("/applications/{application_id}/messages", status_code=201)
def message_applicant(
    application_id: int, data: ApplicationMessage, ngo: VerifiedNgo, user: CurrentUser, db: DbSession
):
    """Contact an applicant from inside the platform. They get it as a notification (live if online)."""
    app = db.scalar(_base().where(Application.id == application_id))
    if app is None:
        raise not_found("Application")
    if app.opportunity.ngo_id != ngo.id:
        raise forbidden("This application belongs to another NGO.")
    reply_to = ngo.contact or user.email
    sent = notify(
        db, [app.volunteer.user_id], title=f"Message from {ngo.ngo_name}",
        message=f'About "{app.opportunity.title}": {data.message}\n\nReply to: {reply_to}',
        type=NotificationType.DIRECT_MESSAGE, priority=NotificationPriority.NORMAL, link="/applications",
        dedupe_key=f"msg:{app.id}:{dedupe_hash(data.message)}",
    )
    log_action(db, user, "MESSAGE_APPLICANT", "Application", app.id,
               {"opportunity_id": app.opportunity_id, "volunteer_id": app.volunteer_id,
                "length": len(data.message)})
    db.commit()
    return {"sent": sent}


@router.post("/applications/{application_id}/reply", status_code=201)
def reply_to_ngo(application_id: int, data: ApplicationMessage, user: VolunteerUser, db: DbSession):
    """The applicant answers the NGO about their own application."""
    vol = get_volunteer(db, user)
    app = db.scalar(_base().where(Application.id == application_id))
    if app is None or app.volunteer_id != vol.id:
        raise not_found("Application")
    sent = notify(
        db, [app.opportunity.ngo.user_id], title=f"Reply from {user.name}",
        message=f'About "{app.opportunity.title}": {data.message}',
        type=NotificationType.DIRECT_MESSAGE, priority=NotificationPriority.NORMAL,
        link="/admin/applications", dedupe_key=f"reply:{app.id}:{dedupe_hash(data.message)}",
    )
    db.commit()
    return {"sent": sent}
