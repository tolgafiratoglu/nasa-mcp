"""OpenTelemetry setup for Mission Control (console exporter by default).

Enable with ``OTEL_CONSOLE=1`` (or any truthy value). Soft-depends on
``opentelemetry-api`` / ``opentelemetry-sdk`` — if missing, tracing is a no-op.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_configured = False
_tracer: Any = None
_tool_latency: Any = None
_error_counter: Any = None


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def setup_tracing(service_name: str = "nasa-mission-control") -> bool:
    """Configure console OTel tracing + basic metrics. Returns True if active."""
    global _configured, _tracer, _tool_latency, _error_counter
    if _configured:
        return _tracer is not None
    _configured = True

    if not _truthy("OTEL_CONSOLE"):
        logger.debug("OTEL_CONSOLE not set — tracing disabled")
        return False

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError:
        logger.warning(
            "OTEL_CONSOLE set but OpenTelemetry packages missing. "
            "Install with: pip install -e '.[otel]'"
        )
        return False

    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("nasa.mission_control")

    reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=10_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("nasa.mission_control")
    _tool_latency = meter.create_histogram(
        name="nasa.tool.latency_ms",
        unit="ms",
        description="MCP / specialist tool call latency",
    )
    _error_counter = meter.create_counter(
        name="nasa.errors",
        unit="1",
        description="Tool and agent error count",
    )
    logger.info("OpenTelemetry console exporter enabled")
    return True


@contextmanager
def agent_span(name: str, **attributes: Any) -> Iterator[Any]:
    """Context manager for an agent invocation span (no-op if tracing off)."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(f"agent.{name}") as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


@contextmanager
def tool_span(tool_name: str, agent: str = "", **attributes: Any) -> Iterator[Any]:
    """Context manager for a tool call span."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(f"tool.{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        if agent:
            span.set_attribute("agent.name", agent)
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


def record_tool_latency(tool_name: str, duration_ms: float | None, *, ok: bool) -> None:
    if _tool_latency is None or duration_ms is None:
        return
    _tool_latency.record(duration_ms, {"tool": tool_name, "ok": str(ok)})


def record_error(kind: str, *, tool: str = "", agent: str = "") -> None:
    if _error_counter is None:
        return
    _error_counter.add(1, {"kind": kind, "tool": tool or "-", "agent": agent or "-"})
