"""NASA Astronomy Picture of the Day (APOD) client."""

from typing import Any

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError
from nasa_mcp.models import APODResult


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

    def _to_result(self, data: dict[str, Any]) -> APODResult:
        media = data.get("media_type", "image")
        if media not in ("image", "video"):
            media = "image"
        return APODResult(
            title=data["title"],
            date=data["date"],
            explanation=data["explanation"],
            url=data["url"],
            hdurl=data.get("hdurl"),
            media_type=media,  # type: ignore[arg-type]
            copyright=data.get("copyright"),
        )

    async def get_apod(self, date: str | None = None) -> APODResult:
        """Fetch the Astronomy Picture of the Day.

        Args:
            date: Optional date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Normalized APODResult.

        Raises:
            NASAError: On upstream failures or unexpected payloads.
        """
        params: dict[str, Any] = {}
        if date is not None:
            params["date"] = date

        data = await self._request("/planetary/apod", params)

        if not isinstance(data, dict) or "title" not in data:
            raise NASAError(
                "NO_DATA",
                "APOD returned unexpected data structure",
                retryable=False,
            )

        return self._to_result(data)
