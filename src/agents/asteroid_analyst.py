"""Asteroid Analyst — NeoWs search and detail (enforced tool whitelist)."""

from __future__ import annotations

from datetime import date
from typing import Any

from strands import Agent

from agents.config import ASTEROID_TOOLS, filter_tools_by_name
from agents.dates import briefing_window


def build_system_prompt(*, today: date | None = None) -> str:
    start, end = briefing_window(today=today)
    return f"""\
You are the Asteroid Analyst for NASA Mission Control.
Use only your tools to answer questions about near-Earth asteroids and close approaches.

Mission Control clock: today={start}. Default window: {start} to {end} (max 7 days).
When the user says "this week", "today", or omits dates, call search_asteroids with \
start_date={start} and end_date={end}. Never ask the user for a date range — pick these dates.
Prefer hazardous_only=true when the user asks about hazardous / PHA objects.
When a specific asteroid id is known or returned from search, call get_asteroid for detail.
Never invent orbital data. Empty results mean no matches — say so clearly.
Do not claim a potentially hazardous asteroid implies an impact is predicted.
"""


def build_asteroid_analyst(model: Any, mcp_tools: list[Any]) -> Agent:
    tools = filter_tools_by_name(mcp_tools, ASTEROID_TOOLS)
    return Agent(
        name="asteroid_analyst",
        description=(
            "Analyze near-Earth asteroids and close approaches. "
            "Use for PHA search, miss distance, and asteroid id lookups."
        ),
        model=model,
        system_prompt=build_system_prompt(),
        tools=tools,
        callback_handler=None,
    )
