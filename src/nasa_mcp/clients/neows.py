"""NASA Near Earth Object Web Service (NeoWs) client."""

from datetime import datetime
from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError
from nasa_mcp.models import Asteroid, AsteroidDetail, CloseApproach


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

    def _parse_asteroid(self, raw: dict[str, Any]) -> Asteroid:
        diameter = raw.get("estimated_diameter", {}).get("meters", {})
        approaches = raw.get("close_approach_data", [])

        close = None
        if approaches:
            ca = approaches[0]
            close = CloseApproach(
                date=ca.get("close_approach_date", ""),
                miss_distance_km=float(ca.get("miss_distance", {}).get("kilometers", 0)),
                relative_velocity_kmh=float(
                    ca.get("relative_velocity", {}).get("kilometers_per_hour", 0)
                ),
            )

        return Asteroid(
            id=str(raw.get("id", "")),
            name=raw.get("name", ""),
            potentially_hazardous=raw.get("is_potentially_hazardous_asteroid", False),
            diameter_min_m=float(diameter.get("estimated_diameter_min", 0)),
            diameter_max_m=float(diameter.get("estimated_diameter_max", 0)),
            close_approach=close,
        )

    def _parse_asteroid_detail(self, raw: dict[str, Any]) -> AsteroidDetail:
        diameter = raw.get("estimated_diameter", {}).get("meters", {})
        orbital = raw.get("orbital_data", {})

        approaches = [
            CloseApproach(
                date=ca.get("close_approach_date", ""),
                miss_distance_km=float(ca.get("miss_distance", {}).get("kilometers", 0)),
                relative_velocity_kmh=float(
                    ca.get("relative_velocity", {}).get("kilometers_per_hour", 0)
                ),
            )
            for ca in raw.get("close_approach_data", [])
        ]

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

    async def search_asteroids(
        self,
        start_date: str,
        end_date: str,
        *,
        hazardous_only: bool = False,
    ) -> list[Asteroid]:
        """Fetch NEOs by close-approach date range.

        Returns a flat list of normalized Asteroid models.
        Empty list means no matches (not an error).

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
        asteroids: list[Asteroid] = []
        for date_key in sorted(near_earth_objects.keys()):
            for raw in near_earth_objects[date_key]:
                asteroids.append(self._parse_asteroid(raw))

        if hazardous_only:
            asteroids = [a for a in asteroids if a.potentially_hazardous]

        return asteroids

    async def get_asteroid(self, asteroid_id: str) -> AsteroidDetail:
        """Fetch detailed data for a specific asteroid by NASA JPL SPK-ID.

        Raises:
            NASAError: On upstream failures or unknown ID (NO_DATA).
        """
        data = await self._request(f"/neo/rest/v1/neo/{asteroid_id}")

        if not isinstance(data, dict) or "name" not in data:
            raise NASAError(
                "NO_DATA",
                f"No data found for asteroid {asteroid_id}",
                retryable=False,
            )

        return self._parse_asteroid_detail(data)
