from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentNgo, CurrentUser, DbSession, VerifiedNgo
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import conflict, forbidden, not_found
from app.models import (
    Application,
    ApplicationStatus,
    Opportunity,
    VerificationStatus,
)
from app.schemas.common import Page
from app.schemas.opportunity import ApplicationOut, ApplicationReview
from app.services import workflow
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["applications"])


def to_out(a: Application) -> ApplicationOut:
    return ApplicationOut(
        id=a.id, opportunity_id=a.opportunity_id, opportunity_title=a.opportunity.title,
        ngo_name=a.opportunity.ngo.ngo_name, volunteer_id=a.volunteer_id,
        volunteer_name=a.volunteer.user.name, volunteer_location=a.volunteer.user.location,
        volunteer_skills=a.volunteer.skills or [], status=a.status,
        application_date=a.application_date, review_note=a.review_note,
    )


def _base():
    return select(Application).options(
        joinedload(Application.opportunity).joinedload(Opportunity.ngo),
        joinedload(Application.volunteer),
    )


@router.post("/opportunities/{opportunity_id}/applications", response_model=ApplicationOut, status_code=201)
def apply(opportunity_id: int, user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
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
        db.commit()
    except IntegrityError:  # concurrent double-submit hit the unique constraint
        db.rollback()
        raise conflict("You have already applied to this opportunity.") from None
    return to_out(db.scalar(_base().where(Application.id == app.id)))


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
    return paginate(db, stmt.order_by(Application.application_date, Application.id), params, to_out)


@router.patch("/applications/{application_id}/review", response_model=ApplicationOut)
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
    db.commit()
    return to_out(app)



