"""Pure validation helpers for MCP tool inputs."""

from __future__ import annotations

from nasa_mcp.clients.base import NASAError


def validate_bbox(bbox: str) -> tuple[float, float, float, float]:
    """Parse and validate a bbox string: min_lon,min_lat,max_lon,max_lat.

    Raises:
        NASAError: INVALID_PARAMETERS when the shape or values are invalid.
    """
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise NASAError(
            "INVALID_PARAMETERS",
            "bbox must be four comma-separated numbers: min_lon,min_lat,max_lon,max_lat",
            retryable=False,
        )
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise NASAError(
            "INVALID_PARAMETERS",
            f"bbox values must be numeric: {exc}",
            retryable=False,
        ) from exc

    return min_lon, min_lat, max_lon, max_lat
