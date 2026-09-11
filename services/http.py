"""Shared HTTP plumbing for outbound provider calls.

Every provider goes through :func:`get_session` so that a single place owns the
User-Agent, retry policy and timeouts.  AniList and MangaDex both sit behind
Cloudflare and reject the default ``python-requests``/``urllib`` User-Agent with
a 403, so identifying ourselves properly is not optional.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 v2 and v1 expose Retry from different paths
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover - very old urllib3
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

logger = logging.getLogger(__name__)

USER_AGENT = (
    "SpellScroll/2.0 (+https://github.com/MdSadman20040812/SpellScroll) "
    "python-requests"
)

DEFAULT_TIMEOUT = (5, 20)  # (connect, read)

_local = threading.local()


def get_session() -> requests.Session:
    """Return a thread-local session with retries and a real User-Agent."""
    session = getattr(_local, "session", None)
    if session is not None:
        return session

    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    _local.session = session
    return session


class RateLimiter:
    """Minimal blocking rate limiter shared across a provider module.

    AniList allows ~90 requests/minute and MangaDex ~5/second; being a polite
    client here is what keeps the catalog sync from getting throttled halfway.
    """

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last
            sleep_for = self.min_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last = time.monotonic()


def request_json(
    method: str,
    url: str,
    *,
    limiter: Optional[RateLimiter] = None,
    timeout: Any = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> Optional[dict]:
    """Perform a request and decode JSON, returning ``None`` on any failure.

    Providers are best-effort by design: a dead upstream must degrade to the
    next provider in the chain, never raise into a view or a sync command.
    """
    if limiter is not None:
        limiter.wait()
    try:
        response = get_session().request(method, url, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        logger.warning("%s %s failed: %s", method, url, exc)
        return None

    if response.status_code >= 400:
        logger.warning("%s %s returned HTTP %s", method, url, response.status_code)
        return None

    try:
        return response.json()
    except ValueError:
        logger.warning("%s %s returned non-JSON body", method, url)
        return None
