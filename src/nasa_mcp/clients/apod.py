"""NASA Astronomy Picture of the Day (APOD) client."""

from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError


class ApodClient(BaseNASAClient):
    """Adapter for the NASA APOD API.

    Endpoint: https://api.nasa.gov/planetary/apod
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
            cache_ttl=21600,  # 6 hours — APOD changes once per day
        )

    async def get_apod(self, date: str | None = None) -> dict[str, Any]:
        """Fetch the Astronomy Picture of the Day.

        Args:
            date: Optional date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Raw APOD JSON from NASA.

        Raises:
            NASAError: On upstream failures or invalid date.
        """
        params: dict[str, Any] = {}
        if date is not None:
            params["date"] = date

        data = await self._request("/planetary/apod", params)

        if not isinstance(data, dict) or "title" not in data:
            raise NASAError("NO_DATA", "APOD returned unexpected data structure", retryable=False)

        return data
