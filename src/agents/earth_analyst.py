"""Earth Events Analyst — EONET natural events (enforced tool whitelist)."""

from __future__ import annotations

from datetime import date
from typing import Any

from strands import Agent

from agents.config import EARTH_TOOLS, filter_tools_by_name
from agents.dates import briefing_window


def build_system_prompt(*, today: date | None = None) -> str:
    start, _end = briefing_window(today=today)
    return f"""\
You are the Earth Events Analyst for NASA Mission Control.
Use get_earth_events for wildfires, storms, volcanoes, and other natural events.

Mission Control clock: today={start}.
When the user says "this week", "major events", or omits filters, call get_earth_events \
with status=open and days=7. Never ask the user for dates or days — use these defaults.
Empty list means no matching events — say so clearly. Summarize title, category, and status.
"""


def build_earth_analyst(model: Any, mcp_tools: list[Any]) -> Agent:
    tools = filter_tools_by_name(mcp_tools, EARTH_TOOLS)
    return Agent(
        name="earth_events_analyst",
        description=(
            "Analyze Earth natural events from NASA EONET: wildfires, volcanoes, "
            "storms, and related open/closed events."
        ),
        model=model,
        system_prompt=build_system_prompt(),
        tools=tools,
        callback_handler=None,
    )
