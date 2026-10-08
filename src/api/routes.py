"""Chat + SSE routes for Mission Control."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import run_commander
from api.events import EventBuffer, event_store
from api.models import AgentEvent, ChatAccepted, ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _publish(
    buffer: EventBuffer,
    event_type: str,
    *,
    agent: str = "commander",
    data: dict | None = None,
) -> None:
    await buffer.publish(
        AgentEvent(
            type=event_type,  # type: ignore[arg-type]
            agent=agent,
            data=data or {},
            correlation_id=buffer.correlation_id,
        )
    )


def _threadsafe_emitter(
    buffer: EventBuffer,
    loop: asyncio.AbstractEventLoop,
) -> Any:
    def emit(event_type: str, agent: str, data: dict[str, Any]) -> None:
        event = AgentEvent(
            type=event_type,  # type: ignore[arg-type]
            agent=agent,
            data=data or {},
            correlation_id=buffer.correlation_id,
        )
        fut = asyncio.run_coroutine_threadsafe(buffer.publish(event), loop)
        try:
            fut.result(timeout=10)
        except Exception:
            logger.exception("Failed to publish telemetry event %s", event_type)

    return emit


async def _run_chat_job(buffer: EventBuffer, message: str) -> None:
    await _publish(
        buffer,
        "status",
        data={"text": "Mission Commander starting"},
    )
    started = time.perf_counter()
    loop = asyncio.get_running_loop()
    on_event = _threadsafe_emitter(buffer, loop)
    try:
        text, briefing = await asyncio.to_thread(run_commander, message, on_event)
        total_ms = int((time.perf_counter() - started) * 1000)
        await _publish(
            buffer,
            "message",
            data={
                "text": text,
                "briefing": briefing,
                "duration_ms": total_ms,
            },
        )
    except Exception as exc:
        logger.exception("Chat job failed for %s", buffer.correlation_id)
        await _publish(
            buffer,
            "error",
            data={
                "message": (
                    "Mission Control failed to complete the request. "
                    f"Details: {exc}"
                )
            },
        )
    finally:
        await buffer.complete()


@router.post("/chat", response_model=ChatAccepted, status_code=202)
async def post_chat(body: ChatRequest) -> ChatAccepted:
    request_id = uuid.uuid4().hex
    buffer = event_store.create(request_id)
    asyncio.create_task(_run_chat_job(buffer, body.message.strip()))
    return ChatAccepted(request_id=request_id)


@router.get("/chat/{request_id}/events")
async def chat_events(request_id: str) -> StreamingResponse:
    buffer = event_store.get(request_id)
    if buffer is None:
        raise HTTPException(status_code=404, detail="Unknown request_id")

    async def event_stream():
        queue = await buffer.subscribe()
        try:
            while True:
                item = await queue.get()
                if item is None:
                    yield "event: done\ndata: {}\n\n"
                    break
                payload = item.model_dump(mode="json")
                yield f"event: {item.type}\ndata: {json.dumps(payload)}\n\n"
        finally:
            await buffer.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
