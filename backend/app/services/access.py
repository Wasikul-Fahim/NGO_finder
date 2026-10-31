from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import forbidden
from app.models import Application, Opportunity, Role, User, Volunteer
from app.services.campaigns import user_ngo_id


def volunteer_viewer(db: Session, user: User, vol: Volunteer) -> tuple[str, int | None]:
    """Who may look at a volunteer: the volunteer, a platform admin, or an NGO the volunteer applied to.

    Returns ("self" | "platform" | "ngo", ngo_id). Raises 403 for anyone else.
    """
    if vol.user_id == user.id:
        return "self", None
    if user.role == Role.PLATFORM_ADMIN:
        return "platform", None
    if user.role == Role.NGO_ADMIN:
        ngo_id = user_ngo_id(db, user)
        if ngo_id is not None and db.scalar(
            select(Application.id).join(Opportunity, Application.opportunity_id == Opportunity.id)
            .where(Application.volunteer_id == vol.id, Opportunity.ngo_id == ngo_id).limit(1)
        ):
            return "ngo", ngo_id
    raise forbidden("You do not have access to this volunteer's information.")
