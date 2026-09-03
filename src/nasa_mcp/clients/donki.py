"""NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information) client."""

from typing import Any, Literal

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError

DonkiEventType = Literal["CME", "FLR", "GST", "IPS", "MPC", "RBE", "HSS"]

DONKI_ENDPOINTS: dict[str, str] = {
    "CME": "/DONKI/CME",
    "FLR": "/DONKI/FLR",
    "GST": "/DONKI/GST",
    "IPS": "/DONKI/IPS",
    "MPC": "/DONKI/MPC",
    "RBE": "/DONKI/RBE",
    "HSS": "/DONKI/HSS",
}


class DonkiClient(BaseNASAClient):
    """Adapter for the NASA DONKI API.

    Base URL: https://api.nasa.gov/DONKI
    Each event type has its own endpoint.
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
            cache_ttl=600,  # 10 min — space weather events arrive periodically
        )

    async def get_events(
        self,
        event_type: DonkiEventType,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch space weather events by type and date range.

        Args:
            event_type: One of CME, FLR, GST, IPS, MPC, RBE, HSS.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of event dicts from DONKI.

        Raises:
            NASAError: On invalid type, upstream failures, etc.
        """
        endpoint = DONKI_ENDPOINTS.get(event_type)
        if not endpoint:
            raise NASAError(
                "INVALID_PARAMETERS",
                f"Unknown DONKI event type: {event_type}",
                retryable=False,
            )

        data = await self._request(
            endpoint,
            {
                "startDate": start_date,
                "endDate": end_date,
            },
        )

        if data is None or (isinstance(data, list) and len(data) == 0):
            return []

        if not isinstance(data, list):
            return [data] if isinstance(data, dict) else []

        return data
