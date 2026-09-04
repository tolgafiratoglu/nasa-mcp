"""NASA Mission Control MCP Server.

Exposes NASA data sources as semantically meaningful MCP tools,
resources, and prompts for AI host consumption.

STDIO transport: stdout is protocol-owned. Use logging (-> stderr), never print().
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import httpx2
from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from nasa_mcp.clients.apod import ApodClient
from nasa_mcp.clients.base import DEFAULT_TIMEOUT, NASAError
from nasa_mcp.clients.donki import DonkiClient
from nasa_mcp.clients.eonet import EonetClient
from nasa_mcp.clients.neows import NeoWsClient
from nasa_mcp.models import (
    APODResult,
    Asteroid,
    AsteroidDetail,
    EarthEvent,
    SpaceWeatherEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Shared NASA clients for the life of the MCP server process."""

    http: httpx2.AsyncClient
    apod: ApodClient
    neows: NeoWsClient
    donki: DonkiClient
    eonet: EonetClient


@asynccontextmanager
async def app_lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    """Open one shared HTTP client and NASA adapters; close on shutdown."""
    http = httpx2.AsyncClient(timeout=DEFAULT_TIMEOUT)
    ctx = AppContext(
        http=http,
        apod=ApodClient(http_client=http),
        neows=NeoWsClient(http_client=http),
        donki=DonkiClient(http_client=http),
        eonet=EonetClient(http_client=http),
    )
    logger.info("NASA Mission Control lifespan started")
    try:
        yield ctx
    finally:
        await http.aclose()
        logger.info("NASA Mission Control lifespan stopped")


mcp = MCPServer(
    "NASA Mission Control",
    lifespan=app_lifespan,
    cache_hints={
        "tools/list": CacheHint(ttl_ms=60_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=86_400_000, scope="public"),
    },
)


def _app(ctx: Context[AppContext]) -> AppContext:
    return ctx.request_context.lifespan_context


def _nasa_error(exc: NASAError) -> Exception:
    return Exception(
        f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})"
    )


