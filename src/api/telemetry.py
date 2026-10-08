"""Strands hook → AgentEvent bridge + briefing accumulation from tool results."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from api.models import (
    ApodCard,
    AsteroidCard,
    BriefingPayload,
    CloseApproachCard,
    EarthEventCard,
    SpaceWeatherCard,
)

logger = logging.getLogger(__name__)

EventEmitter = Callable[[str, str, dict[str, Any]], None]


def _safe_text(value: Any, limit: int = 600) -> str:
    text = value if isinstance(value, str) else str(value)
    text = text.strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _tool_use_parts(tool_use: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(tool_use, dict):
        name = str(tool_use.get("name") or "tool")
        args = tool_use.get("input") or tool_use.get("arguments") or {}
        if not isinstance(args, dict):
            args = {"value": args}
        return name, args
    name = str(getattr(tool_use, "name", None) or "tool")
    args = getattr(tool_use, "input", None) or getattr(tool_use, "arguments", None) or {}
    if not isinstance(args, dict):
        args = {"value": args}
    return name, args


def _result_to_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, Exception):
        return f"ERROR: {result}"
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
                else:
                    parts.append(str(block))
            return "\n".join(parts)
        if "structured_content" in result:
            try:
                return json.dumps(result["structured_content"])
            except TypeError:
                pass
        try:
            return json.dumps(result)
        except TypeError:
            return str(result)
    content = getattr(result, "content", None)
    if content is not None:
        return _result_to_text({"content": content})
    return str(result)


def _try_parse_json(text: str) -> Any | None:
    raw = text.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = raw.find(start_char)
        end = raw.rfind(end_char)
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


class BriefingAccumulator:
    """Build FE briefing cards from tool_result payloads (not raw NASA wire format in FE)."""

    def __init__(self) -> None:
        self.payload = BriefingPayload()

    def ingest(self, tool_name: str, result_text: str) -> None:
        parsed = _try_parse_json(result_text)
        if parsed is None:
            return
        try:
            if tool_name in ("search_asteroids", "get_asteroid"):
                self._ingest_asteroids(parsed)
            elif tool_name == "get_space_weather":
                self._ingest_weather(parsed)
            elif tool_name == "get_earth_events":
                self._ingest_earth(parsed)
            elif tool_name == "get_apod":
                self._ingest_apod(parsed)
        except Exception:
            logger.debug("Briefing ingest skipped for %s", tool_name, exc_info=True)

    def _ingest_asteroids(self, parsed: Any) -> None:
        items = parsed if isinstance(parsed, list) else [parsed]
        if isinstance(parsed, dict) and "result" in parsed:
            items = parsed["result"] if isinstance(parsed["result"], list) else [parsed["result"]]
        cards: list[AsteroidCard] = []
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            ca = item.get("close_approach")
            close = None
            if isinstance(ca, dict):
                close = CloseApproachCard(
                    date=str(ca.get("date", "")),
                    miss_distance_km=float(ca.get("miss_distance_km") or 0),
                    relative_velocity_kmh=float(ca.get("relative_velocity_kmh") or 0),
                )
            cards.append(
                AsteroidCard(
                    id=str(item["id"]),
                    name=str(item.get("name", "")),
                    potentially_hazardous=bool(item.get("potentially_hazardous", False)),
                    diameter_min_m=float(item.get("diameter_min_m") or 0),
                    diameter_max_m=float(item.get("diameter_max_m") or 0),
                    close_approach=close,
                )
            )
        if cards:
            # Merge by id (detail lookup updates / search replaces batch)
            by_id = {a.id: a for a in self.payload.asteroids}
            for card in cards:
                by_id[card.id] = card
            self.payload.asteroids = list(by_id.values())

    def _ingest_weather(self, parsed: Any) -> None:
        items = parsed if isinstance(parsed, list) else [parsed]
        if isinstance(parsed, dict) and "result" in parsed:
            items = parsed["result"] if isinstance(parsed["result"], list) else [parsed["result"]]
        cards = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cards.append(
                SpaceWeatherCard(
                    event_type=str(item.get("event_type", "")),
                    event_id=str(item.get("event_id", "")),
                    time=str(item.get("time", "")),
                    summary=str(item.get("summary", "")),
                )
            )
        if cards:
            self.payload.space_weather = cards

    def _ingest_earth(self, parsed: Any) -> None:
        items = parsed if isinstance(parsed, list) else [parsed]
        if isinstance(parsed, dict) and "result" in parsed:
            items = parsed["result"] if isinstance(parsed["result"], list) else [parsed["result"]]
        cards = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cats = item.get("categories") or []
            if not isinstance(cats, list):
                cats = [str(cats)]
            cards.append(
                EarthEventCard(
                    id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    categories=[str(c) for c in cats],
                    status=str(item.get("status", "open")),
                )
            )
        if cards:
            self.payload.earth_events = cards

    def _ingest_apod(self, parsed: Any) -> None:
        if not isinstance(parsed, dict) or "title" not in parsed:
            return
        media = parsed.get("media_type", "image")
        if media not in ("image", "video"):
            media = "image"
        self.payload.apod = ApodCard(
            title=str(parsed["title"]),
            date=str(parsed.get("date", "")),
            explanation=str(parsed.get("explanation", "")),
            url=str(parsed.get("url", "")),
            hdurl=parsed.get("hdurl"),
            media_type=media,  # type: ignore[arg-type]
            copyright=parsed.get("copyright"),
        )


class MissionTelemetry:
    """Attach Strands lifecycle hooks and emit Mission Control AgentEvents."""

    def __init__(
        self,
        on_event: EventEmitter | None = None,
        accumulator: BriefingAccumulator | None = None,
    ) -> None:
        self._emit: EventEmitter = on_event or (lambda *_a, **_k: None)
        self.accumulator = accumulator or BriefingAccumulator()
        self._started_at: dict[str, float] = {}

    def attach(self, agent: Any) -> None:
        """Register hooks on a Strands Agent instance."""
        try:
            from strands.hooks import (
                AfterInvocationEvent,
                AfterToolCallEvent,
                BeforeInvocationEvent,
                BeforeToolCallEvent,
            )
        except ImportError:
            # Older / alternate export paths
            from strands.hooks.events import (  # type: ignore[no-redef]
                AfterInvocationEvent,
                AfterToolCallEvent,
                BeforeInvocationEvent,
                BeforeToolCallEvent,
            )

        agent.add_hook(self._before_invocation, BeforeInvocationEvent)
        agent.add_hook(self._after_invocation, AfterInvocationEvent)
        agent.add_hook(self._before_tool, BeforeToolCallEvent)
        agent.add_hook(self._after_tool, AfterToolCallEvent)

    def _agent_name(self, event: Any) -> str:
        agent = getattr(event, "agent", None)
        name = getattr(agent, "name", None) if agent is not None else None
        return str(name or "agent")

    def _before_invocation(self, event: Any) -> None:
        name = self._agent_name(event)
        self._started_at[name] = time.perf_counter()
        self._emit("agent_start", name, {})
        self._emit("status", name, {"text": f"{name} started"})

    def _after_invocation(self, event: Any) -> None:
        name = self._agent_name(event)
        started = self._started_at.pop(name, None)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else None
        self._emit(
            "agent_end",
            name,
            {"ok": True, "duration_ms": duration_ms},
        )

    def _before_tool(self, event: Any) -> None:
        tool_name, args = _tool_use_parts(getattr(event, "tool_use", {}))
        self._emit(
            "tool_call",
            self._agent_name(event),
            {"tool": tool_name, "arguments": args},
        )
        self._emit(
            "status",
            self._agent_name(event),
            {"text": f"Calling {tool_name}"},
        )

    def _after_tool(self, event: Any) -> None:
        tool_name, _args = _tool_use_parts(getattr(event, "tool_use", {}))
        result = getattr(event, "result", None)
        ok = not isinstance(result, Exception)
        summary = _safe_text(_result_to_text(result))
        duration = getattr(event, "duration", None)
        duration_ms = int(duration * 1000) if isinstance(duration, (int, float)) else None
        if ok:
            self.accumulator.ingest(tool_name, summary)
        else:
            self._emit(
                "error",
                self._agent_name(event),
                {"message": summary, "tool": tool_name},
            )
        self._emit(
            "tool_result",
            self._agent_name(event),
            {
                "tool": tool_name,
                "ok": ok,
                "summary": summary,
                "duration_ms": duration_ms,
            },
        )
