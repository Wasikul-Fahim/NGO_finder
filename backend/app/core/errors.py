import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        self.headers = headers


def _body(code: str, message: str, fields: dict[str, str] | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


def validation_fields(errors) -> dict[str, str]:
    fields: dict[str, str] = {}
    for err in errors:
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        key = ".".join(loc) or "_"
        message = err["msg"].removeprefix("Value error, ")
        fields.setdefault(key, message)
    return fields


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            _body(exc.code, exc.message, exc.fields), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException):
        code = _STATUS_CODES.get(exc.status_code, "ERROR")
        return JSONResponse(
            _body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            _body(
                "VALIDATION_ERROR",
                "Please correct the highlighted fields.",
                validation_fields(exc.errors()),
            ),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(_body("INTERNAL_ERROR", "Something went wrong."), status_code=500)


def not_found(what: str = "Resource") -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} not found.")


def forbidden(message: str = "You do not have permission to do this.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def conflict(message: str) -> AppError:
    return AppError(409, "CONFLICT", message)


def unauthorized(message: str = "Not authenticated.") -> AppError:
    return AppError(
        401, "UNAUTHORIZED", message, headers={"WWW-Authenticate": "Bearer"}
    )
