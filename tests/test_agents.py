"""Agent layer unit tests — no live LLM or NASA calls."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from agents.asteroid_analyst import build_system_prompt as asteroid_prompt
from agents.commander import build_system_prompt as commander_prompt
from agents.config import (
    ASTEROID_TOOLS,
    COMMANDER_MCP_TOOLS,
    EARTH_TOOLS,
    WEATHER_TOOLS,
    filter_tools_by_name,
    tool_name,
)
from agents.dates import briefing_window, clock_context
from agents.earth_analyst import build_system_prompt as earth_prompt
from agents.weather_analyst import build_system_prompt as weather_prompt


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


def test_briefing_window_is_seven_days_inclusive():
    start, end = briefing_window(today=date(2026, 10, 8))
    assert start == "2026-10-08"
    assert end == "2026-10-14"


def test_clock_context_includes_concrete_dates():
    ctx = clock_context(today=date(2026, 10, 8))
    assert "2026-10-08" in ctx
    assert "2026-10-14" in ctx
    assert "Never ask the user for dates" in ctx


def test_prompts_inject_concrete_dates_and_forbid_asking():
    fixed = date(2026, 10, 8)
    for prompt_fn in (commander_prompt, asteroid_prompt, weather_prompt, earth_prompt):
        text = prompt_fn(today=fixed)
        assert "2026-10-08" in text
        assert "Never ask the user" in text
