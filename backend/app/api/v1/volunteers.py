from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import conflict, forbidden, not_found
from app.models import (
    Application,
    Opportunity,
    Participation,
    Role,
    Task,
    User,
    Volunteer,
)
from app.schemas.common import Page
from app.schemas.opportunity import (
    VolunteerDirectoryOut,
    VolunteerOut,
    VolunteerUpdate,
)
from app.services.access import volunteer_viewer
from app.services.audit import log_action
from app.services.campaigns import user_ngo_id
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/volunteers", tags=["volunteers"])

VolunteerUser = Annotated[User, Depends(require_roles(Role.VOLUNTEER))]
Staff = Annotated[User, Depends(require_roles(Role.NGO_ADMIN, Role.PLATFORM_ADMIN))]


def get_volunteer(db, user: User) -> Volunteer:
    vol = db.scalar(select(Volunteer).where(Volunteer.user_id == user.id))
    if vol is None:
        raise forbidden("No volunteer profile is linked to this account. Create one first.")
    return vol


def is_complete(vol: Volunteer) -> bool:
    return bool(vol.user.phone and vol.user.location and vol.skills)


def to_out(vol: Volunteer) -> VolunteerOut:
    return VolunteerOut(
        id=vol.id, name=vol.user.name, phone=vol.user.phone, location=vol.user.location,
        skills=vol.skills or [], interests=vol.interests or [], availability=vol.availability or [],
        experience=vol.experience, profile_complete=is_complete(vol),
    )


def to_directory(vol: Volunteer) -> VolunteerDirectoryOut:
    return VolunteerDirectoryOut(**to_out(vol).model_dump(), email=vol.user.email)


def apply_update(vol: Volunteer, data: VolunteerUpdate) -> list[str]:
    changed = []
    for field, value in data.model_dump(exclude_unset=True).items():
        if field in ("location", "phone"):
            setattr(vol.user, field, value)
        elif value is not None or field == "experience":
            setattr(vol, field, value)
        else:
            continue
        changed.append(field)
    return changed


def _load(db, volunteer_id: int) -> Volunteer:
    vol = db.scalar(select(Volunteer).options(joinedload(Volunteer.user)).where(Volunteer.id == volunteer_id))
    if vol is None:
        raise not_found("Volunteer")
    return vol


@router.post("", response_model=VolunteerOut, status_code=201)
def create_profile(data: VolunteerUpdate, user: VolunteerUser, db: DbSession):
    """Sign-up already creates an empty profile; this recreates one if it was deleted."""
    if db.scalar(select(Volunteer.id).where(Volunteer.user_id == user.id)):
        raise conflict("You already have a volunteer profile. Update it instead.")
    vol = Volunteer(user_id=user.id, skills=[], interests=[], availability=[])
    db.add(vol)
    db.flush()
    apply_update(vol, data)
    db.commit()
    return to_out(vol)


@router.get("", response_model=Page[VolunteerDirectoryOut])
def list_volunteers(
    user: Staff, db: DbSession, params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=100)] = None,
    skill: Annotated[str | None, Query(max_length=50)] = None,
):
    """NGO admins see volunteers who applied to their opportunities; platform admins see everyone."""
    stmt = select(Volunteer).options(joinedload(Volunteer.user)).join(User, User.id == Volunteer.user_id)
    if user.role == Role.NGO_ADMIN:
        ngo_id = user_ngo_id(db, user)
        stmt = stmt.where(Volunteer.id.in_(
            select(Application.volunteer_id).join(Opportunity, Application.opportunity_id == Opportunity.id)
            .where(Opportunity.ngo_id == ngo_id)))
    if q:
        stmt = stmt.where(or_(User.name.ilike(f"%{q.strip()}%"), User.email.ilike(f"%{q.strip()}%")))
    if skill:
        stmt = stmt.where(cast(Volunteer.skills, String).ilike(f'%"{skill.strip()}"%'))
    return paginate(db, stmt.order_by(User.name, Volunteer.id), params, to_directory)


@router.get("/me", response_model=VolunteerOut)
def my_profile(user: VolunteerUser, db: DbSession):
    return to_out(get_volunteer(db, user))


@router.patch("/me", response_model=VolunteerOut)
@router.put("/me", response_model=VolunteerOut)
def update_my_profile(data: VolunteerUpdate, user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
    apply_update(vol, data)
    db.commit()
    return to_out(vol)


@router.get("/{volunteer_id}", response_model=VolunteerDirectoryOut)
def get_volunteer_by_id(volunteer_id: int, user: CurrentUser, db: DbSession):
    vol = _load(db, volunteer_id)
    volunteer_viewer(db, user, vol)
    return to_directory(vol)


@router.put("/{volunteer_id}", response_model=VolunteerOut)
@router.patch("/{volunteer_id}", response_model=VolunteerOut)
def update_volunteer(volunteer_id: int, data: VolunteerUpdate, user: CurrentUser, db: DbSession):
    vol = _load(db, volunteer_id)
    kind, _ = volunteer_viewer(db, user, vol)
    if kind not in ("self", "platform"):
        raise forbidden("Only the volunteer or a platform admin can change this profile.")
    changed = apply_update(vol, data)
    if kind == "platform":
        log_action(db, user, "UPDATE_VOLUNTEER", "Volunteer", vol.id, {"fields": sorted(changed)})
    db.commit()
    return to_out(vol)


@router.delete("/{volunteer_id}")
def delete_volunteer(volunteer_id: int, user: CurrentUser, db: DbSession):
    """Removes a profile only when it has no history; otherwise explains why it can't."""
    vol = _load(db, volunteer_id)
    kind, _ = volunteer_viewer(db, user, vol)
    if kind not in ("self", "platform"):
        raise forbidden("Only the volunteer or a platform admin can delete this profile.")
    history = {
        "applications": db.scalar(select(func.count()).where(Application.volunteer_id == vol.id)) or 0,
        "attendance records": db.scalar(select(func.count()).where(Participation.volunteer_id == vol.id)) or 0,
        "tasks": db.scalar(select(func.count()).where(Task.volunteer_id == vol.id)) or 0,
    }
    blocking = {k: v for k, v in history.items() if v}
    if blocking:
        raise conflict(
            "This profile can't be deleted because it has history ("
            + ", ".join(f"{v} {k}" for k, v in blocking.items())
            + "). Records are kept for NGO accountability.")
    log_action(db, user, "DELETE_VOLUNTEER", "Volunteer", vol.id, {"user_id": vol.user_id})
    db.delete(vol)
    db.commit()
    return {"deleted": True}
