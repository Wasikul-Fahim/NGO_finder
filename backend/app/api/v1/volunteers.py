from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.core.errors import forbidden
from app.models import Role, User, Volunteer
from app.schemas.opportunity import VolunteerOut, VolunteerUpdate

router = APIRouter(prefix="/volunteers", tags=["volunteers"])

VolunteerUser = Annotated[User, Depends(require_roles(Role.VOLUNTEER))]


def get_volunteer(db, user: User) -> Volunteer:
    vol = db.scalar(select(Volunteer).where(Volunteer.user_id == user.id))
    if vol is None:
        raise forbidden("No volunteer profile is linked to this account.")
    return vol


def to_out(vol: Volunteer) -> VolunteerOut:
    return VolunteerOut(
        id=vol.id, name=vol.user.name, location=vol.user.location, skills=vol.skills or [],
        interests=vol.interests or [], availability=vol.availability or [], experience=vol.experience,
    )


@router.get("/me", response_model=VolunteerOut)
def my_profile(user: VolunteerUser, db: DbSession):
    return to_out(get_volunteer(db, user))


@router.patch("/me", response_model=VolunteerOut)
def update_my_profile(data: VolunteerUpdate, user: VolunteerUser, db: DbSession):
    vol = get_volunteer(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "location":
            user.location = value
        elif value is not None or field == "experience":
            setattr(vol, field, value)
    db.commit()
    return to_out(vol)
