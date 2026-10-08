"""Deterministic routing expectations for evaluation (no live LLM).

These rules mirror the Mission Commander system prompt. They are used by
tests to assert intended delegation — not a runtime router that replaces
the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteExpectation:
    """What a well-behaved Commander should touch for a query class."""

    specialists: frozenset[str]
    commander_mcp_tools: frozenset[str]
    # Tools that must NOT be used for this query class
    forbidden_specialists: frozenset[str] = frozenset()


def classify_query(query: str) -> str:
    """Coarse query class for evaluation scenarios."""
    q = query.lower()
    if any(
        key in q
        for key in (
            "mission briefing",
            "full briefing",
            "daily briefing",
            "briefing for the next",
            "briefing for this week",
        )
    ):
        return "full_briefing"
    if any(key in q for key in ("apod", "astronomy picture", "space picture", "picture of the day")):
        return "apod_only"
    if any(
        key in q
        for key in (
            "asteroid",
            "neo",
            "pha",
            "hazardous",
            "close approach",
            "near-earth",
        )
    ):
        return "asteroids"
    if any(
        key in q
        for key in ("space weather", "solar", "cme", "flare", "geomagnetic", "donki")
    ):
        return "space_weather"
    if any(
        key in q
        for key in ("wildfire", "volcano", "earth event", "eonet", "natural disaster")
    ):
        return "earth_events"
    return "unknown"


def expected_route(query: str) -> RouteExpectation:
    """Return expected specialist / tool sets for evaluation assertions."""
    kind = classify_query(query)
    if kind == "full_briefing":
        return RouteExpectation(
            specialists=frozenset(
                {
                    "asteroid_analyst",
                    "space_weather_analyst",
                    "earth_events_analyst",
                }
            ),
            commander_mcp_tools=frozenset({"get_apod"}),
        )
    if kind == "apod_only":
        return RouteExpectation(
            specialists=frozenset(),
            commander_mcp_tools=frozenset({"get_apod"}),
            forbidden_specialists=frozenset(
                {
                    "asteroid_analyst",
                    "space_weather_analyst",
                    "earth_events_analyst",
                }
            ),
        )
    if kind == "asteroids":
        return RouteExpectation(
            specialists=frozenset({"asteroid_analyst"}),
            commander_mcp_tools=frozenset(),
            forbidden_specialists=frozenset(
                {"space_weather_analyst", "earth_events_analyst"}
            ),
        )
    if kind == "space_weather":
        return RouteExpectation(
            specialists=frozenset({"space_weather_analyst"}),
            commander_mcp_tools=frozenset(),
            forbidden_specialists=frozenset(
                {"asteroid_analyst", "earth_events_analyst"}
            ),
        )
    if kind == "earth_events":
        return RouteExpectation(
            specialists=frozenset({"earth_events_analyst"}),
            commander_mcp_tools=frozenset(),
            forbidden_specialists=frozenset(
                {"asteroid_analyst", "space_weather_analyst"}
            ),
        )
    return RouteExpectation(specialists=frozenset(), commander_mcp_tools=frozenset())


def assert_no_unnecessary_calls(
    query: str,
    *,
    specialists_called: set[str],
    commander_tools_called: set[str],
) -> None:
    """Fail if observed calls violate the expected route for the query class."""
    exp = expected_route(query)
    unexpected_specialists = specialists_called & set(exp.forbidden_specialists)
    if unexpected_specialists:
        raise AssertionError(
            f"Unnecessary specialists for query {query!r}: {unexpected_specialists}"
        )
    if exp.specialists and not (specialists_called & set(exp.specialists)):
        raise AssertionError(
            f"Expected one of {set(exp.specialists)}, got {specialists_called}"
        )
    if exp.commander_mcp_tools and not (
        commander_tools_called & set(exp.commander_mcp_tools)
    ):
        # For apod_only / full_briefing we expect get_apod
        if exp.commander_mcp_tools == frozenset({"get_apod"}):
            raise AssertionError(
                f"Expected commander tools {set(exp.commander_mcp_tools)}, "
                f"got {commander_tools_called}"
            )
