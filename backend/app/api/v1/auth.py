from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import AppError, unauthorized
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    NgoRegisterRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.services import auth as auth_service
from app.services.rate_limit import login_limiter

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/api"  # covers both /api/v1/auth/* and the /api/auth/* alias


def _set_refresh_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=s.refresh_token_expire_days * 86400,
        httponly=True,
        secure=s.refresh_cookie_secure,
        samesite=s.refresh_cookie_samesite,
        path=COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=COOKIE_PATH,
        secure=s.refresh_cookie_secure,
        httponly=True,
        samesite=s.refresh_cookie_samesite,
    )


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest, db: DbSession):
    return auth_service.register_user(db, data)


@router.post("/register-ngo", response_model=UserOut, status_code=201)
def register_ngo(data: NgoRegisterRequest, db: DbSession):
    """Organisations join here. The account works immediately but the NGO stays PENDING (it cannot
    post campaigns, opportunities or events) until a platform admin verifies it."""
    return auth_service.register_ngo(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, response: Response, db: DbSession):
    ip = request.client.host if request.client else "unknown"
    keys = [f"ip:{ip}:{data.email}", f"email:{data.email}"]
    wait = login_limiter.retry_after(keys)
    if wait:
        raise AppError(
            429,
            "TOO_MANY_REQUESTS",
            "Too many failed attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    try:
        user = auth_service.authenticate(db, data.email, data.password)
    except AppError:
        login_limiter.record_failure(keys)
        raise
    login_limiter.reset(keys)
    raw, _ = auth_service.issue_refresh_token(db, user, user_agent=request.headers.get("user-agent"))
    db.commit()
    _set_refresh_cookie(response, raw)
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
):
    if not refresh_token:
        raise unauthorized("Session expired. Please log in again.")
    try:
        user, new_raw = auth_service.rotate_refresh_token(
            db, refresh_token, request.headers.get("user-agent")
        )
    except AppError:
        _clear_refresh_cookie(response)
        raise
    _set_refresh_cookie(response, new_raw)
    return _token_response(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
):
    auth_service.logout(db, refresh_token)
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UpdateProfileRequest, user: CurrentUser, db: DbSession):
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "name" and value is None:
            continue
        setattr(user, field, value)
    db.commit()
    return user


@router.post("/change-password", status_code=204)
def change_password(data: ChangePasswordRequest, user: CurrentUser, db: DbSession, response: Response):
    auth_service.change_password(db, user, data.current_password, data.new_password)
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response


# The report documents profile management under /users/profile; same behaviour as /auth/me.
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/profile", response_model=UserOut)
def get_profile(user: CurrentUser):
    return user


@users_router.put("/profile/update", response_model=UserOut)
@users_router.patch("/profile/update", response_model=UserOut)
@users_router.put("/profile", response_model=UserOut)
@users_router.patch("/profile", response_model=UserOut)
def update_profile(data: UpdateProfileRequest, user: CurrentUser, db: DbSession):
    return update_me(data, user, db)
