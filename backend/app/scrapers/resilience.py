"""Shared scraping resilience: rate limiting, retry/backoff, proxy rotation (AD-13).

The design point: a long crawl touches thousands of pages, so *some* of them will
fail no matter what -- a transient TCP reset, a slow render, a momentary 502. The
pipeline must treat those as expected, not exceptional. Two layers do that:

  1. `request_with_retry` retries one request a few times with exponential backoff
     (honouring `Retry-After` when the site sends it), so a blip doesn't even
     surface to the caller.
  2. `FailureBudget` lets the *caller* skip an item that still failed after those
     retries, while tracking how many have been skipped -- so one dead page can
     never kill a 2000-page run, but a systemic problem (banned, site down) still
     aborts instead of silently yielding nothing for an hour.

`RateLimiter` is the preventive half: spacing requests out so 429s don't happen in
the first place is strictly better than reacting to them once they do.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Status codes worth retrying: rate limiting, plus the transient server-side 5xx
# family. Notably absent: 403/404 -- those are answers, not blips, and retrying
# them just burns the rate limit budget.
_RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

_RETRY_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class ScrapeAborted(Exception):
    """Too many consecutive failures -- something systemic, stop the run."""


class RateLimiter:
    """Spaces calls at least `delay` apart, with jitter so a crawl doesn't emit a
    machine-perfect request cadence. Async-safe: concurrent callers queue on the lock."""

    def __init__(self, delay: float, *, jitter: float = 0.3) -> None:
        self.delay = delay
        self.jitter = jitter
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < self._next_allowed:
                await asyncio.sleep(self._next_allowed - now)
                now = loop.time()
            self._next_allowed = now + self.delay + random.uniform(0, self.jitter)


class ProxyRotator:
    """Round-robins over configured proxy URLs. Empty config == direct connection,
    which is the default and the norm; this exists so a deployment that *does* have
    real proxies can spread load without touching adapter code."""

    def __init__(self, proxies: list[str] | None = None) -> None:
        if proxies is None:
            raw = get_settings().scraper_proxies
            proxies = [p.strip() for p in raw.split(",") if p.strip()]
        self.proxies = proxies
        self._cycle = itertools.cycle(proxies) if proxies else None

    @property
    def enabled(self) -> bool:
        return self._cycle is not None

    def next_proxy(self) -> str | None:
        return next(self._cycle) if self._cycle else None


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Parse a Retry-After header. Only the delta-seconds form is handled -- the
    HTTP-date form is rare in practice and a wrong parse is worse than falling
    back to our own backoff curve."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw.strip()))
    except ValueError:
        return None


async def request_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    method: str = "GET",
    limiter: RateLimiter | None = None,
    max_retries: int | None = None,
    **kwargs,
) -> httpx.Response:
    """One HTTP request, retried through transient failures.

    Returns the response even on non-retryable error statuses (404 etc) -- deciding
    what a 404 means is the caller's business. Raises the underlying httpx exception
    only if every attempt failed to get a response at all.
    """
    settings = get_settings()
    if max_retries is None:
        max_retries = settings.scraper_max_retries

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        if limiter is not None:
            await limiter.wait()
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in _RETRY_STATUS:
                return response
            if attempt == max_retries:
                return response
            wait = _retry_after_seconds(response) or _backoff(attempt, settings)
            logger.warning(
                "scrape: %s %s -> %s, retry %d/%d in %.1fs",
                method,
                url,
                response.status_code,
                attempt + 1,
                max_retries,
                wait,
            )
        except _RETRY_EXCEPTIONS as exc:
            last_exc = exc
            if attempt == max_retries:
                raise
            wait = _backoff(attempt, settings)
            logger.warning(
                "scrape: %s %s -> %s, retry %d/%d in %.1fs",
                method,
                url,
                type(exc).__name__,
                attempt + 1,
                max_retries,
                wait,
            )
        await asyncio.sleep(wait)

    if last_exc is not None:  # pragma: no cover -- loop always returns or raises first
        raise last_exc
    raise RuntimeError("unreachable")


def _backoff(attempt: int, settings) -> float:
    """Exponential with full jitter. Jitter matters: without it, every retry after a
    shared outage fires simultaneously and re-creates the spike that caused it."""
    ceiling = min(settings.scraper_backoff_base_seconds * (2**attempt), settings.scraper_backoff_max_seconds)
    return random.uniform(ceiling / 2, ceiling)


class FailureBudget:
    """Tracks skipped items so one bad page can't kill a long run, while a sustained
    streak of failures still aborts it.

    Consecutive-failure count (not total) is the abort signal on purpose: 200 scattered
    failures across 5000 pages is a normal crawl, but 25 in a row means we're banned or
    the site is down, and continuing would just hammer it for nothing.
    """

    def __init__(self, max_consecutive: int | None = None) -> None:
        if max_consecutive is None:
            max_consecutive = get_settings().scraper_max_consecutive_failures
        self.max_consecutive = max_consecutive
        self.failed = 0
        self.consecutive = 0

    def record_success(self) -> None:
        self.consecutive = 0

    def record_failure(self, what: str, exc: BaseException) -> None:
        self.failed += 1
        self.consecutive += 1
        logger.warning(
            "scrape: skipping %s after retries (%s: %s) -- %d consecutive, %d total",
            what,
            type(exc).__name__,
            exc,
            self.consecutive,
            self.failed,
        )
        if self.consecutive >= self.max_consecutive:
            raise ScrapeAborted(
                f"aborted after {self.consecutive} consecutive failures "
                f"({self.failed} total); last: {type(exc).__name__}: {exc}"
            ) from exc


async def guarded(
    budget: FailureBudget,
    what: str,
    coro_factory: Callable[[], Awaitable[T]],
) -> T | None:
    """Run one fetch under the failure budget. Returns None if it failed and was
    skipped; re-raises CancelledError (a stop request is not a failure) and
    ScrapeAborted (budget exhausted)."""
    try:
        result = await coro_factory()
    except asyncio.CancelledError:
        raise
    except ScrapeAborted:
        raise
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any per-item failure is skippable
        budget.record_failure(what, exc)
        return None
    budget.record_success()
    return result
