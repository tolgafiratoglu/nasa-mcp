"""Model and validation contract tests — no live NASA calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nasa_mcp.clients.base import NASAError
from nasa_mcp.clients.neows import NeoWsClient
from nasa_mcp.models import APODResult, Asteroid
from nasa_mcp.validation import validate_bbox


def test_asteroid_id_required():
    with pytest.raises(ValidationError):
        Asteroid(
            name="x",
            potentially_hazardous=False,
            diameter_min_m=1.0,
            diameter_max_m=2.0,
        )


def test_asteroid_model_accepts_id():
    rock = Asteroid(
        id="2000433",
        name="Eros",
        potentially_hazardous=False,
        diameter_min_m=10.0,
        diameter_max_m=20.0,
    )
    assert rock.id == "2000433"


def test_apod_optional_hdurl_absent_ok():
    result = APODResult(
        title="Test",
        date="2024-01-01",
        explanation="A picture",
        url="https://example.com/img.jpg",
        media_type="image",
    )
    assert result.hdurl is None


def test_apod_media_type_video_ok():
    result = APODResult(
        title="Vid",
        date="2024-01-01",
        explanation="A video",
        url="https://example.com/v.mp4",
        media_type="video",
    )
    assert result.media_type == "video"


def test_apod_invalid_media_type_rejected():
    with pytest.raises(ValidationError):
        APODResult(
            title="Bad",
            date="2024-01-01",
            explanation="x",
            url="https://example.com/x",
            media_type="gif",  # type: ignore[arg-type]
        )


def test_bbox_valid():
    assert validate_bbox("-180,-90,180,90") == (-180.0, -90.0, 180.0, 90.0)


def test_bbox_malformed_reject():
    with pytest.raises(NASAError) as exc_info:
        validate_bbox("1,2,3")
    assert exc_info.value.error_type == "INVALID_PARAMETERS"


def test_bbox_non_numeric_reject():
    with pytest.raises(NASAError) as exc_info:
        validate_bbox("a,b,c,d")
    assert exc_info.value.error_type == "INVALID_PARAMETERS"


def test_neows_seven_day_range_accepted():
    client = NeoWsClient()
    client._validate_date_range("2024-01-01", "2024-01-08")


def test_neows_over_seven_day_range_rejected():
    client = NeoWsClient()
    with pytest.raises(NASAError) as exc_info:
        client._validate_date_range("2024-01-01", "2024-01-09")
    assert exc_info.value.error_type == "INVALID_PARAMETERS"


def test_neows_end_before_start_rejected():
    client = NeoWsClient()
    with pytest.raises(NASAError) as exc_info:
        client._validate_date_range("2024-01-10", "2024-01-01")
    assert exc_info.value.error_type == "INVALID_PARAMETERS"
