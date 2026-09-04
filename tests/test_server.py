"""MCP contract tests via Client(mcp) — mocked NASA clients, no live HTTP."""

from __future__ import annotations

import pytest
from mcp import Client

from nasa_mcp.clients.apod import ApodClient
from nasa_mcp.clients.base import NASAError
from nasa_mcp.clients.neows import NeoWsClient
from nasa_mcp.models import APODResult, Asteroid, CloseApproach
from nasa_mcp.server import mcp

EXPECTED_TOOLS = {
    "get_apod",
    "search_asteroids",
    "get_asteroid",
    "get_space_weather",
    "get_earth_events",
}


@pytest.mark.asyncio
async def test_tools_list_contains_all_five():
    async with Client(mcp) as client:
        result = await client.list_tools()
        names = {t.name for t in result.tools}
        assert EXPECTED_TOOLS <= names


@pytest.mark.asyncio
async def test_all_tools_read_only_hint():
    async with Client(mcp) as client:
        result = await client.list_tools()
        for tool in result.tools:
            if tool.name in EXPECTED_TOOLS:
                assert tool.annotations is not None
                assert tool.annotations.read_only_hint is True


@pytest.mark.asyncio
async def test_resources_and_prompt_listed():
    async with Client(mcp) as client:
        resources = await client.list_resources()
        uris = {str(r.uri) for r in resources.resources}
        assert "nasa://glossary" in uris
        assert "nasa://eonet/categories" in uris

        prompts = await client.list_prompts()
        names = {p.name for p in prompts.prompts}
        assert "daily_mission_briefing" in names

        prompt = await client.get_prompt("daily_mission_briefing")
        text = " ".join(
            block.text
            for msg in prompt.messages
            for block in (msg.content if isinstance(msg.content, list) else [msg.content])
            if hasattr(block, "text")
        )
        assert "search_asteroids" in text
        assert "ALL" in text or "event_type=ALL" in text
        assert "get_asteroid" in text


@pytest.mark.asyncio
async def test_glossary_resource_readable():
    async with Client(mcp) as client:
        result = await client.read_resource("nasa://glossary")
        body = "".join(
            c.text for c in result.contents if hasattr(c, "text") and c.text
        )
        assert "NEO" in body
        assert "CME" in body


@pytest.mark.asyncio
async def test_search_asteroids_structured_content_includes_id(monkeypatch):
    async def fake_search(self, start_date, end_date, *, hazardous_only=False):
        return [
            Asteroid(
                id="2000433",
                name="Eros",
                potentially_hazardous=False,
                diameter_min_m=10.0,
                diameter_max_m=20.0,
                close_approach=CloseApproach(
                    date="2024-01-02",
                    miss_distance_km=1e6,
                    relative_velocity_kmh=40000.0,
                ),
            )
        ]

    monkeypatch.setattr(NeoWsClient, "search_asteroids", fake_search)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_asteroids",
            {"start_date": "2024-01-01", "end_date": "2024-01-07"},
        )
        assert not result.is_error
        assert result.structured_content is not None
        items = result.structured_content.get("result", [])
        assert items[0]["id"] == "2000433"


@pytest.mark.asyncio
async def test_nasa_failure_is_tool_error(monkeypatch):
    async def fake_fail(self, date=None):
        raise NASAError("UPSTREAM_ERROR", "simulated failure", retryable=True)

    monkeypatch.setattr(ApodClient, "get_apod", fake_fail)

    async with Client(mcp) as client:
        result = await client.call_tool("get_apod", {})
        assert result.is_error is True
        assert result.structured_content is None


@pytest.mark.asyncio
async def test_get_apod_structured_shape(monkeypatch):
    async def fake_apod(self, date=None):
        return APODResult(
            title="Test",
            date=date or "2024-01-01",
            explanation="Explain",
            url="https://example.com/a.jpg",
            media_type="image",
        )

    monkeypatch.setattr(ApodClient, "get_apod", fake_apod)

    async with Client(mcp) as client:
        result = await client.call_tool("get_apod", {"date": "2024-01-01"})
        assert not result.is_error
        sc = result.structured_content
        assert sc["title"] == "Test"
        assert sc["media_type"] == "image"
        assert sc["date"] == "2024-01-01"


@pytest.mark.asyncio
async def test_search_asteroids_empty_list_is_success(monkeypatch):
    async def fake_empty(self, start_date, end_date, *, hazardous_only=False):
        return []

    monkeypatch.setattr(NeoWsClient, "search_asteroids", fake_empty)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_asteroids",
            {"start_date": "2024-01-01", "end_date": "2024-01-07"},
        )
        assert not result.is_error
        assert result.structured_content.get("result") == []


@pytest.mark.asyncio
async def test_search_asteroids_invalid_range_is_error(monkeypatch):
    async def fake_invalid(self, start_date, end_date, *, hazardous_only=False):
        raise NASAError(
            "INVALID_PARAMETERS",
            "NeoWs date range limited to 7 days.",
            retryable=False,
        )

    monkeypatch.setattr(NeoWsClient, "search_asteroids", fake_invalid)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_asteroids",
            {"start_date": "2024-01-01", "end_date": "2024-01-20"},
        )
        assert result.is_error is True


@pytest.mark.asyncio
async def test_get_asteroid_unknown_is_error(monkeypatch):
    async def fake_missing(self, asteroid_id: str):
        raise NASAError(
            "NOT_FOUND",
            f"NASA resource not found: /neo/rest/v1/neo/{asteroid_id}",
            retryable=False,
        )

    monkeypatch.setattr(NeoWsClient, "get_asteroid", fake_missing)

    async with Client(mcp) as client:
        result = await client.call_tool("get_asteroid", {"asteroid_id": "99999999"})
        assert result.is_error is True
