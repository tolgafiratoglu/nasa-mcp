"""Pydantic models for NASA MCP tool outputs."""

from pydantic import BaseModel, Field


class APODResult(BaseModel):
    """NASA Astronomy Picture of the Day."""

    title: str = Field(description="Title of the astronomy picture.")
    date: str = Field(description="Date of the picture in YYYY-MM-DD format.")
    explanation: str = Field(description="Detailed explanation of the image.")
    url: str = Field(description="URL to the image or video.")
    hdurl: str | None = Field(default=None, description="URL to the high-definition image, if available.")
    media_type: str = Field(description="Type of media: 'image' or 'video'.")
    copyright: str | None = Field(default=None, description="Copyright holder, if applicable.")


class CloseApproach(BaseModel):
    """A single close approach event for an asteroid."""

    date: str = Field(description="Close approach date.")
    miss_distance_km: float = Field(description="Miss distance in kilometers.")
    relative_velocity_kmh: float = Field(description="Relative velocity in km/h.")


class Asteroid(BaseModel):
    """Near-Earth asteroid summary from NeoWs feed."""

    id: str = Field(description="NASA JPL SPK-ID.")
    name: str = Field(description="Asteroid designation.")
    potentially_hazardous: bool = Field(description="NASA PHA classification.")
    diameter_min_m: float = Field(description="Minimum estimated diameter in meters.")
    diameter_max_m: float = Field(description="Maximum estimated diameter in meters.")
    close_approach: CloseApproach | None = Field(default=None, description="Nearest close approach in the queried range.")


class AsteroidDetail(BaseModel):
    """Detailed asteroid data from NeoWs lookup."""

    id: str = Field(description="NASA JPL SPK-ID.")
    name: str = Field(description="Asteroid designation.")
    potentially_hazardous: bool = Field(description="NASA PHA classification.")
    diameter_min_m: float = Field(description="Minimum estimated diameter in meters.")
    diameter_max_m: float = Field(description="Maximum estimated diameter in meters.")
    absolute_magnitude: float = Field(description="Absolute magnitude (H).")
    orbital_period_days: float | None = Field(default=None, description="Orbital period in days.")
    close_approaches: list[CloseApproach] = Field(default_factory=list, description="All known close approaches.")


class SpaceWeatherEvent(BaseModel):
    """A space weather event from NASA DONKI."""

    event_type: str = Field(description="Event type code: CME, FLR, GST, IPS, MPC, RBE, or HSS.")
    event_id: str = Field(description="Unique DONKI event identifier.")
    time: str = Field(description="Event time (ISO 8601 or DONKI format).")
    link: str = Field(default="", description="URL to the DONKI event detail page.")
    summary: str = Field(default="", description="Brief event summary when available.")


class EventGeometry(BaseModel):
    """A geographic point associated with an Earth event."""

    date: str = Field(description="Observation date (ISO 8601).")
    type: str = Field(default="Point", description="GeoJSON geometry type.")
    coordinates: list[float] = Field(description="[longitude, latitude] pair.")


class EarthEvent(BaseModel):
    """A natural event from NASA EONET."""

    id: str = Field(description="EONET event ID.")
    title: str = Field(description="Event title.")
    categories: list[str] = Field(description="Category titles (e.g. 'Wildfires', 'Volcanoes').")
    status: str = Field(description="Event status: 'open' or 'closed'.")
    geometry: list[EventGeometry] = Field(default_factory=list, description="Geographic points with timestamps.")
