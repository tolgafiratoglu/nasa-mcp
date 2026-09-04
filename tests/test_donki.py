"""DONKI ALL fan-out contract tests — mocked HTTP only."""

from __future__ import annotations

import httpx2
import pytest

from nasa_mcp.clients.donki import DonkiClient


async def _noop_sleep(_: float) -> None:
    return None


@pytest.mark.asyncio
async def test_donki_all_fans_out_and_sorts_newest_first():
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/CME"):
            return httpx2.Response(
                200,
                json=[{"activityID": "cme-1", "startTime": "2024-01-01T00:00Z"}],
            )
        if path.endswith("/FLR"):
            return httpx2.Response(
                200,
                json=[{"flrID": "flr-1", "beginTime": "2024-01-03T00:00Z"}],
            )
        return httpx2.Response(200, json=[])

    transport = httpx2.MockTransport(handler)
    http = httpx2.AsyncClient(transport=transport, timeout=5.0)
    client = DonkiClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        events = await client.get_events("ALL", "2024-01-01", "2024-01-07")
        assert len(events) == 2
        assert events[0].event_type == "FLR"
        assert events[1].event_type == "CME"
        assert any(p.endswith("/CME") for p in calls)
        assert any(p.endswith("/FLR") for p in calls)
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_donki_empty_list_is_success():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=[])

    transport = httpx2.MockTransport(handler)
    http = httpx2.AsyncClient(transport=transport, timeout=5.0)
    client = DonkiClient(http_client=http, api_key="TEST")
    try:
        events = await client.get_events("CME", "2024-01-01", "2024-01-07")
        assert events == []
    finally:
        await http.aclose()
