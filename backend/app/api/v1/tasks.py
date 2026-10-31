from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, VerifiedNgo
from app.api.v1.volunteers import VolunteerUser, get_volunteer
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import (
    Campaign,
    NotificationPriority,
    NotificationType,
    Opportunity,
    Role,
    Task,
    TaskStatus,
    Volunteer,
)
from app.schemas.common import Page
from app.schemas.opportunity import TaskAssign, TaskCreate, TaskOut, TaskStatusChange, TaskUpdate
from app.services import campaigns as campaign_svc
from app.services import workflow
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def to_out(t: Task) -> TaskOut:
    return TaskOut(
        id=t.id, campaign_id=t.campaign_id, campaign_title=t.campaign.title,
        opportunity_id=t.opportunity_id, volunteer_id=t.volunteer_id,
        volunteer_name=t.volunteer.user.name if t.volunteer else None, task_name=t.task_name,
        description=t.description, deadline=t.deadline, status=t.status, created_at=t.created_at,
    )


def _base():
    return select(Task).options(joinedload(Task.campaign), joinedload(Task.volunteer))


def _get_owned(db, task_id: int, ngo) -> Task:
    task = db.scalar(_base().where(Task.id == task_id))
    if task is None:
        raise not_found("Task")
    if task.campaign.ngo_id != ngo.id:
        raise forbidden("This task belongs to another NGO.")
    return task


def _notify_assigned(db, task: Task, campaign_title: str) -> None:
    volunteer = db.get(Volunteer, task.volunteer_id)
    notify(db, [volunteer.user_id], title="New task assigned",
           message=f'You were assigned "{task.task_name}" in {campaign_title}.',
           type=NotificationType.TASK_ASSIGNED, link="/tasks", priority=NotificationPriority.HIGH,
           dedupe_key=f"task:{task.id}:{task.volunteer_id}")


def _ensure_open(task: Task) -> None:
    if task.campaign.status in campaign_svc.LOCKED_STATUSES:
        raise conflict(f"Tasks cannot be changed on a {task.campaign.status.value.lower()} campaign.")


@router.post("", response_model=TaskOut, status_code=201)
def create_task(data: TaskCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    campaign = campaign_svc.get_owned_campaign(db, data.campaign_id, ngo)
    if campaign.status in campaign_svc.LOCKED_STATUSES:
        raise conflict(f"Tasks cannot be added to a {campaign.status.value.lower()} campaign.")
    if data.opportunity_id is not None:
        opp = db.get(Opportunity, data.opportunity_id)
        if opp is None or opp.ngo_id != ngo.id:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {"opportunity_id": "Pick one of your own opportunities."})
    if data.volunteer_id is not None:
        workflow.ensure_assignable(db, data.volunteer_id, ngo, data.opportunity_id)
    task = Task(**data.model_dump(), status=TaskStatus.PENDING)
    db.add(task)
    db.flush()
    log_action(db, user, "CREATE_TASK", "Task", task.id,
               {"campaign_id": campaign.id, "volunteer_id": data.volunteer_id})
    if data.volunteer_id is not None:
        _notify_assigned(db, task, campaign.title)
    db.commit()
    return to_out(db.scalar(_base().where(Task.id == task.id)))


@router.get("/me", response_model=Page[TaskOut])
def my_tasks(
    user: VolunteerUser, db: DbSession, params: Annotated[PageParams, Depends()],
    status: TaskStatus | None = None,
):
    vol = get_volunteer(db, user)
    stmt = _base().where(Task.volunteer_id == vol.id)
    if status:
        stmt = stmt.where(Task.status == status)
    return paginate(db, stmt.order_by(Task.deadline.is_(None), Task.deadline, Task.id), params, to_out)


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()],
    status: TaskStatus | None = None, campaign_id: int | None = None, volunteer_id: int | None = None,
):
    """Role-aware: volunteers get their own tasks, NGO admins their NGO's, platform admins all."""
    stmt = _base().join(Task.campaign)
    if user.role == Role.VOLUNTEER:
        stmt = stmt.where(Task.volunteer_id == get_volunteer(db, user).id)
    elif user.role == Role.NGO_ADMIN:
        stmt = stmt.where(Campaign.ngo_id == campaign_svc.user_ngo_id(db, user))
    elif user.role != Role.PLATFORM_ADMIN:
        raise forbidden("Tasks are available to volunteers and admins.")
    if status:
        stmt = stmt.where(Task.status == status)
    if campaign_id:
        stmt = stmt.where(Task.campaign_id == campaign_id)
    if volunteer_id and user.role != Role.VOLUNTEER:
        stmt = stmt.where(Task.volunteer_id == volunteer_id)
    return paginate(db, stmt.order_by(Task.created_at.desc(), Task.id.desc()), params, to_out)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    task = _get_owned(db, task_id, ngo)
    _ensure_open(task)
    if task.status in (TaskStatus.COMPLETED, TaskStatus.DECLINED):
        raise conflict(f"A {task.status.value.lower()} task can no longer be edited.")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("task_name", "x") is None:
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {"task_name": "This field cannot be empty."})
    for field, value in changes.items():
        setattr(task, field, value)
    log_action(db, user, "UPDATE_TASK", "Task", task.id, {"fields": sorted(changes)})
    db.commit()
    return to_out(task)


@router.post("/{task_id}/assign", response_model=TaskOut)
def assign_task(task_id: int, data: TaskAssign, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    task = _get_owned(db, task_id, ngo)
    _ensure_open(task)
    if task.status not in (TaskStatus.PENDING, TaskStatus.DECLINED):
        raise conflict(f"A {task.status.value.lower()} task cannot be reassigned.")
    workflow.ensure_assignable(db, data.volunteer_id, ngo, task.opportunity_id)
    previous = task.volunteer_id
    task.volunteer_id = data.volunteer_id
    task.status = TaskStatus.PENDING  # a reassigned declined task starts over
    log_action(db, user, "ASSIGN_TASK", "Task", task.id,
               {"from_volunteer_id": previous, "to_volunteer_id": data.volunteer_id})
    _notify_assigned(db, task, task.campaign.title)
    db.commit()
    db.refresh(task)  # drop the stale `volunteer` relationship loaded before reassignment
    return to_out(task)


@router.patch("/{task_id}/status", response_model=TaskOut)
def change_status(task_id: int, data: TaskStatusChange, user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
    task = db.scalar(_base().where(Task.id == task_id))
    if task is None or task.volunteer_id != vol.id:
        raise not_found("Task")  # don't reveal other volunteers' tasks
    workflow.ensure_task_transition(task.status, data.status)
    task.status = data.status
    notify(db, [task.campaign.ngo.user_id], title="Task update",
           message=f'{user.name} marked "{task.task_name}" as {data.status.value.replace("_", " ").lower()}.',
           type=NotificationType.TASK_UPDATE, link="/admin/tasks",
           dedupe_key=f"taskstatus:{task.id}:{data.status.value}")
    db.commit()
    return to_out(task)
