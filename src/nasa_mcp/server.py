"""NASA Mission Control MCP Server.

Exposes NASA data sources as semantically meaningful MCP tools,
resources, and prompts for AI host consumption.

STDIO transport: stdout is protocol-owned. Use logging (-> stderr), never print().
"""

import logging
from typing import Annotated

from mcp.server import CacheHint, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from nasa_mcp.clients.apod import ApodClient
from nasa_mcp.clients.base import NASAError
from nasa_mcp.clients.donki import DonkiClient
from nasa_mcp.clients.eonet import EonetClient
from nasa_mcp.clients.neows import NeoWsClient
from nasa_mcp.models import (
    APODResult,
    Asteroid,
    AsteroidDetail,
    CloseApproach,
    EarthEvent,
    EventGeometry,
    SpaceWeatherEvent,
)

logger = logging.getLogger(__name__)

mcp = MCPServer(
    "NASA Mission Control",
    cache_hints={
        "tools/list": CacheHint(ttl_ms=60_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=86_400_000, scope="public"),
    },
)

_apod_client = ApodClient()
_neows_client = NeoWsClient()
_donki_client = DonkiClient()
_eonet_client = EonetClient()


def _parse_asteroid(raw: dict) -> Asteroid:
    """Extract an Asteroid model from raw NeoWs feed data."""
    diameter = raw.get("estimated_diameter", {}).get("meters", {})
    approaches = raw.get("close_approach_data", [])

    close = None
    if approaches:
        ca = approaches[0]
        close = CloseApproach(
            date=ca.get("close_approach_date", ""),
            miss_distance_km=float(ca.get("miss_distance", {}).get("kilometers", 0)),
            relative_velocity_kmh=float(ca.get("relative_velocity", {}).get("kilometers_per_hour", 0)),
        )

    return Asteroid(
        id=str(raw.get("id", "")),
        name=raw.get("name", ""),
        potentially_hazardous=raw.get("is_potentially_hazardous_asteroid", False),
        diameter_min_m=float(diameter.get("estimated_diameter_min", 0)),
        diameter_max_m=float(diameter.get("estimated_diameter_max", 0)),
        close_approach=close,
    )


@mcp.tool(
    title="Astronomy Picture of the Day",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_apod(
    date: Annotated[str | None, Field(description="Date in YYYY-MM-DD format. Defaults to today.")] = None,
) -> APODResult:
    """Get NASA's Astronomy Picture of the Day with its explanation.

    Returns the title, image URL, and a detailed explanation written
    by a professional astronomer. Great for daily space inspiration.
    """
    try:
        data = await _apod_client.get_apod(date=date)
    except NASAError as exc:
        raise Exception(f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})")

    return APODResult(
        title=data["title"],
        date=data["date"],
        explanation=data["explanation"],
        url=data["url"],
        hdurl=data.get("hdurl"),
        media_type=data["media_type"],
        copyright=data.get("copyright"),
    )


@mcp.tool(
    title="Search near-Earth asteroids",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def search_asteroids(
    start_date: Annotated[str, Field(description="Start date in YYYY-MM-DD format.")],
    end_date: Annotated[str, Field(description="End date in YYYY-MM-DD format.")],
    hazardous_only: Annotated[bool, Field(description="Filter to potentially hazardous asteroids only.")] = False,
) -> list[Asteroid]:
    """Search near-Earth asteroids by their close approach date to Earth.

    Returns asteroids with estimated diameter, miss distance, and velocity.
    Date range is limited to 7 days by the NASA NeoWs API.
    Use get_asteroid for detailed information on a specific object.
    """
    try:
        raw_asteroids = await _neows_client.search_asteroids(start_date, end_date)
    except NASAError as exc:
        raise Exception(f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})")

    asteroids = [_parse_asteroid(raw) for raw in raw_asteroids]

    if hazardous_only:
        asteroids = [a for a in asteroids if a.potentially_hazardous]

    return asteroids


