"""NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information) client."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

import httpx2

from nasa_mcp.clients.base import BaseNASAClient, NASAError
from nasa_mcp.models import SpaceWeatherEvent

DonkiUpstreamType = Literal["CME", "FLR", "GST", "IPS", "MPC", "RBE", "HSS"]
SpaceWeatherEventType = Literal["ALL", "CME", "FLR", "GST", "IPS", "MPC", "RBE", "HSS"]

DONKI_ENDPOINTS: dict[str, str] = {
    "CME": "/DONKI/CME",
    "FLR": "/DONKI/FLR",
    "GST": "/DONKI/GST",
    "IPS": "/DONKI/IPS",
    "MPC": "/DONKI/MPC",
    "RBE": "/DONKI/RBE",
    "HSS": "/DONKI/HSS",
}

_TIME_KEYS = {
    "CME": "startTime",
    "FLR": "beginTime",
    "GST": "startTime",
    "IPS": "eventTime",
    "MPC": "eventTime",
    "RBE": "eventTime",
    "HSS": "eventTime",
}

_ID_KEYS = {
    "CME": "activityID",
    "FLR": "flrID",
    "GST": "gstID",
    "IPS": "activityID",
    "MPC": "activityID",
    "RBE": "activityID",
    "HSS": "activityID",
}


def _event_sort_key(raw: dict[str, Any]) -> str:
    event_type = str(raw.get("event_type", ""))
    time_key = _TIME_KEYS.get(event_type, "eventTime")
    return str(raw.get(time_key) or raw.get("startTime") or raw.get("beginTime") or "")


def _to_space_weather_event(raw: dict[str, Any]) -> SpaceWeatherEvent:
    etype = str(raw.get("event_type", ""))
    time_key = _TIME_KEYS.get(etype, "eventTime")
    id_key = _ID_KEYS.get(etype, "activityID")
    return SpaceWeatherEvent(
        event_type=etype,
        event_id=str(raw.get(id_key, "")),
        time=str(raw.get(time_key, "")),
        link=str(raw.get("link", "")),
        summary=str(raw.get("note", raw.get("instruments", ""))),
    )


class DonkiClient(BaseNASAClient):
    """Adapter for the NASA DONKI API.

    Base URL: https://api.nasa.gov/DONKI
    Each event type has its own endpoint. ``ALL`` is an MCP convenience
    that fans out to every supported endpoint and merges results.
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

    async def _fetch_type(
        self,
        event_type: DonkiUpstreamType,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        endpoint = DONKI_ENDPOINTS[event_type]
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
            items = [data] if isinstance(data, dict) else []
        else:
            items = data

        tagged: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["event_type"] = event_type
            tagged.append(row)
        return tagged

    async def get_events(
        self,
        event_type: SpaceWeatherEventType | str,
        start_date: str,
        end_date: str,
    ) -> list[SpaceWeatherEvent]:
        """Fetch space weather events by type and date range.

        Args:
            event_type: ALL, CME, FLR, GST, IPS, MPC, RBE, or HSS.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            Normalized SpaceWeatherEvent list (empty = no matches).
            Sorted newest-first when event_type is ALL.

        Raises:
            NASAError: On invalid type, upstream failures, etc.
        """
        normalized = str(event_type).upper()

        if normalized == "ALL":
            batches = await asyncio.gather(
                *[
                    self._fetch_type(t, start_date, end_date)  # type: ignore[arg-type]
                    for t in DONKI_ENDPOINTS
                ]
            )
            merged: list[dict[str, Any]] = []
            for batch in batches:
                merged.extend(batch)
            merged.sort(key=_event_sort_key, reverse=True)
            return [_to_space_weather_event(raw) for raw in merged]

        if normalized not in DONKI_ENDPOINTS:
            raise NASAError(
                "INVALID_PARAMETERS",
                f"Unknown DONKI event type: {event_type}",
                retryable=False,
            )

        raws = await self._fetch_type(normalized, start_date, end_date)  # type: ignore[arg-type]
        return [_to_space_weather_event(raw) for raw in raws]
