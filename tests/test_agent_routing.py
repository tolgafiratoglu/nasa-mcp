"""Deterministic routing + whitelist evaluation — no live LLM/NASA."""

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
from agents.routing import (
    assert_no_unnecessary_calls,
    classify_query,
    expected_route,
)


def _fake_tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(tool_name=name)


ALL_MCP = [
    _fake_tool("search_asteroids"),
    _fake_tool("get_asteroid"),
    _fake_tool("get_space_weather"),
    _fake_tool("get_earth_events"),
    _fake_tool("get_apod"),
]


def test_classify_asteroid_query():
    assert classify_query("Any hazardous asteroids this week?") == "asteroids"


def test_classify_apod_query():
    assert classify_query("What's today's astronomy picture?") == "apod_only"


def test_classify_full_briefing():
    assert (
        classify_query("Give me a mission briefing for the next 7 days.")
        == "full_briefing"
    )


def test_expected_route_asteroids_uses_analyst_only():
    exp = expected_route("Are there any hazardous asteroids approaching Earth?")
    assert exp.specialists == frozenset({"asteroid_analyst"})
    assert "get_apod" not in exp.commander_mcp_tools
    assert "space_weather_analyst" in exp.forbidden_specialists


def test_expected_route_apod_forbids_specialists():
    exp = expected_route("What's today's space picture?")
    assert exp.commander_mcp_tools == frozenset({"get_apod"})
    assert exp.specialists == frozenset()
    assert "asteroid_analyst" in exp.forbidden_specialists


def test_expected_route_full_briefing():
    exp = expected_route("Give me a mission briefing for this week")
    assert exp.specialists == frozenset(
        {"asteroid_analyst", "space_weather_analyst", "earth_events_analyst"}
    )
    assert exp.commander_mcp_tools == frozenset({"get_apod"})


def test_assert_no_unnecessary_calls_detects_extra_specialist():
    with pytest.raises(AssertionError, match="Unnecessary"):
        assert_no_unnecessary_calls(
            "What's today's astronomy picture?",
            specialists_called={"asteroid_analyst"},
            commander_tools_called={"get_apod"},
        )


def test_assert_no_unnecessary_calls_accepts_good_asteroid_route():
    assert_no_unnecessary_calls(
        "Any hazardous asteroids?",
        specialists_called={"asteroid_analyst"},
        commander_tools_called=set(),
    )


def test_whitelist_enforced_at_construction_asteroid():
    tools = filter_tools_by_name(ALL_MCP, ASTEROID_TOOLS)
    names = {tool_name(t) for t in tools}
    assert names == set(ASTEROID_TOOLS)
    assert "get_apod" not in names
    assert "get_space_weather" not in names


def test_whitelist_enforced_at_construction_commander_mcp():
    tools = filter_tools_by_name(ALL_MCP, COMMANDER_MCP_TOOLS)
    assert {tool_name(t) for t in tools} == {"get_apod"}


def test_specialist_whitelists_are_disjoint():
    sets = [set(ASTEROID_TOOLS), set(WEATHER_TOOLS), set(EARTH_TOOLS)]
    for i, a in enumerate(sets):
        for j, b in enumerate(sets):
            if i == j:
                continue
            assert a.isdisjoint(b)
