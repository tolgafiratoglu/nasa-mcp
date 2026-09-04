"""NASA adapter unit tests — mocked HTTP + fixtures, no live NASA."""

from __future__ import annotations

import httpx2
import pytest

from nasa_mcp.clients.apod import ApodClient
from nasa_mcp.clients.base import NASAError
from nasa_mcp.clients.donki import DonkiClient
from nasa_mcp.clients.eonet import EonetClient
from nasa_mcp.clients.neows import NeoWsClient
from tests.fixtures import load_fixture


async def _noop_sleep(_: float) -> None:
    return None


def _http(handler) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler), timeout=5.0)


# --- NeoWs -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_neows_search_parses_feed():
    feed = load_fixture("neows_feed.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "/neo/rest/v1/feed" in str(request.url)
        return httpx2.Response(200, json=feed)

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        rocks = await client.search_asteroids("2024-01-01", "2024-01-07")
        assert len(rocks) == 2
        assert rocks[0].id == "2000433"
        assert rocks[1].potentially_hazardous is True
        assert rocks[1].close_approach is not None
        assert rocks[1].close_approach.miss_distance_km == 500000.0
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_hazardous_only_filter():
    feed = load_fixture("neows_feed.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=feed)

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        rocks = await client.search_asteroids(
            "2024-01-01", "2024-01-07", hazardous_only=True
        )
        assert len(rocks) == 1
        assert rocks[0].id == "2465633"
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_empty_feed_is_success():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={"element_count": 0, "near_earth_objects": {}},
        )

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        rocks = await client.search_asteroids("2024-01-01", "2024-01-07")
        assert rocks == []
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_lookup_parses_detail():
    payload = load_fixture("neows_lookup.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "/neo/rest/v1/neo/2000433" in str(request.url)
        return httpx2.Response(200, json=payload)

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        detail = await client.get_asteroid("2000433")
        assert detail.id == "2000433"
        assert detail.absolute_magnitude == 10.31
        assert detail.orbital_period_days == 643.0
        assert len(detail.close_approaches) == 2
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_unknown_asteroid_404():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, text="Not Found")

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        with pytest.raises(NASAError) as exc_info:
            await client.get_asteroid("99999999")
        assert exc_info.value.error_type == "NOT_FOUND"
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_malformed_lookup_is_no_data():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"id": "x"})

    http = _http(handler)
    client = NeoWsClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        with pytest.raises(NASAError) as exc_info:
            await client.get_asteroid("x")
        assert exc_info.value.error_type == "NO_DATA"
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_neows_invalid_date_range_rejected():
    http = _http(lambda r: httpx2.Response(200, json={}))
    client = NeoWsClient(http_client=http, api_key="TEST")
    try:
        with pytest.raises(NASAError) as exc_info:
            await client.search_asteroids("2024-01-01", "2024-01-20")
        assert exc_info.value.error_type == "INVALID_PARAMETERS"
    finally:
        await http.aclose()


# --- APOD ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apod_parses_fixture():
    payload = load_fixture("apod.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "/planetary/apod" in str(request.url)
        return httpx2.Response(200, json=payload)

    http = _http(handler)
    client = ApodClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        result = await client.get_apod(date="2024-01-15")
        assert result.title == "The Lagoon Nebula"
        assert result.media_type == "image"
        assert result.hdurl is not None
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_apod_unknown_media_type_normalized():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "title": "Odd",
                "date": "2024-01-01",
                "explanation": "x",
                "url": "https://example.com/x",
                "media_type": "other",
            },
        )

    http = _http(handler)
    client = ApodClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        result = await client.get_apod()
        assert result.media_type == "image"
    finally:
        await http.aclose()


# --- DONKI -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_donki_single_type_from_fixture():
    cme = load_fixture("donki_cme.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "/DONKI/CME" in str(request.url)
        return httpx2.Response(200, json=cme)

    http = _http(handler)
    client = DonkiClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        events = await client.get_events("CME", "2024-01-01", "2024-01-07")
        assert len(events) == 1
        assert events[0].event_type == "CME"
        assert events[0].event_id.startswith("2024-01-02")
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_donki_invalid_type_rejected():
    http = _http(lambda r: httpx2.Response(200, json=[]))
    client = DonkiClient(http_client=http, api_key="TEST")
    try:
        with pytest.raises(NASAError) as exc_info:
            await client.get_events("BOGUS", "2024-01-01", "2024-01-07")
        assert exc_info.value.error_type == "INVALID_PARAMETERS"
    finally:
        await http.aclose()


# --- EONET -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_eonet_parses_events():
    payload = load_fixture("eonet_events.json")

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "eonet.gsfc.nasa.gov" in str(request.url)
        return httpx2.Response(200, json=payload)

    http = _http(handler)
    client = EonetClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        events = await client.get_events(days=7, status="open")
        assert len(events) == 2
        assert events[0].id == "EONET_123"
        assert events[0].status == "open"
        assert events[1].status == "closed"
        assert events[0].geometry[0].coordinates == [-120.5, 37.2]
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_eonet_empty_events_is_success():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"events": []})

    http = _http(handler)
    client = EonetClient(http_client=http, api_key="TEST")
    client._sleep = _noop_sleep
    try:
        events = await client.get_events()
        assert events == []
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_eonet_invalid_bbox_rejected():
    http = _http(lambda r: httpx2.Response(200, json={"events": []}))
    client = EonetClient(http_client=http, api_key="TEST")
    try:
        with pytest.raises(NASAError) as exc_info:
            await client.get_events(bbox="not-a-bbox")
        assert exc_info.value.error_type == "INVALID_PARAMETERS"
    finally:
        await http.aclose()
