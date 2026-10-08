"""Earth Events Analyst — EONET natural events (enforced tool whitelist)."""

from __future__ import annotations

from typing import Any

from strands import Agent

from agents.config import EARTH_TOOLS, filter_tools_by_name

SYSTEM_PROMPT = """\
You are the Earth Events Analyst for NASA Mission Control.
Use get_earth_events for wildfires, storms, volcanoes, and other natural events.
Default to status=open and a sensible days look-back (e.g. 7) unless the user specifies otherwise.
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
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        callback_handler=None,
    )
