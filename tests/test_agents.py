"""Agent layer unit tests — no live LLM or NASA calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.config import (
    ASTEROID_TOOLS,
    COMMANDER_MCP_TOOLS,
    EARTH_TOOLS,
    WEATHER_TOOLS,
    filter_tools_by_name,
    tool_name,
)


def _fake_tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(tool_name=name)


def test_tool_name_from_tool_name_attr():
    assert tool_name(_fake_tool("search_asteroids")) == "search_asteroids"


def test_tool_name_from_name_attr():
    assert tool_name(SimpleNamespace(name="get_apod")) == "get_apod"


def test_filter_tools_by_name_enforces_whitelist():
    tools = [
        _fake_tool("search_asteroids"),
        _fake_tool("get_asteroid"),
        _fake_tool("get_apod"),
        _fake_tool("get_space_weather"),
    ]
    selected = filter_tools_by_name(tools, ASTEROID_TOOLS)
    assert {tool_name(t) for t in selected} == set(ASTEROID_TOOLS)


def test_filter_tools_by_name_rejects_missing():
    tools = [_fake_tool("search_asteroids")]
    with pytest.raises(RuntimeError, match="missing"):
        filter_tools_by_name(tools, ASTEROID_TOOLS)


def test_whitelist_sets_are_disjoint_for_specialists():
    """Commander MCP tools must not overlap specialist NASA tools."""
    specialist = set(ASTEROID_TOOLS) | set(WEATHER_TOOLS) | set(EARTH_TOOLS)
    assert set(COMMANDER_MCP_TOOLS).isdisjoint(specialist)
    assert set(COMMANDER_MCP_TOOLS) == {"get_apod"}
