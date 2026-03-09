from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import requests

from src.auth.cas_client import ZJUAuthClient
from src.common.http import create_session
from src.common.utils import now_utc_iso


@dataclass
class TokenRefreshSnapshot:
    token: str
    last_refresh_at_utc: str
    last_refresh_error: str


class LoginTokenManager:
    """Thread-safe token holder with refresh cooldown on repeated failures."""

    def __init__(
        self,
        *,
        auth_client: ZJUAuthClient,
        username: str,
        password: str,
        center_course_id: int,
        authcode: str,
        refresh_cooldown_sec: float = 30.0,
        session_factory: Callable[[], requests.Session] | None = None,
    ) -> None:
        self._auth_client = auth_client
        self._username = username
        self._password = password
        self._center_course_id = int(center_course_id)
        self._authcode = str(authcode or "")
        self._refresh_cooldown_sec = max(0.0, float(refresh_cooldown_sec))
        self._session_factory = session_factory or (lambda: create_session(pool_size=8))

        self._lock = threading.Lock()
        self._token = ""
        self._last_refresh_at_utc = ""
        self._last_refresh_error = ""
        self._last_failure_mono = 0.0

    def get_token(self) -> str:
        with self._lock:
            return self._token

    def snapshot(self) -> TokenRefreshSnapshot:
        with self._lock:
            return TokenRefreshSnapshot(
                token=self._token,
                last_refresh_at_utc=self._last_refresh_at_utc,
                last_refresh_error=self._last_refresh_error,
            )

    def refresh(self, reason: str, *, force: bool = False) -> tuple[bool, str]:
        refresh_reason = str(reason or "unspecified")
        now_mono = time.monotonic()

        with self._lock:
            if not force and self._last_failure_mono > 0:
                elapsed = now_mono - self._last_failure_mono
                if elapsed < self._refresh_cooldown_sec:
                    remain = self._refresh_cooldown_sec - elapsed
                    msg = (
                        f"refresh cooldown active ({remain:.1f}s remaining); "
                        f"last_error={self._last_refresh_error or 'unknown'}"
                    )
                    return False, msg

            try:
                session = self._session_factory()
                try:
                    token = self._auth_client.login_and_get_token(
                        session=session,
                        username=self._username,
                        password=self._password,
                        center_course_id=self._center_course_id,
                        authcode=self._authcode,
                    )
                finally:
                    try:
                        session.close()
                    except Exception:
                        pass
                if not token:
                    raise RuntimeError("login succeeded but token is empty")
            except Exception as exc:
                self._last_refresh_at_utc = now_utc_iso()
                self._last_refresh_error = f"{refresh_reason}: {exc}"
                self._last_failure_mono = now_mono
                return False, self._last_refresh_error

            self._token = token
            self._last_refresh_at_utc = now_utc_iso()
            self._last_refresh_error = ""
            self._last_failure_mono = 0.0
            return True, ""
