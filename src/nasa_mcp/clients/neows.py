"""NASA Near Earth Object Web Service (NeoWs) client."""

from datetime import datetime
from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError


class NeoWsClient(BaseNASAClient):
    """Adapter for the NASA NeoWs API.

    Feed endpoint: https://api.nasa.gov/neo/rest/v1/feed
    Lookup endpoint: https://api.nasa.gov/neo/rest/v1/neo/{asteroid_id}
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
            cache_ttl=900,  # 15 min — orbital data updates infrequently
        )

    def _validate_date_range(self, start_date: str, end_date: str) -> None:
        """NASA NeoWs limits feed requests to a 7-day window."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise NASAError(
                "INVALID_PARAMETERS",
                f"Invalid date format: {exc}. Use YYYY-MM-DD.",
                retryable=False,
            )

        if end < start:
            raise NASAError(
                "INVALID_PARAMETERS",
                "end_date must be after start_date.",
                retryable=False,
            )

        if (end - start).days > 7:
            raise NASAError(
                "INVALID_PARAMETERS",
                "NeoWs date range limited to 7 days.",
                retryable=False,
            )

    async def search_asteroids(
        self,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch NEOs by close-approach date range.

        Returns a flat list of asteroid dicts extracted from the date-keyed response.

        Raises:
            NASAError: On validation failures or upstream errors.
        """
        self._validate_date_range(start_date, end_date)

        data = await self._request(
            "/neo/rest/v1/feed",
            {
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        near_earth_objects = data.get("near_earth_objects", {})
        asteroids: list[dict[str, Any]] = []
        for date_key in sorted(near_earth_objects.keys()):
            asteroids.extend(near_earth_objects[date_key])

        return asteroids

    async def get_asteroid(self, asteroid_id: str) -> dict[str, Any]:
        """Fetch detailed data for a specific asteroid by its NASA JPL SPK-ID.

        Raises:
            NASAError: On upstream failures or unknown ID.
        """
        data = await self._request(f"/neo/rest/v1/neo/{asteroid_id}")

        if not isinstance(data, dict) or "name" not in data:
            raise NASAError(
                "NO_DATA",
                f"No data found for asteroid {asteroid_id}",
                retryable=False,
            )

        return data