@mcp.tool(
    title="Get asteroid details",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_asteroid(
    asteroid_id: Annotated[str, Field(description="NASA JPL SPK-ID of the asteroid.")],
) -> AsteroidDetail:
    """Get detailed information about a specific near-Earth asteroid.

    Returns orbital data, size estimates, absolute magnitude, and
    a full list of known close approaches. Use search_asteroids first
    to find interesting asteroid IDs.
    """
    try:
        raw = await _neows_client.get_asteroid(asteroid_id)
    except NASAError as exc:
        raise Exception(f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})")

    diameter = raw.get("estimated_diameter", {}).get("meters", {})
    orbital = raw.get("orbital_data", {})

    approaches = []
    for ca in raw.get("close_approach_data", []):
        approaches.append(CloseApproach(
            date=ca.get("close_approach_date", ""),
            miss_distance_km=float(ca.get("miss_distance", {}).get("kilometers", 0)),
            relative_velocity_kmh=float(ca.get("relative_velocity", {}).get("kilometers_per_hour", 0)),
        ))

    period_raw = orbital.get("orbital_period")
    orbital_period = float(period_raw) if period_raw else None

    return AsteroidDetail(
        id=str(raw.get("id", "")),
        name=raw.get("name", ""),
        potentially_hazardous=raw.get("is_potentially_hazardous_asteroid", False),
        diameter_min_m=float(diameter.get("estimated_diameter_min", 0)),
        diameter_max_m=float(diameter.get("estimated_diameter_max", 0)),
        absolute_magnitude=float(raw.get("absolute_magnitude_h", 0)),
        orbital_period_days=orbital_period,
        close_approaches=approaches,
    )


@mcp.tool(
    title="Get space weather events",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_space_weather(
    event_type: Annotated[
        str,
        Field(description="Event type: CME, FLR (solar flare), GST (geomagnetic storm), IPS, MPC, RBE, or HSS."),
    ],
    start_date: Annotated[str, Field(description="Start date in YYYY-MM-DD format.")],
    end_date: Annotated[str, Field(description="End date in YYYY-MM-DD format.")],
) -> list[SpaceWeatherEvent]:
    """Get space weather events from NASA's DONKI database.

    Covers coronal mass ejections (CME), solar flares (FLR),
    geomagnetic storms (GST), interplanetary shocks (IPS),
    magnetopause crossings (MPC), radiation belt enhancements (RBE),
    and high-speed streams (HSS).
    """
    try:
        raw_events = await _donki_client.get_events(event_type, start_date, end_date)
    except NASAError as exc:
        raise Exception(f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})")

    TIME_KEYS = {
        "CME": "startTime",
        "FLR": "beginTime",
        "GST": "startTime",
        "IPS": "eventTime",
        "MPC": "eventTime",
        "RBE": "eventTime",
        "HSS": "eventTime",
    }
    time_key = TIME_KEYS.get(event_type, "eventTime")

    ID_KEYS = {
        "CME": "activityID",
        "FLR": "flrID",
        "GST": "gstID",
        "IPS": "activityID",
        "MPC": "activityID",
        "RBE": "activityID",
        "HSS": "activityID",
    }
    id_key = ID_KEYS.get(event_type, "activityID")

    events = []
    for raw in raw_events:
        events.append(SpaceWeatherEvent(
            event_type=event_type,
            event_id=str(raw.get(id_key, "")),
            time=str(raw.get(time_key, "")),
            link=str(raw.get("link", "")),
            summary=str(raw.get("note", raw.get("instruments", ""))),
        ))

    return events


