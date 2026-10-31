import asyncio
import logging
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.core.security import decode_access_token
from app.models import Notification, NotificationStatus, User
from app.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()

UNAUTHORIZED = 4401


def _authenticate(token: str | None, factory: Callable) -> tuple[int, int] | None:
    """Returns (user_id, unread_count) for a valid token of an active user, else None."""
    if not token:
        return None
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    with factory() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        unread = db.scalar(select(func.count()).where(
            Notification.user_id == user_id, Notification.status == NotificationStatus.UNREAD)) or 0
        return user_id, unread


@router.websocket("/ws/notifications")
async def notifications_socket(
    websocket: WebSocket,
    factory: Annotated[Callable, Depends(get_session_factory)],
    token: Annotated[str | None, Query()] = None,
):
    # Authenticate BEFORE accepting: a bad token never gets a live socket.
    auth = await run_in_threadpool(_authenticate, token, factory)
    if auth is None:
        await websocket.close(code=UNAUTHORIZED)
        return
    user_id, unread = auth
    await websocket.accept()
    manager.add(user_id, websocket, asyncio.get_running_loop())
    try:
        await websocket.send_json({"event": "connected", "unread": unread})
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("Notification socket closed with error", exc_info=True)
    finally:
        manager.remove(user_id, websocket)
