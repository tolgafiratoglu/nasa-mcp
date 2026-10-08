"""Commander runner — wraps existing agents.mission_control (no duplication)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agents.commander import mission_control
from agents.dates import clock_context
from api.models import BriefingPayload
from api.telemetry import BriefingAccumulator, EventEmitter, MissionTelemetry

# Injectable for tests (mocked Commander).
CommanderRunner = Callable[[str], str]

_runner: CommanderRunner | None = None


def set_commander_runner(runner: CommanderRunner | None) -> None:
    global _runner
    _runner = runner


def run_commander(
    message: str,
    on_event: EventEmitter | None = None,
) -> tuple[str, dict[str, Any]]:
    """Run Mission Commander; optionally stream telemetry via on_event.

    Returns (response_text, briefing_dict).
    """
    if _runner is not None:
        if on_event is not None:
            on_event("agent_start", "mission_commander", {})
            on_event("status", "mission_commander", {"text": "mock commander"})
            on_event(
                "agent_end",
                "mission_commander",
                {"ok": True, "duration_ms": 1},
            )
        return _runner(message), BriefingPayload().model_dump()

    accumulator = BriefingAccumulator()
    telemetry = MissionTelemetry(on_event=on_event, accumulator=accumulator)
    augmented = f"{clock_context()}\n\n{message}"
    with mission_control(telemetry=telemetry) as commander:
        result = commander(augmented)
    return str(result), accumulator.payload.model_dump()
