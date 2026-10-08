"""Mission Commander — orchestrates specialists (agents-as-tools) + APOD only."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from strands import Agent

from agents.asteroid_analyst import build_asteroid_analyst
from agents.config import (
    COMMANDER_MCP_TOOLS,
    build_model,
    create_nasa_mcp_client,
    filter_tools_by_name,
)
from agents.earth_analyst import build_earth_analyst
from agents.weather_analyst import build_weather_analyst

SYSTEM_PROMPT = """\
You are the Mission Commander for NASA AI Mission Control.
You analyze the user request, delegate to specialist agents, and synthesize a clear briefing.

Specialist tools (use these for domain work — do not invent NASA data):
- asteroid_analyst: near-Earth asteroids, PHA search, and asteroid id detail
- space_weather_analyst: solar / geomagnetic / DONKI space weather
- earth_events_analyst: EONET wildfires, storms, volcanoes, etc.

You may call get_apod yourself for Astronomy Picture of the Day questions or when building \
a full mission briefing.

Routing rules:
- Asteroid / PHA / close-approach questions → asteroid_analyst only (including single-id lookups)
- Space weather / solar / CME / flare → space_weather_analyst
- Earth natural events → earth_events_analyst
- APOD / today's astronomy picture alone → get_apod
- Full mission briefing → call the three specialists as needed, then get_apod

Keep answers grounded in tool results. Never claim a PHA implies a predicted impact.
If a specialist reports an error, summarize the failure without crashing the briefing.
"""


def build_commander(
    model: Any,
    mcp_tools: list[Any],
    *,
    telemetry: Any | None = None,
) -> Agent:
    """Build Commander with specialist agents-as-tools + get_apod only."""
    apod_tools = filter_tools_by_name(mcp_tools, COMMANDER_MCP_TOOLS)

    asteroid = build_asteroid_analyst(model, mcp_tools)
    weather = build_weather_analyst(model, mcp_tools)
    earth = build_earth_analyst(model, mcp_tools)

    if telemetry is not None:
        telemetry.attach(asteroid)
        telemetry.attach(weather)
        telemetry.attach(earth)

    specialist_tools = [
        asteroid.as_tool(
            name="asteroid_analyst",
            description=(
                "Delegate asteroid and close-approach analysis. "
                "Pass a clear research question including dates when relevant."
            ),
        ),
        weather.as_tool(
            name="space_weather_analyst",
            description=(
                "Delegate space weather analysis (DONKI). "
                "Pass a clear question including date range when relevant."
            ),
        ),
        earth.as_tool(
            name="earth_events_analyst",
            description=(
                "Delegate Earth natural-event analysis (EONET). "
                "Pass a clear question including days/status filters when relevant."
            ),
        ),
    ]

    commander = Agent(
        name="mission_commander",
        description="Orchestrates NASA Mission Control specialists and synthesizes briefings.",
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[*specialist_tools, *apod_tools],
    )
    if telemetry is not None:
        telemetry.attach(commander)
    return commander


@contextmanager
def mission_control(
    model: Any | None = None,
    *,
    telemetry: Any | None = None,
) -> Iterator[Agent]:
    """Open MCP STDIO session and yield a ready Mission Commander agent."""
    resolved = model or build_model()
    mcp = create_nasa_mcp_client()
    with mcp:
        tools = mcp.list_tools_sync()
        yield build_commander(resolved, tools, telemetry=telemetry)
