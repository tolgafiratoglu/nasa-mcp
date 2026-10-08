"""Space Weather Analyst — DONKI events (enforced tool whitelist)."""

from __future__ import annotations

from datetime import date
from typing import Any

from strands import Agent

from agents.config import WEATHER_TOOLS, filter_tools_by_name
from agents.dates import briefing_window


def build_system_prompt(*, today: date | None = None) -> str:
    start, end = briefing_window(today=today)
    return f"""\
You are the Space Weather Analyst for NASA Mission Control.
Use get_space_weather to report solar and geomagnetic activity (CME, flares, storms, etc.).

Mission Control clock: today={start}. Default window: {start} to {end}.
When the user says "this week", "recent", or omits dates, call get_space_weather with \
event_type=ALL, start_date={start}, end_date={end}. Never ask the user for dates.
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
        system_prompt=build_system_prompt(),
        tools=tools,
        callback_handler=None,
    )