@mcp.tool(
    title="Astronomy Picture of the Day",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_apod(
    ctx: Context[AppContext],
    date: Annotated[
        str | None,
        Field(description="Date in YYYY-MM-DD format. Defaults to today."),
    ] = None,
) -> APODResult:
    """Get NASA's Astronomy Picture of the Day with title, media URL, and explanation.

    Prefer this for astronomy imagery questions. media_type may be image or video.
    """
    try:
        return await _app(ctx).apod.get_apod(date=date)
    except NASAError as exc:
        raise _nasa_error(exc) from exc


@mcp.tool(
    title="Search near-Earth asteroids",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def search_asteroids(
    ctx: Context[AppContext],
    start_date: Annotated[str, Field(description="Start date in YYYY-MM-DD format.")],
    end_date: Annotated[str, Field(description="End date in YYYY-MM-DD format.")],
    hazardous_only: Annotated[
        bool,
        Field(description="If true, return only potentially hazardous asteroids (PHA)."),
    ] = False,
) -> list[Asteroid]:
    """Search near-Earth asteroids by close-approach date range (max 7 days).

    Each result includes an id — call get_asteroid with that id for orbital detail.
    Empty list means no matches in range (not an error).
    """
    try:
        return await _app(ctx).neows.search_asteroids(
            start_date,
            end_date,
            hazardous_only=hazardous_only,
        )
    except NASAError as exc:
        raise _nasa_error(exc) from exc


@mcp.tool(
    title="Get asteroid details",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_asteroid(
    ctx: Context[AppContext],
    asteroid_id: Annotated[
        str,
        Field(description="NASA JPL SPK-ID from search_asteroids (e.g. '2000433')."),
    ],
) -> AsteroidDetail:
    """Get detailed orbital and approach data for one asteroid by id.

    Use after search_asteroids to inspect a notable or hazardous object.
    """
    try:
        return await _app(ctx).neows.get_asteroid(asteroid_id)
    except NASAError as exc:
        raise _nasa_error(exc) from exc


@mcp.tool(
    title="Get space weather events",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_space_weather(
    ctx: Context[AppContext],
    event_type: Annotated[
        Literal["ALL", "CME", "FLR", "GST", "IPS", "MPC", "RBE", "HSS"],
        Field(
            description=(
                "ALL fans out across DONKI types; or CME, FLR (flare), GST (storm), "
                "IPS, MPC, RBE, HSS."
            )
        ),
    ],
    start_date: Annotated[str, Field(description="Start date in YYYY-MM-DD format.")],
    end_date: Annotated[str, Field(description="End date in YYYY-MM-DD format.")],
) -> list[SpaceWeatherEvent]:
    """Get space weather events from NASA DONKI for a date range.

    Prefer event_type=ALL for mission briefings. Empty list means no events found.
    """
    try:
        return await _app(ctx).donki.get_events(event_type, start_date, end_date)
    except NASAError as exc:
        raise _nasa_error(exc) from exc


@mcp.tool(
    title="Get Earth natural events",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_earth_events(
    ctx: Context[AppContext],
    categories: Annotated[
        list[str] | None,
        Field(
            description="Category IDs such as wildfires, volcanoes. Omit/null for all."
        ),
    ] = None,
    days: Annotated[
        int,
        Field(description="Look-back window in days (1–365). Default 7.", ge=1, le=365),
    ] = 7,
    status: Annotated[
        Literal["open", "closed", "all"],
        Field(description="open, closed, or all. Default open."),
    ] = "open",
    bbox: Annotated[
        str | None,
        Field(description="Optional bbox: min_lon,min_lat,max_lon,max_lat."),
    ] = None,
) -> list[EarthEvent]:
    """Get natural Earth events from EONET (wildfires, storms, volcanoes, etc.).

    Results include coordinates for mapping. See nasa://eonet/categories.
    Empty list means no matching events.
    """
    try:
        return await _app(ctx).eonet.get_events(
            categories=categories,
            days=days,
            status=status,
            bbox=bbox,
        )
    except NASAError as exc:
        raise _nasa_error(exc) from exc


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

NASA_GLOSSARY = """# NASA Mission Control Glossary

**NEO** — Near-Earth Object (perihelion < 1.3 AU).
**PHA** — Potentially Hazardous Asteroid (MOID ≤ 0.05 AU, H ≤ 22).
**AU** — Astronomical Unit (~149.6 million km).
**Miss distance** — Closest Earth approach distance for a pass.
**CME** — Coronal Mass Ejection.
**Solar flare** — Sudden solar brightening (classes A/B/C/M/X).
**Geomagnetic storm** — Magnetosphere disturbance (Kp / G1–G5).
**DONKI** — NASA space-weather event catalog.
**EONET** — Earth Observatory Natural Event Tracker.
**APOD** — Astronomy Picture of the Day.
"""

EONET_CATEGORIES = """# EONET Categories (use titles/ids with get_earth_events)

| ID | Title |
|----|-------|
| 8 | Wildfires |
| 12 | Volcanoes |
| 10 | Severe Storms |
| 9 | Floods |
| 15 | Sea and Lake Ice |
| 16 | Earthquakes |
| 6 | Drought |
| 7 | Dust and Haze |
| 14 | Landslides |
| 17 | Snow |
| 18 | Temperature Extremes |
| 13 | Water Color |
| 19 | Manmade |
"""


@mcp.resource("nasa://glossary")
def glossary() -> str:
    """Short glossary of NEO, PHA, CME, DONKI, EONET, and related terms."""
    return NASA_GLOSSARY


@mcp.resource("nasa://eonet/categories")
def eonet_categories() -> str:
    """Compact EONET category id/title table for get_earth_events filters."""
    return EONET_CATEGORIES


@mcp.prompt(title="Daily Mission Briefing")
def daily_mission_briefing() -> str:
    """Orchestrate a multi-tool NASA Mission Control briefing for the next 7 days."""
    return (
        "Create today's NASA Mission Control Briefing for the next 7 days.\n\n"
        "1. Call search_asteroids for this week with hazardous_only=true. "
        "For the most notable approach, call get_asteroid with its id.\n"
        "2. Call get_space_weather with event_type=ALL for a recent date range.\n"
        "3. Call get_earth_events for currently open major events.\n"
        "4. Call get_apod for today's astronomy picture.\n\n"
        "Present a structured mission-control briefing. "
        "Do not claim a PHA implies an impact is predicted."
    )


if __name__ == "__main__":
    mcp.run()
