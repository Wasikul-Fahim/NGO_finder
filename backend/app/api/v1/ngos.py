from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, or_, select

from app.api.deps import CurrentNgo, CurrentUser, DbSession, require_roles
from app.core.errors import conflict, forbidden, not_found
from app.models import (
    NGO,
    Campaign,
    Donation,
    NotificationPriority,
    NotificationType,
    Opportunity,
    Role,
    User,
    VerificationStatus,
)
from app.schemas.auth import NgoRegisterRequest, UserOut
from app.schemas.common import Page
from app.schemas.ngo import NgoOut, NgoUpdate, NgoVerify
from app.services import auth as auth_service
from app.services import uploads
from app.services.audit import log_action
from app.services.notifications import notify
from app.services.pagination import PageParams, paginate

router = APIRouter(prefix="/ngos", tags=["ngos"])
PlatformAdmin = Annotated[User, Depends(require_roles(Role.PLATFORM_ADMIN))]


def to_out(n: NGO) -> NgoOut:
    return NgoOut(
        id=n.id, ngo_name=n.ngo_name, description=n.description, address=n.address, contact=n.contact,
        contact_number=n.contact_number, registration_info=n.registration_info,
        logo_url=f"/uploads/logos/{n.logo_path}" if n.logo_path else None,
        verification_status=n.verification_status, verification_remarks=n.verification_remarks,
        created_at=n.created_at,
    )


def _editable(db, ngo_id: int, user: User) -> NGO:
    """The NGO's own admin, or a platform admin."""
    ngo = db.get(NGO, ngo_id)
    if ngo is None:
        raise not_found("NGO")
    if user.role != Role.PLATFORM_ADMIN and not (user.role == Role.NGO_ADMIN and ngo.user_id == user.id):
        raise forbidden("You can only manage your own NGO.")
    return ngo


def _apply_update(ngo: NGO, data: NgoUpdate) -> list[str]:
    changes = data.model_dump(exclude_unset=True)
    if changes.get("ngo_name") is None:
        changes.pop("ngo_name", None)
    for field, value in changes.items():
        setattr(ngo, field, value)
    return sorted(changes)


@router.post("", response_model=UserOut, status_code=201)
def register_ngo(data: NgoRegisterRequest, db: DbSession):
    """Register an NGO (same as /auth/register-ngo). It starts PENDING until a platform admin verifies it."""
    return auth_service.register_ngo(db, data)


@router.get("/me", response_model=NgoOut)
def get_my_ngo(ngo: CurrentNgo):
    return to_out(ngo)


@router.patch("/me", response_model=NgoOut)
@router.put("/me", response_model=NgoOut)
def update_my_ngo(data: NgoUpdate, ngo: CurrentNgo, user: CurrentUser, db: DbSession):
    fields = _apply_update(ngo, data)
    log_action(db, user, "UPDATE_NGO", "NGO", ngo.id, {"fields": fields})
    db.commit()
    return to_out(ngo)


@router.post("/me/logo", response_model=NgoOut)
async def upload_logo(ngo: CurrentNgo, user: CurrentUser, db: DbSession, file: Annotated[UploadFile, File()]):
    """PNG, JPG or WEBP up to 2 MB. The type is checked from the file's contents."""
    name = await uploads.save_logo(file)
    old, ngo.logo_path = ngo.logo_path, name
    log_action(db, user, "UPLOAD_NGO_LOGO", "NGO", ngo.id, {})
    db.commit()
    uploads.delete_logo(old)
    return to_out(ngo)


@router.delete("/me/logo", response_model=NgoOut)
def remove_logo(ngo: CurrentNgo, user: CurrentUser, db: DbSession):
    old, ngo.logo_path = ngo.logo_path, None
    log_action(db, user, "REMOVE_NGO_LOGO", "NGO", ngo.id, {})
    db.commit()
    uploads.delete_logo(old)
    return to_out(ngo)


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
    return paginate(db, stmt, params, to_out)


@router.get("/{ngo_id}", response_model=NgoOut)
def get_ngo(ngo_id: int, user: CurrentUser, db: DbSession):
    ngo = db.get(NGO, ngo_id)
    visible = ngo is not None and (
        ngo.verification_status == VerificationStatus.VERIFIED
        or user.role == Role.PLATFORM_ADMIN or ngo.user_id == user.id)
    if not visible:
        raise not_found("NGO")
    return to_out(ngo)


@router.put("/{ngo_id}", response_model=NgoOut)
@router.patch("/{ngo_id}", response_model=NgoOut)
def update_ngo(ngo_id: int, data: NgoUpdate, user: CurrentUser, db: DbSession):
    ngo = _editable(db, ngo_id, user)
    fields = _apply_update(ngo, data)
    log_action(db, user, "UPDATE_NGO", "NGO", ngo.id, {"fields": fields})
    db.commit()
    return to_out(ngo)


@router.delete("/{ngo_id}")
def delete_ngo(ngo_id: int, user: CurrentUser, db: DbSession):
    """Only an NGO with no campaigns, opportunities or donations can be removed; otherwise explain why."""
    ngo = _editable(db, ngo_id, user)
    related = {
        "campaigns": db.scalar(select(func.count()).where(Campaign.ngo_id == ngo.id)) or 0,
        "opportunities": db.scalar(select(func.count()).where(Opportunity.ngo_id == ngo.id)) or 0,
        "donations": db.scalar(select(func.count()).where(Donation.ngo_id == ngo.id)) or 0,
    }
    blocking = {k: v for k, v in related.items() if v}
    if blocking:
        raise conflict(
            "This NGO can't be deleted because it has related records ("
            + ", ".join(f"{v} {k}" for k, v in blocking.items())
            + "). Records are kept for accountability; ask a platform admin to reject or deactivate it instead.")
    log_action(db, user, "DELETE_NGO", "NGO", ngo.id, {"ngo_name": ngo.ngo_name})
    logo = ngo.logo_path
    db.delete(ngo)
    db.commit()
    uploads.delete_logo(logo)
    return {"deleted": True}


@router.patch("/{ngo_id}/verify", response_model=NgoOut)
@router.patch("/{ngo_id}/verification", response_model=NgoOut)
def verify_ngo(ngo_id: int, data: NgoVerify, db: DbSession, admin: PlatformAdmin):
    ngo = db.get(NGO, ngo_id)
    if ngo is None:
        raise not_found("NGO")
    target = VerificationStatus(data.status)
    if ngo.verification_status == target:
        raise conflict(f"NGO is already {target.value}.")
    previous = ngo.verification_status
    ngo.verification_status = target
    ngo.verification_remarks = data.remarks
    log_action(
        db, admin, "VERIFY_NGO" if target == VerificationStatus.VERIFIED else "REJECT_NGO", "NGO",
        ngo.id, {"from": previous.value, "to": target.value, "reason": data.remarks},
    )
    approved = target == VerificationStatus.VERIFIED
    notify(db, [ngo.user_id], title="Your NGO was verified" if approved else "Your NGO was not verified",
           message=("You can now post campaigns, opportunities and events." if approved else
                    "Your organisation was not approved." + (f" Reason: {data.remarks}" if data.remarks else "")),
           type=NotificationType.ANNOUNCEMENT, link="/admin",
           priority=NotificationPriority.HIGH, dedupe_key=f"ngo-verify:{ngo.id}:{target.value}")
    db.commit()
    return to_out(ngo)
