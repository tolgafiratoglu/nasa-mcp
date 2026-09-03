"""Base NASA API client with shared HTTP logic, caching, and error handling."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx2
from cachetools import TTLCache

logger = logging.getLogger(__name__)

NASA_BASE_URL = "https://api.nasa.gov"

# Rate-limit: DEMO_KEY = 30/hour, 50/day. Registered key = 1000/hour.
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
RETRY_AFTER_CAP_SECONDS = 10.0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

SleepFn = Callable[[float], Awaitable[None]]


class NASAError(Exception):
    """Structured error from a NASA API call."""

    def __init__(self, error_type: str, message: str, retryable: bool = False):
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        super().__init__(f"[{error_type}] {message}")


def _safe_error_text(text: str, api_key: str) -> str:
    """Strip API key material from error/log strings."""
    if not api_key:
        return text
    return text.replace(api_key, "[REDACTED]")


class BaseNASAClient:
    """Shared HTTP infrastructure for all NASA API adapters.

    Handles API key injection, timeouts, retries with backoff,
    per-client TTL caching, and structured error mapping.

    Pass an ``httpx2.AsyncClient`` to share connections across adapters
    (lifespan) or inject ``MockTransport`` in tests. When omitted, a
    client is created and owned by this instance.
    """

    def __init__(
        self,
        *,
        http_client: httpx2.AsyncClient | None = None,
        api_key: str | None = None,
        cache_ttl: int = 900,
        cache_maxsize: int = 128,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_after_cap: float = RETRY_AFTER_CAP_SECONDS,
        sleep: SleepFn | None = None,
    ):
        self._owns_client = http_client is None
        self._http = http_client or httpx2.AsyncClient(timeout=DEFAULT_TIMEOUT)
        self._api_key = (
            api_key if api_key is not None else os.environ.get("NASA_API_KEY", "DEMO_KEY")
        )
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._max_retries = max_retries
        self._retry_after_cap = retry_after_cap
        self._sleep: SleepFn = sleep or asyncio.sleep

    async def aclose(self) -> None:
        """Close the HTTP client if this instance owns it."""
        if self._owns_client:
            await self._http.aclose()

    def _cache_key(self, path: str, params: dict[str, Any]) -> str:
        sorted_params = sorted((k, v) for k, v in params.items() if k != "api_key")
        return f"{path}|{sorted_params}"

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a GET request to a NASA API endpoint with caching and retries.

        Returns parsed JSON. Raises NASAError on failure.
        Failed responses are never cached.
        """
        params = dict(params or {})
        params["api_key"] = self._api_key

        cache_key = self._cache_key(path, params)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit: %s", path)
            return cached

        url = f"{NASA_BASE_URL}{path}" if path.startswith("/") else path

        last_error: NASAError | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._http.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    self._cache[cache_key] = data
                    try:
                        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
                        logger.debug("Cache miss, fetched: %s (%dms)", path, elapsed_ms)
                    except RuntimeError:
                        logger.debug("Cache miss, fetched: %s", path)
                    return data

                if response.status_code == 429:
                    raw_retry = response.headers.get("Retry-After", "60")
                    try:
                        retry_after = min(float(raw_retry), self._retry_after_cap)
                    except ValueError:
                        retry_after = self._retry_after_cap
                    logger.warning(
                        "NASA rate limit hit on %s (attempt %d), sleep=%.1fs",
                        path,
                        attempt,
                        retry_after,
                    )
                    if attempt == self._max_retries:
                        raise NASAError(
                            "UPSTREAM_RATE_LIMIT",
                            f"NASA API rate limit exceeded on {path}",
                            retryable=True,
                        )
                    await self._sleep(retry_after)
                    continue

                if response.status_code in RETRY_STATUS_CODES:
                    logger.warning(
                        "NASA %d on %s (attempt %d)",
                        response.status_code,
                        path,
                        attempt,
                    )
                    if attempt == self._max_retries:
                        raise NASAError(
                            "UPSTREAM_ERROR",
                            f"NASA API returned {response.status_code} on {path}",
                            retryable=True,
                        )
                    await self._sleep(min(2**attempt, self._retry_after_cap))
                    continue

                if response.status_code == 404:
                    raise NASAError(
                        "NOT_FOUND",
                        f"NASA resource not found: {path}",
                        retryable=False,
                    )

                raise NASAError(
                    "UPSTREAM_ERROR",
                    f"NASA API returned {response.status_code} on {path}",
                    retryable=False,
                )

            except NASAError:
                raise

            except httpx2.TimeoutException:
                last_error = NASAError(
                    "UPSTREAM_TIMEOUT",
                    f"NASA API timeout on {path}",
                    retryable=True,
                )
                logger.warning("Timeout on %s (attempt %d)", path, attempt)
                if attempt == self._max_retries:
                    raise last_error
                await self._sleep(min(2**attempt, self._retry_after_cap))

            except httpx2.HTTPError as exc:
                safe = _safe_error_text(str(exc), self._api_key)
                last_error = NASAError(
                    "UPSTREAM_ERROR",
                    f"HTTP error on {path}: {safe}",
                    retryable=True,
                )
                logger.warning("HTTP error on %s (attempt %d): %s", path, attempt, safe)
                if attempt == self._max_retries:
                    raise last_error
                await self._sleep(min(2**attempt, self._retry_after_cap))

        raise last_error or NASAError(
            "UPSTREAM_ERROR",
            f"All retries exhausted for {path}",
            retryable=False,
        )
