"""NASA EONET (Earth Observatory Natural Event Tracker) v3 client."""

from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError
from nasa_mcp.models import EarthEvent, EventGeometry
from nasa_mcp.validation import validate_bbox

EONET_BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3"


class EonetClient(BaseNASAClient):
    """Adapter for the NASA EONET v3 API.

    Base URL: https://eonet.gsfc.nasa.gov/api/v3
    Note: EONET uses its own base URL, not api.nasa.gov.
    """

    def __init__(
        self,
        *,
        http_client: httpx2.AsyncClient | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            http_client=http_client,
            api_key=api_key,
            cache_ttl=300,  # 5 min — natural events can change status rapidly
        )

    def _parse_event(self, raw: dict[str, Any]) -> EarthEvent:
        geometry = []
        for geo in raw.get("geometry", []):
            coords = geo.get("coordinates", [])
            if len(coords) >= 2:
                geometry.append(
                    EventGeometry(
                        date=str(geo.get("date", "")),
                        type=geo.get("type", "Point"),
                        coordinates=coords[:2],
                    )
                )

        cat_titles = [c.get("title", "") for c in raw.get("categories", [])]

        return EarthEvent(
            id=str(raw.get("id", "")),
            title=raw.get("title", ""),
            categories=cat_titles,
            status="closed" if raw.get("closed") else "open",
            geometry=geometry,
        )

    async def get_events(
        self,
        categories: list[str] | None = None,
        days: int = 7,
        status: str = "open",
        bbox: str | None = None,
    ) -> list[EarthEvent]:
        """Fetch natural events from EONET v3.

        Args:
            categories: Filter by category IDs (e.g. ["wildfires", "volcanoes"]).
            days: Number of days to look back. Default 7.
            status: "open", "closed", or "all". Default "open".
            bbox: Bounding box as "min_lon,min_lat,max_lon,max_lat".

        Returns:
            Normalized EarthEvent list (empty = no matches).

        Raises:
            NASAError: On validation or upstream failures.
        """
        params: dict[str, Any] = {
            "days": days,
            "status": status,
        }

        if bbox:
            validate_bbox(bbox)
            params["bbox"] = bbox

        url = f"{EONET_BASE_URL}/events"
        if categories:
            url = f"{EONET_BASE_URL}/categories/{','.join(categories)}"

        data = await self._request(url, params)

        events = data.get("events", [])
        if not isinstance(events, list):
            raise NASAError(
                "NO_DATA",
                "EONET returned unexpected data structure",
                retryable=False,
            )

        return [self._parse_event(raw) for raw in events if isinstance(raw, dict)]

    async def get_categories(self) -> list[dict[str, Any]]:
        """Fetch the list of EONET event categories."""
        data = await self._request(f"{EONET_BASE_URL}/categories")
        return data.get("categories", [])
