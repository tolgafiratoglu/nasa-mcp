"""Commander runner — wraps existing agents.mission_control (no duplication)."""

from __future__ import annotations

from collections.abc import Callable

from agents.commander import mission_control

# Injectable for tests (mocked Commander).
CommanderRunner = Callable[[str], str]

_runner: CommanderRunner | None = None


def set_commander_runner(runner: CommanderRunner | None) -> None:
    global _runner
    _runner = runner


def run_commander(message: str) -> str:
    """Synchronously run Mission Commander; used from a worker thread."""
    if _runner is not None:
        return _runner(message)
    with mission_control() as commander:
        result = commander(message)
    return str(result)
