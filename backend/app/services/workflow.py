"""Server-side state machines for applications and tasks. Invalid moves raise 409."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    NGO,
    Application,
    ApplicationStatus,
    Opportunity,
    TaskStatus,
    Volunteer,
)

APPLICATION_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SUBMITTED: {ApplicationStatus.UNDER_REVIEW},
    ApplicationStatus.UNDER_REVIEW: {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED},
    ApplicationStatus.ACCEPTED: set(),
    ApplicationStatus.REJECTED: set(),
}

TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.ACCEPTED, TaskStatus.DECLINED},
    TaskStatus.ACCEPTED: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.DECLINED: set(),
}


def ensure_application_transition(current: ApplicationStatus, target: ApplicationStatus) -> None:
    if target not in APPLICATION_TRANSITIONS[current]:
        raise AppError(
            409, "INVALID_TRANSITION", f"Cannot move an application from {current.value} to {target.value}."
        )


def ensure_task_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in TASK_TRANSITIONS[current]:
        raise AppError(409, "INVALID_TRANSITION", f"Cannot move a task from {current.value} to {target.value}.")


def has_accepted_application(db: Session, volunteer_id: int, ngo_id: int) -> bool:
    return db.scalar(
        select(Application.id).join(Opportunity, Application.opportunity_id == Opportunity.id)
        .where(Application.volunteer_id == volunteer_id, Application.status == ApplicationStatus.ACCEPTED,
               Opportunity.ngo_id == ngo_id).limit(1)
    ) is not None


def ensure_assignable(
    db: Session, volunteer_id: int, ngo: NGO, opportunity_id: int | None = None
) -> Volunteer:
    """A task may only go to a volunteer holding an ACCEPTED application with this NGO
    (and to the named opportunity, when the task is tied to one)."""
    volunteer = db.get(Volunteer, volunteer_id)
    if volunteer is None or not volunteer.user.is_active:
        raise AppError(404, "NOT_FOUND", "Volunteer not found.")
    stmt = (
        select(Application.id)
        .join(Opportunity, Application.opportunity_id == Opportunity.id)
        .where(
            Application.volunteer_id == volunteer_id,
            Application.status == ApplicationStatus.ACCEPTED,
            Opportunity.ngo_id == ngo.id,
        )
    )
    if opportunity_id is not None:
        stmt = stmt.where(Application.opportunity_id == opportunity_id)
    if db.scalar(stmt.limit(1)) is None:
        raise AppError(
            409,
            "NOT_ELIGIBLE",
            "This volunteer has no accepted application"
            + (" for that opportunity." if opportunity_id else " with your NGO."),
        )
    return volunteer
