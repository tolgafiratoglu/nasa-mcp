"""HTTP and SSE event contracts for NASA AI Mission Control API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


AgentEventType = Literal[
    "agent_start",
    "agent_end",
    "tool_call",
    "tool_result",
    "status",
    "message",
    "error",
]


class AgentEvent(BaseModel):
    """Shared event contract for SSE (Phase 2+) and future agent hooks (Phase 3)."""

    type: AgentEventType
    agent: str = Field(description="Agent id, e.g. commander, asteroid_analyst.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(description="Equals request_id for the chat turn.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000, description="User question.")


class ChatAccepted(BaseModel):
    request_id: str


class CloseApproachCard(BaseModel):
    date: str
    miss_distance_km: float
    relative_velocity_kmh: float


class AsteroidCard(BaseModel):
    id: str
    name: str
    potentially_hazardous: bool
    diameter_min_m: float = 0.0
    diameter_max_m: float = 0.0
    close_approach: CloseApproachCard | None = None


class SpaceWeatherCard(BaseModel):
    event_type: str
    event_id: str = ""
    time: str = ""
    summary: str = ""


class EarthEventCard(BaseModel):
    id: str
    title: str
    categories: list[str] = Field(default_factory=list)
    status: str = "open"


class ApodCard(BaseModel):
    title: str
    date: str
    explanation: str
    url: str
    hdurl: str | None = None
    media_type: Literal["image", "video"] = "image"
    copyright: str | None = None


class BriefingPayload(BaseModel):
    """Pre-shaped card data for the frontend (never raw NASA JSON)."""

    asteroids: list[AsteroidCard] = Field(default_factory=list)
    space_weather: list[SpaceWeatherCard] = Field(default_factory=list)
    earth_events: list[EarthEventCard] = Field(default_factory=list)
    apod: ApodCard | None = None
