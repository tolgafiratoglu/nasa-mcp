"""Mocked unit tests for BaseNASAClient — no live NASA calls."""

from __future__ import annotations

import json
from typing import Any

import httpx2
import pytest

from nasa_mcp.clients.base import NASAError, BaseNASAClient, RETRY_AFTER_CAP_SECONDS


SECRET = "super-secret-nasa-key"


async def _noop_sleep(_: float) -> None:
    return None


def _make_client(
    handler,
    *,
    max_retries: int = 3,
    retry_after_cap: float = RETRY_AFTER_CAP_SECONDS,
) -> BaseNASAClient:
    transport = httpx2.MockTransport(handler)
    http = httpx2.AsyncClient(transport=transport, timeout=5.0)
    return BaseNASAClient(
        http_client=http,
        api_key=SECRET,
        cache_ttl=60,
        max_retries=max_retries,
        retry_after_cap=retry_after_cap,
        sleep=_noop_sleep,
    )


@pytest.mark.asyncio
async def test_200_success():
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(200, json={"ok": True, "path": request.url.path})

    client = _make_client(handler)
    try:
        data = await client._request("/planetary/apod")
        assert data == {"ok": True, "path": "/planetary/apod"}
        assert calls["n"] == 1
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_success_is_cached():
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(200, json={"n": calls["n"]})

    client = _make_client(handler)
    try:
        first = await client._request("/planetary/apod")
        second = await client._request("/planetary/apod")
        assert first == second == {"n": 1}
        assert calls["n"] == 1
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_failed_response_not_cached():
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx2.Response(500, text="boom")
        return httpx2.Response(200, json={"recovered": True})

    client = _make_client(handler, max_retries=3)
    try:
        data = await client._request("/planetary/apod")
        assert data == {"recovered": True}
        assert calls["n"] == 3

        # After success, next call should hit cache (no 4th upstream call)
        again = await client._request("/planetary/apod")
        assert again == {"recovered": True}
        assert calls["n"] == 3
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_429_retries_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(429, headers={"Retry-After": "2"}, text="rate")
        return httpx2.Response(200, json={"ok": True})

    transport = httpx2.MockTransport(handler)
    http = httpx2.AsyncClient(transport=transport, timeout=5.0)
    client = BaseNASAClient(
        http_client=http,
        api_key=SECRET,
        max_retries=3,
        sleep=record_sleep,
    )
    try:
        data = await client._request("/neo/rest/v1/feed")
        assert data == {"ok": True}
        assert calls["n"] == 2
        assert sleeps == [2.0]
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_429_exhausted():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, headers={"Retry-After": "1"}, text="rate")

    client = _make_client(handler, max_retries=3)
    try:
        with pytest.raises(NASAError) as exc_info:
            await client._request("/neo/rest/v1/feed")
        err = exc_info.value
        assert err.error_type == "UPSTREAM_RATE_LIMIT"
        assert err.retryable is True
        assert SECRET not in str(err)
        assert SECRET not in err.message
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_retry_after_cap_applied():
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, headers={"Retry-After": "99999"}, text="rate")

    transport = httpx2.MockTransport(handler)
    http = httpx2.AsyncClient(transport=transport, timeout=5.0)
    client = BaseNASAClient(
        http_client=http,
        api_key=SECRET,
        max_retries=2,
        retry_after_cap=10.0,
        sleep=record_sleep,
    )
    try:
        with pytest.raises(NASAError) as exc_info:
            await client._request("/planetary/apod")
        assert exc_info.value.error_type == "UPSTREAM_RATE_LIMIT"
        assert sleeps == [10.0]
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_500_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx2.Response(500, text="err")
        return httpx2.Response(200, json={"ok": True})

    client = _make_client(handler)
    try:
        data = await client._request("/DONKI/CME")
        assert data == {"ok": True}
        assert calls["n"] == 2
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_500_exhausted():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, text="unavailable")

    client = _make_client(handler, max_retries=3)
    try:
        with pytest.raises(NASAError) as exc_info:
            await client._request("/DONKI/FLR")
        assert exc_info.value.error_type == "UPSTREAM_ERROR"
        assert exc_info.value.retryable is True
        assert SECRET not in str(exc_info.value)
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_timeout_maps_to_nasa_error():
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("simulated timeout", request=request)

    client = _make_client(handler, max_retries=2)
    try:
        with pytest.raises(NASAError) as exc_info:
            await client._request("/planetary/apod")
        assert exc_info.value.error_type == "UPSTREAM_TIMEOUT"
        assert exc_info.value.retryable is True
        assert SECRET not in str(exc_info.value)
        assert SECRET not in exc_info.value.message
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_api_key_not_in_error_from_http_exception():
    """Ensure redaction works even if underlying error text mentions the key."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(
            f"failed connecting with key={SECRET}",
            request=request,
        )

    client = _make_client(handler, max_retries=1)
    try:
        with pytest.raises(NASAError) as exc_info:
            await client._request("/planetary/apod")
        assert SECRET not in str(exc_info.value)
        assert SECRET not in exc_info.value.message
        assert "[REDACTED]" in exc_info.value.message
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
async def test_different_params_different_cache_entries():
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        date = request.url.params.get("date", "none")
        calls.append(date)
        return httpx2.Response(200, json={"date": date})

    client = _make_client(handler)
    try:
        a = await client._request("/planetary/apod", {"date": "2024-01-01"})
        b = await client._request("/planetary/apod", {"date": "2024-01-02"})
        a2 = await client._request("/planetary/apod", {"date": "2024-01-01"})
        assert a["date"] == "2024-01-01"
        assert b["date"] == "2024-01-02"
        assert a2["date"] == "2024-01-01"
        assert calls == ["2024-01-01", "2024-01-02"]
    finally:
        await client._http.aclose()
