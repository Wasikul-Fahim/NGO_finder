from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.models import NGO, Role, User, VerificationStatus

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


def _user_from_credentials(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if creds is None:
        return None
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized("Invalid or expired token.") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized("Invalid or expired token.")
    return user


def get_optional_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User | None:
    return _user_from_credentials(creds, db)


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    user = _user_from_credentials(creds, db)
    if user is None:
        raise unauthorized()
    return user


def require_roles(*roles: Role):
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise forbidden("Your role cannot access this resource.")
        return user

    return checker


def get_current_ngo(
    user: Annotated[User, Depends(require_roles(Role.NGO_ADMIN))], db: DbSession
) -> NGO:
    """The NGO owned by the signed-in NGO admin (verified or not)."""
    ngo = db.query(NGO).filter(NGO.user_id == user.id).first()
    if ngo is None:
        raise forbidden("No NGO is linked to this account.")
    return ngo


def require_verified_ngo_admin(ngo: Annotated[NGO, Depends(get_current_ngo)]) -> NGO:
    if ngo.verification_status != VerificationStatus.VERIFIED:
        raise forbidden("Your NGO must be verified before you can do this.")
    return ngo


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentNgo = Annotated[NGO, Depends(get_current_ngo)]
VerifiedNgo = Annotated[NGO, Depends(require_verified_ngo_admin)]
