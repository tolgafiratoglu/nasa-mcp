"""Sample NASA API JSON fixtures for mocked adapter tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent


def load_fixture(name: str) -> Any:
    """Load a JSON fixture by filename (e.g. ``neows_feed.json``)."""
    path = FIXTURES_DIR / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
