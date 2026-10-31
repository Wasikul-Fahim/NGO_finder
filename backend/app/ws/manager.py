"""Tracks live WebSocket connections per user and pushes payloads to them.

`publish` is safe to call from any thread (sync endpoints run in a worker pool) and never raises:
live delivery is best-effort, the persisted notification is the source of truth.
"""
import asyncio
import logging
from threading import Lock

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[int, set[tuple[WebSocket, asyncio.AbstractEventLoop]]] = {}
        self._lock = Lock()

    def add(self, user_id: int, ws: WebSocket, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._conns.setdefault(user_id, set()).add((ws, loop))

    def remove(self, user_id: int, ws: WebSocket) -> None:
        with self._lock:
            conns = self._conns.get(user_id, set())
            self._conns[user_id] = {c for c in conns if c[0] is not ws}
            if not self._conns[user_id]:
                del self._conns[user_id]

    def connected_users(self) -> set[int]:
        with self._lock:
            return set(self._conns)

    async def _send(self, user_id: int, ws: WebSocket, data: dict) -> None:
        try:
            await ws.send_json(data)
        except Exception:  # client went away mid-send
            logger.debug("Dropping dead socket for user %s", user_id, exc_info=True)
            self.remove(user_id, ws)

    def publish(self, payloads: list[dict]) -> None:
        for payload in payloads:
            user_id = payload["user_id"]
            with self._lock:
                targets = list(self._conns.get(user_id, ()))
            for ws, loop in targets:
                try:
                    asyncio.run_coroutine_threadsafe(self._send(user_id, ws, payload["data"]), loop)
                except Exception:
                    logger.warning("Could not schedule live delivery to user %s", user_id, exc_info=True)
                    self.remove(user_id, ws)


manager = ConnectionManager()
