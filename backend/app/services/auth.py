import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, conflict, unauthorized
from app.core.security import (
    DUMMY_HASH,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import (
    NGO,
    Beneficiary,
    NotificationType,
    RefreshToken,
    Role,
    User,
    VerificationStatus,
    Volunteer,
)
from app.models.base import utcnow
from app.schemas.auth import NgoRegisterRequest, RegisterRequest
from app.services.audit import log_action
from app.services.notifications import notify

INVALID_CREDENTIALS = "Invalid email or password."


def register_user(db: Session, data: RegisterRequest) -> User:
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise _duplicate_email()
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=Role(data.role),
        location=data.location,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _duplicate_email() from None
    if user.role == Role.VOLUNTEER:
        db.add(Volunteer(user_id=user.id, skills=[], interests=[], availability=[]))
    elif user.role == Role.BENEFICIARY:
        db.add(Beneficiary(user_id=user.id, name=user.name, location=user.location))
    db.commit()
    return user


def register_ngo(db: Session, data: NgoRegisterRequest) -> User:
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise _duplicate_email()
    user = User(
        name=data.name, email=data.email, password_hash=hash_password(data.password), phone=data.phone,
        role=Role.NGO_ADMIN, location=data.location, is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _duplicate_email() from None
    ngo = NGO(
        user_id=user.id, ngo_name=data.ngo_name, description=data.description, address=data.address,
        contact=data.contact, verification_status=VerificationStatus.PENDING,
    )
    db.add(ngo)
    db.flush()
    log_action(db, user, "REGISTER_NGO", "NGO", ngo.id, {"ngo_name": ngo.ngo_name})
    admins = db.scalars(select(User.id).where(User.role == Role.PLATFORM_ADMIN, User.is_active.is_(True)))
    notify(db, admins, title="NGO awaiting verification",
           message=f'"{ngo.ngo_name}" registered and is waiting to be verified.',
           type=NotificationType.ANNOUNCEMENT, link="/platform/ngos", dedupe_key=f"ngo-signup:{ngo.id}")
    db.commit()
    return user


def _duplicate_email() -> AppError:
    return AppError(
        409, "CONFLICT", "An account with this email already exists.", {"email": "Email already in use."}
    )


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    # Always run one bcrypt comparison so timing doesn't reveal whether the email exists.
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok or not user.is_active:
        raise unauthorized(INVALID_CREDENTIALS)
    return user


def issue_refresh_token(
    db: Session, user: User, family_id: str | None = None, user_agent: str | None = None
) -> tuple[str, RefreshToken]:
    raw = generate_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        family_id=family_id or uuid.uuid4().hex,
        token_hash=hash_refresh_token(raw),
        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_expire_days),
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(row)
    db.flush()
    return raw, row


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def rotate_refresh_token(
    db: Session, raw_token: str, user_agent: str | None = None
) -> tuple[User, str]:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token)))
    if row is None:
        raise unauthorized("Session expired. Please log in again.")
    if row.revoked_at is not None:
        # A rotated/revoked token came back: assume theft and kill the whole chain.
        revoke_family(db, row.family_id)
        db.commit()
        raise unauthorized("Session expired. Please log in again.")
    user = db.get(User, row.user_id)
    if row.expires_at <= utcnow() or user is None or not user.is_active:
        raise unauthorized("Session expired. Please log in again.")

    new_raw, new_row = issue_refresh_token(db, user, row.family_id, user_agent)
    row.revoked_at = utcnow()
    row.replaced_by_id = new_row.id
    db.commit()
    return user, new_raw


def logout(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token)))
    if row is not None:
        revoke_family(db, row.family_id)
        db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError(
            400, "INVALID_PASSWORD", "Current password is incorrect.", {"current_password": "Incorrect password."}
        )
    if current == new:
        raise conflict("New password must differ from the current password.")
    user.password_hash = hash_password(new)
    revoke_all_for_user(db, user.id)
    db.commit()
