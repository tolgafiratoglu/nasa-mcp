"""Space Weather Analyst — DONKI events (enforced tool whitelist)."""

from __future__ import annotations

from typing import Any

from strands import Agent

from agents.config import WEATHER_TOOLS, filter_tools_by_name

SYSTEM_PROMPT = """\
You are the Space Weather Analyst for NASA Mission Control.
Use get_space_weather to report solar and geomagnetic activity (CME, flares, storms, etc.).
For mission briefings prefer event_type=ALL over a recent date range.
Empty list means no events found — say so clearly. Cite event_type and times from tool results.
"""


def build_weather_analyst(model: Any, mcp_tools: list[Any]) -> Agent:
    tools = filter_tools_by_name(mcp_tools, WEATHER_TOOLS)
    return Agent(
        name="space_weather_analyst",
        description=(
            "Analyze NASA DONKI space weather: CME, solar flares, geomagnetic storms, "
            "and related events for a date range."
        ),
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        callback_handler=None,
    )
