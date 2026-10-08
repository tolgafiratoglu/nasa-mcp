"""Asteroid Analyst — NeoWs search and detail (enforced tool whitelist)."""

from __future__ import annotations

from typing import Any

from strands import Agent

from agents.config import ASTEROID_TOOLS, filter_tools_by_name

SYSTEM_PROMPT = """\
You are the Asteroid Analyst for NASA Mission Control.
Use only your tools to answer questions about near-Earth asteroids and close approaches.
For date-range questions call search_asteroids (max 7-day window). Prefer hazardous_only=true \
when the user asks about hazardous / PHA objects.
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
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        callback_handler=None,
    )
