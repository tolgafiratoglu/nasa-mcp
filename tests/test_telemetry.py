"""Telemetry / briefing accumulator unit tests — no live LLM/NASA."""

from __future__ import annotations

from api.telemetry import BriefingAccumulator, _tool_use_parts


def test_tool_use_parts_from_dict():
    name, args = _tool_use_parts(
        {"name": "search_asteroids", "input": {"start_date": "2024-01-01"}}
    )
    assert name == "search_asteroids"
    assert args["start_date"] == "2024-01-01"


def test_briefing_accumulator_asteroids():
    acc = BriefingAccumulator()
    acc.ingest(
        "search_asteroids",
        '[{"id": "1", "name": "Eros", "potentially_hazardous": false, '
        '"diameter_min_m": 1, "diameter_max_m": 2, '
        '"close_approach": {"date": "2024-01-02", "miss_distance_km": 1000, '
        '"relative_velocity_kmh": 40000}}]',
    )
    assert len(acc.payload.asteroids) == 1
    assert acc.payload.asteroids[0].name == "Eros"


def test_briefing_accumulator_apod():
    acc = BriefingAccumulator()
    acc.ingest(
        "get_apod",
        '{"title": "Nebula", "date": "2024-01-01", "explanation": "x", '
        '"url": "https://example.com/a.jpg", "media_type": "image"}',
    )
    assert acc.payload.apod is not None
    assert acc.payload.apod.title == "Nebula"
