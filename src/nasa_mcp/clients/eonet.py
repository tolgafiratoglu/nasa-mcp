"""NASA EONET (Earth Observatory Natural Event Tracker) v3 client."""

from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError

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

    async def get_events(
        self,
        categories: list[str] | None = None,
        days: int = 7,
        status: str = "open",
        bbox: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch natural events from EONET v3.

        Args:
            categories: Filter by category IDs (e.g. ["wildfires", "volcanoes"]).
            days: Number of days to look back. Default 7.
            status: "open", "closed", or "all". Default "open".
            bbox: Bounding box as "min_lon,min_lat,max_lon,max_lat".

        Returns:
            List of event dicts from EONET.

        Raises:
            NASAError: On upstream failures.
        """
        params: dict[str, Any] = {
            "days": days,
            "status": status,
        }

        if bbox:
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

        return events

    async def get_categories(self) -> list[dict[str, Any]]:
        """Fetch the list of EONET event categories."""
        data = await self._request(f"{EONET_BASE_URL}/categories")
        return data.get("categories", [])