@mcp.tool(
    title="Get Earth natural events",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def get_earth_events(
    categories: Annotated[
        list[str],
        Field(description="Filter by category IDs, e.g. ['wildfires', 'volcanoes']. Empty list for all."),
    ] = [],
    days: Annotated[int, Field(description="Number of days to look back. Default 7.", ge=1, le=365)] = 7,
    status: Annotated[
        str,
        Field(description="Event status filter: 'open', 'closed', or 'all'. Default 'open'."),
    ] = "open",
    bbox: Annotated[
        str | None,
        Field(description="Bounding box as 'min_lon,min_lat,max_lon,max_lat' for geographic filtering."),
    ] = None,
) -> list[EarthEvent]:
    """Get active natural events on Earth from NASA's EONET tracker.

    Covers wildfires, volcanoes, severe storms, floods, icebergs,
    earthquakes, and more. Returns events with geographic coordinates
    for mapping. Use nasa://eonet/categories resource for category reference.
    """
    try:
        raw_events = await _eonet_client.get_events(
            categories=categories if categories else None,
            days=days,
            status=status,
            bbox=bbox,
        )
    except NASAError as exc:
        raise Exception(f"NASA API error: {exc.message} (type={exc.error_type}, retryable={exc.retryable})")

    events = []
    for raw in raw_events:
        geometry = []
        for geo in raw.get("geometry", []):
            coords = geo.get("coordinates", [])
            if len(coords) >= 2:
                geometry.append(EventGeometry(
                    date=str(geo.get("date", "")),
                    type=geo.get("type", "Point"),
                    coordinates=coords[:2],
                ))

        cat_titles = [c.get("title", "") for c in raw.get("categories", [])]

        events.append(EarthEvent(
            id=str(raw.get("id", "")),
            title=raw.get("title", ""),
            categories=cat_titles,
            status="closed" if raw.get("closed") else "open",
            geometry=geometry,
        ))

    return events


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

NASA_GLOSSARY = """# NASA Mission Control Glossary

**NEO** (Near-Earth Object): An asteroid or comet with a perihelion distance less than 1.3 AU.

**PHA** (Potentially Hazardous Asteroid): An asteroid with a minimum orbit intersection distance (MOID) of 0.05 AU or less and an absolute magnitude (H) of 22.0 or brighter.

**AU** (Astronomical Unit): The mean distance from the Earth to the Sun, approximately 149.6 million km.

**Miss Distance**: The closest distance an asteroid will pass from Earth during a given approach.

**Absolute Magnitude (H)**: A measure of an asteroid's intrinsic brightness. Lower values indicate larger or more reflective objects.

**CME** (Coronal Mass Ejection): A large expulsion of plasma and magnetic field from the Sun's corona.

**Solar Flare**: A sudden flash of increased brightness on the Sun, classified by peak X-ray flux as A, B, C, M, or X class.

**Geomagnetic Storm**: A disturbance of Earth's magnetosphere caused by solar wind shock waves, rated on the Kp index (G1–G5).

**EONET**: NASA's Earth Observatory Natural Event Tracker, cataloging wildfires, volcanoes, storms, icebergs, and other natural events worldwide.

**APOD**: Astronomy Picture of the Day, a daily image or video of the cosmos with an explanation by a professional astronomer.

**DSCOVR/EPIC**: The Deep Space Climate Observatory carries the Earth Polychromatic Imaging Camera, capturing full-disc Earth images from the L1 Lagrange point.

**DONKI**: Space Weather Database Of Notifications, Knowledge, Information — NASA's comprehensive space weather event catalog.

**Kp Index**: A planetary index measuring geomagnetic activity on a 0–9 scale.
"""

EONET_CATEGORIES = """# EONET Event Categories

| ID | Title | Description |
|----|-------|-------------|
| 6 | Drought | Long-term water shortages |
| 7 | Dust and Haze | Dust storms and atmospheric haze |
| 16 | Earthquakes | Seismic events |
| 9 | Floods | Flooding events |
| 14 | Landslides | Landslide events |
| 19 | Manmade | Human-caused events |
| 15 | Sea and Lake Ice | Ice formation and breakup |
| 10 | Severe Storms | Tropical cyclones, nor'easters, severe thunderstorms |
| 17 | Snow | Snowfall and blizzards |
| 18 | Temperature Extremes | Heat waves and cold spells |
| 12 | Volcanoes | Volcanic eruptions and activity |
| 13 | Water Color | Algal blooms and water discoloration |
| 8 | Wildfires | Forest and brush fires |
"""


@mcp.resource("nasa://glossary")
def glossary() -> str:
    """NASA and space science terminology used across Mission Control tools.

    Provides definitions for NEO, PHA, AU, CME, solar flare, geomagnetic storm,
    and other domain terms that help interpret tool results correctly.
    """
    return NASA_GLOSSARY


@mcp.resource("nasa://eonet/categories")
def eonet_categories() -> str:
    """EONET natural event categories with IDs used by the get_earth_events tool.

    Reference this to understand event category codes when filtering Earth events.
    """
    return EONET_CATEGORIES


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(title="Daily Mission Briefing")
def daily_mission_briefing() -> str:
    """Generate today's NASA Mission Control briefing.

    Triggers multi-tool orchestration: the LLM discovers and calls
    search_asteroids, get_space_weather, get_earth_events, get_apod,
    and optionally get_asteroid for notable objects.
    """
    return (
        "Create today's NASA Mission Control Briefing.\n\n"
        "Include:\n"
        "- Near-Earth asteroids approaching this week "
        "(flag any potentially hazardous ones)\n"
        "- Recent significant space weather events\n"
        "- Currently active major natural events on Earth\n"
        "- Today's Astronomy Picture of the Day\n\n"
        "Investigate anything unusual in more detail. "
        "Present the briefing in a structured, mission-control style."
    )


if __name__ == "__main__":
    mcp.run()
