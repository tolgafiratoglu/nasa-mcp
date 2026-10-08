"""Concrete date windows for Mission Control briefings (NeoWs ≤7 days)."""

from __future__ import annotations

from datetime import date, timedelta


def briefing_window(*, today: date | None = None) -> tuple[str, str]:
    """Return (start_iso, end_iso) for a 7-day inclusive window starting today."""
    start = today or date.today()
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def clock_context(*, today: date | None = None) -> str:
    """Short preamble so agents resolve 'this week' without asking the user."""
    start, end = briefing_window(today=today)
    return (
        f"[Mission Control clock: today={start}. "
        f"Default search window: {start} to {end} (7 days inclusive). "
        f"Resolve relative phrases like 'this week' / 'today' to these dates. "
        f"Never ask the user for dates — call tools with these YYYY-MM-DD values.]"
    )
