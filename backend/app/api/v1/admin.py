from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError, conflict, not_found
from app.core.security import hash_password
from app.models import (
    NGO,
    Application,
    AuditLog,
    Campaign,
    Donation,
    DonationStatus,
    DonationType,
    Opportunity,
    Participation,
    Role,
    Task,
    User,
    VerificationStatus,
)
from app.schemas.admin import (
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    NgoAdminCreate,
    PlatformStats,
)
from app.schemas.common import Page
from app.services import auth as auth_service
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

PlatformAdmin = Annotated[User, Depends(require_roles(Role.PLATFORM_ADMIN))]

# Every route here needs a platform admin, enforced once for the whole router.
router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles(Role.PLATFORM_ADMIN))]
)


def audit_out(log: AuditLog, actor_name: str | None) -> AuditLogOut:
    return AuditLogOut(
        id=log.id, actor_user_id=log.actor_user_id, actor_name=actor_name, action_type=log.action_type,
        entity_type=log.entity_type, entity_id=log.entity_id, details=log.details or {},
        timestamp=log.timestamp,
    )


def user_out(u: User) -> AdminUserOut:
    ngo = u.ngo
    return AdminUserOut(
        id=u.id, name=u.name, email=u.email, phone=u.phone, role=u.role, location=u.location,
        is_active=u.is_active, is_verified=u.is_verified, ngo_id=ngo.id if ngo else None,
        ngo_name=ngo.ngo_name if ngo else None, ngo_status=ngo.verification_status if ngo else None,
        created_at=u.created_at,
    )


# ------------------------------------------------------------------ audit log
# Read-only by design: there is no POST/PATCH/PUT/DELETE here, and the ORM refuses to
# update or delete an AuditLog row.

@router.get("/audit-logs", response_model=Page[AuditLogOut])
def audit_logs(
    db: DbSession, params: Annotated[PageParams, Depends()],
    actor_user_id: int | None = None, action_type: str | None = None, entity_type: str | None = None,
    entity_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
):
    stmt = select(AuditLog, User.name).outerjoin(User, User.id == AuditLog.actor_user_id)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action_type:
        stmt = stmt.where(AuditLog.action_type == action_type)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if date_from:
        stmt = stmt.where(AuditLog.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(AuditLog.timestamp < datetime.combine(date_to + timedelta(days=1), time.min))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(AuditLog.action_type.ilike(like), AuditLog.entity_type.ilike(like),
                              User.name.ilike(like)))
    stmt = stmt.order_by(AuditLog.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)).all()
    return {
        "items": [audit_out(log, name) for log, name in rows], "page": params.page,
        "page_size": params.page_size, "total": total,
        "pages": -(-total // params.page_size) if total else 0,
    }


@router.get("/audit-logs/actions", response_model=list[str])
def audit_action_types(db: DbSession):
    return list(db.scalars(select(AuditLog.action_type).distinct().order_by(AuditLog.action_type)))


# ---------------------------------------------------------------------- users

@router.get("/users", response_model=Page[AdminUserOut])
def list_users(
    db: DbSession, params: Annotated[PageParams, Depends()], role: Role | None = None,
    is_active: bool | None = None, q: Annotated[str | None, Query(max_length=100)] = None,
):
    stmt = select(User).options(joinedload(User.ngo))
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    return paginate(db, stmt.order_by(User.created_at.desc(), User.id.desc()), params, user_out)


@router.get("/users/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User")
    return user_out(user)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, data: AdminUserUpdate, admin: PlatformAdmin, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User")
    changes = data.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                       {k: "This field cannot be empty." for k, v in changes.items() if v is None})
    if user.id == admin.id and changes.get("is_active") is False:
        raise conflict("You cannot deactivate your own account.")
    for field, value in changes.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            log_action(db, admin, {"is_active": "ACTIVATE_USER" if value else "DEACTIVATE_USER",
                                   "is_verified": "VERIFY_USER" if value else "UNVERIFY_USER"}[field],
                       "User", user.id, {"email": user.email, "role": user.role.value})
    if changes.get("is_active") is False:
        auth_service.revoke_all_for_user(db, user.id)  # kick out existing sessions immediately
    db.commit()
    return user_out(user)


@router.post("/ngo-admins", response_model=AdminUserOut, status_code=201)
def create_ngo_admin(data: NgoAdminCreate, admin: PlatformAdmin, db: DbSession):
    """The trusted way to create an NGO admin account. Public signup can never do this."""
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise AppError(409, "CONFLICT", "An account with this email already exists.",
                       {"email": "Email already in use."})
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password),
                role=Role.NGO_ADMIN, is_active=True, is_verified=True)
    db.add(user)
    db.flush()
    ngo = NGO(user_id=user.id, ngo_name=data.ngo_name, description=data.description,
              verification_status=VerificationStatus.VERIFIED if data.verified else VerificationStatus.PENDING)
    db.add(ngo)
    db.flush()
    log_action(db, admin, "CREATE_NGO_ADMIN", "NGO", ngo.id,
               {"user_id": user.id, "ngo_name": ngo.ngo_name, "verified": data.verified})
    db.commit()
    return user_out(user)


# ---------------------------------------------------------------------- stats

def _counts(db, column) -> dict[str, int]:
    return {getattr(k, "value", k): n for k, n in db.execute(select(column, func.count()).group_by(column))}


@router.get("/stats", response_model=PlatformStats)
def stats(db: DbSession):
    hours = db.scalar(select(func.coalesce(func.sum(Participation.hours), 0))
                      .where(Participation.attendance.is_(True)))
    money = db.scalar(select(func.coalesce(func.sum(Donation.amount), 0)).where(
        Donation.status == DonationStatus.RECEIVED, Donation.donation_type == DonationType.MONEY))
    return PlatformStats(
        users_by_role=_counts(db, User.role),
        active_users=db.scalar(select(func.count()).where(User.is_active.is_(True))) or 0,
        ngos_by_status=_counts(db, NGO.verification_status),
        campaigns_by_status=_counts(db, Campaign.status),
        opportunities_active=db.scalar(select(func.count()).where(Opportunity.is_active.is_(True))) or 0,
        applications_by_status=_counts(db, Application.status),
        tasks_by_status=_counts(db, Task.status),
        volunteer_hours=float(hours or 0),
        donations_received_money=float(money or 0),
        donations_pending=db.scalar(select(func.count()).where(
            Donation.status == DonationStatus.PENDING)) or 0,
        audit_entries=db.scalar(select(func.count()).select_from(AuditLog)) or 0,
    )
