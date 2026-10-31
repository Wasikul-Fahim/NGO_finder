import time
from collections import defaultdict, deque
from threading import Lock

from app.core.config import get_settings


class LoginRateLimiter:
    """In-memory sliding window of failed logins, keyed by IP and by email.

    Process-local: with several workers, back it with Redis (or slowapi's storage).
    """

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float, window: int) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > window:
            q.popleft()
        return q

    def retry_after(self, keys: list[str]) -> int:
        """Seconds until a blocked key frees up, or 0 if not blocked."""
        s = get_settings()
        now = time.monotonic()
        wait = 0
        with self._lock:
            for key in keys:
                q = self._prune(key, now, s.login_window_seconds)
                if len(q) >= s.login_max_attempts:
                    wait = max(wait, int(s.login_window_seconds - (now - q[0])) + 1)
        return wait

    def record_failure(self, keys: list[str]) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                self._failures[key].append(now)

    def reset(self, keys: list[str] | None = None) -> None:
        with self._lock:
            if keys is None:
                self._failures.clear()
            else:
                for key in keys:
                    self._failures.pop(key, None)


login_limiter = LoginRateLimiter()
