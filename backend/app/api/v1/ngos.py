from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select

from app.api.deps import CurrentNgo, CurrentUser, DbSession, require_roles
from app.core.errors import conflict, not_found
from app.models import NGO, NotificationPriority, NotificationType, Role, User, VerificationStatus
from app.schemas.common import Page
from app.schemas.ngo import NgoOut, NgoUpdate, NgoVerify
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/ngos", tags=["ngos"])


@router.get("/me", response_model=NgoOut)
def get_my_ngo(ngo: CurrentNgo):
    return ngo


@router.patch("/me", response_model=NgoOut)
def update_my_ngo(data: NgoUpdate, ngo: CurrentNgo, user: CurrentUser, db: DbSession):
    changes = data.model_dump(exclude_unset=True)
    if changes.get("ngo_name") is None:
        changes.pop("ngo_name", None)
    for field, value in changes.items():
        setattr(ngo, field, value)
    log_action(db, user, "UPDATE_NGO", "NGO", ngo.id, {"fields": sorted(changes)})
    db.commit()
    return ngo


@router.get("", response_model=Page[NgoOut])
def list_ngos(
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: VerificationStatus | None = None,
):
    stmt = select(NGO).order_by(NGO.ngo_name, NGO.id)
    if user.role == Role.PLATFORM_ADMIN:
        if status:
            stmt = stmt.where(NGO.verification_status == status)
    else:
        stmt = stmt.where(NGO.verification_status == VerificationStatus.VERIFIED)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(NGO.ngo_name.ilike(like), NGO.description.ilike(like)))
    return paginate(db, stmt, params)


@router.patch("/{ngo_id}/verify", response_model=NgoOut)
def verify_ngo(
    ngo_id: int,
    data: NgoVerify,
    db: DbSession,
    admin: Annotated[User, Depends(require_roles(Role.PLATFORM_ADMIN))],
):
    ngo = db.get(NGO, ngo_id)
    if ngo is None:
        raise not_found("NGO")
    target = VerificationStatus(data.status)
    if ngo.verification_status == target:
        raise conflict(f"NGO is already {target.value}.")
    previous = ngo.verification_status
    ngo.verification_status = target
    log_action(
        db, admin, "VERIFY_NGO" if target == VerificationStatus.VERIFIED else "REJECT_NGO", "NGO",
        ngo.id, {"from": previous.value, "to": target.value, "reason": data.reason},
    )
    approved = target == VerificationStatus.VERIFIED
    notify(db, [ngo.user_id], title="Your NGO was verified" if approved else "Your NGO was not verified",
           message=("You can now post campaigns, opportunities and events." if approved else
                    "Your organisation was not approved." + (f" Reason: {data.reason}" if data.reason else "")),
           type=NotificationType.ANNOUNCEMENT, link="/admin",
           priority=NotificationPriority.HIGH, dedupe_key=f"ngo-verify:{ngo.id}:{target.value}")
    db.commit()
    return ngo
