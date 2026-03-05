from __future__ import annotations

import threading

import requests

THREAD_LOCAL = threading.local()


def create_session(pool_size: int = 128) -> requests.Session:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=0,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_thread_session(pool_size: int = 128) -> requests.Session:
    session = getattr(THREAD_LOCAL, "session", None)
    if session is not None:
        return session

    session = create_session(pool_size=pool_size)
    THREAD_LOCAL.session = session
    return session
