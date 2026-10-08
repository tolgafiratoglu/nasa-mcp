"""Telemetry / briefing accumulator unit tests — no live LLM/NASA."""

from __future__ import annotations

from api.telemetry import BriefingAccumulator, MissionTelemetry, _safe_text, _tool_use_parts


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


def test_briefing_accumulator_long_apod_explanation():
    """UI summaries truncate; ingest must still accept full JSON."""
    explanation = "word " * 200
    payload = (
        '{"title": "Long", "date": "2024-01-01", '
        f'"explanation": "{explanation.strip()}", '
        '"url": "https://example.com/a.jpg", "media_type": "image"}'
    )
    assert len(payload) > 600
    assert len(_safe_text(payload)) <= 600

    acc = BriefingAccumulator()
    acc.ingest("get_apod", payload)
    assert acc.payload.apod is not None
    assert acc.payload.apod.title == "Long"


def test_after_tool_ingests_full_text_not_truncated_summary():
    events: list[tuple] = []
    acc = BriefingAccumulator()
    telemetry = MissionTelemetry(on_event=lambda *a, **k: events.append(a), accumulator=acc)

    explanation = "detail " * 150
    full = (
        '{"title": "Full", "date": "2024-01-01", '
        f'"explanation": "{explanation.strip()}", '
        '"url": "https://example.com/a.jpg", "media_type": "image"}'
    )

    class _FakeEvent:
        agent = type("A", (), {"name": "mission_commander"})()
        tool_use = {"name": "get_apod", "input": {}}
        result = {"content": [{"text": full}]}
        duration = 0.01

    telemetry._after_tool(_FakeEvent())
    assert acc.payload.apod is not None
    assert acc.payload.apod.title == "Full"
