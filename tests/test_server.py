"""MCP contract tests using in-memory Client(mcp)."""

import os

import pytest
from mcp import Client

from nasa_mcp.server import mcp

has_nasa_key = os.environ.get("NASA_API_KEY", "DEMO_KEY") != "DEMO_KEY"
skip_without_key = pytest.mark.skipif(not has_nasa_key, reason="No NASA API key; DEMO_KEY rate-limited")


@pytest.mark.asyncio
async def test_tools_list_contains_apod():
    async with Client(mcp) as client:
        result = await client.list_tools()
        tool_names = [t.name for t in result.tools]
        assert "get_apod" in tool_names


@pytest.mark.asyncio
async def test_get_apod_returns_structured_content():
    """Integration test: calls the real NASA APOD API with DEMO_KEY."""
    async with Client(mcp) as client:
        result = await client.call_tool("get_apod", {})

        assert not result.is_error
        assert result.structured_content is not None
        assert "title" in result.structured_content
        assert "explanation" in result.structured_content
        assert "url" in result.structured_content
        assert "date" in result.structured_content
        assert "media_type" in result.structured_content


@pytest.mark.asyncio
async def test_get_apod_with_specific_date():
    """Fetch a known historical APOD to verify date parameter works."""
    async with Client(mcp) as client:
        result = await client.call_tool("get_apod", {"date": "2024-01-01"})

        assert not result.is_error
        assert result.structured_content is not None
        assert result.structured_content["date"] == "2024-01-01"


@pytest.mark.asyncio
async def test_get_apod_invalid_date_returns_error():
    """NASA API should reject obviously invalid dates."""
    async with Client(mcp) as client:
        result = await client.call_tool("get_apod", {"date": "not-a-date"})

        assert result.is_error


@pytest.mark.asyncio
async def test_tools_list_contains_asteroid_tools():
    async with Client(mcp) as client:
        result = await client.list_tools()
        tool_names = [t.name for t in result.tools]
        assert "search_asteroids" in tool_names
        assert "get_asteroid" in tool_names


@pytest.mark.asyncio
async def test_search_asteroids():
    """Integration test: search NEOs for a known past week."""
    async with Client(mcp) as client:
        result = await client.call_tool("search_asteroids", {
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
        })

        assert not result.is_error
        assert result.structured_content is not None
        items = result.structured_content.get("result", [])
        assert len(items) > 0
        assert "name" in items[0]
        assert "potentially_hazardous" in items[0]


@pytest.mark.asyncio
async def test_search_asteroids_hazardous_only():
    """Hazardous filter should return subset."""
    async with Client(mcp) as client:
        result = await client.call_tool("search_asteroids", {
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "hazardous_only": True,
        })

        assert not result.is_error
        items = result.structured_content.get("result", [])
        for item in items:
            assert item["potentially_hazardous"] is True


@pytest.mark.asyncio
async def test_search_asteroids_invalid_range():
    """Date range > 7 days should fail."""
    async with Client(mcp) as client:
        result = await client.call_tool("search_asteroids", {
            "start_date": "2024-01-01",
            "end_date": "2024-01-15",
        })

        assert result.is_error
