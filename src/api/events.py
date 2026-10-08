"""In-memory buffered event queues for SSE subscribers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from api.models import AgentEvent


@dataclass
class EventBuffer:
    """Replay history for late SSE subscribers; signal completion when done."""

    correlation_id: str
    history: list[AgentEvent] = field(default_factory=list)
    _subscribers: list[asyncio.Queue[AgentEvent | None]] = field(default_factory=list)
    done: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, event: AgentEvent) -> None:
        async with self._lock:
            self.history.append(event)
            for queue in list(self._subscribers):
                await queue.put(event)

    async def complete(self) -> None:
        async with self._lock:
            self.done = True
            for queue in list(self._subscribers):
                await queue.put(None)

    async def subscribe(self) -> asyncio.Queue[AgentEvent | None]:
        queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
        async with self._lock:
            for event in self.history:
                await queue.put(event)
            if self.done:
                await queue.put(None)
            else:
                self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[AgentEvent | None]) -> None:
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)


class EventStore:
    def __init__(self) -> None:
        self._buffers: dict[str, EventBuffer] = {}

    def create(self, correlation_id: str) -> EventBuffer:
        buffer = EventBuffer(correlation_id=correlation_id)
        self._buffers[correlation_id] = buffer
        return buffer

    def get(self, correlation_id: str) -> EventBuffer | None:
        return self._buffers.get(correlation_id)


event_store = EventStore()
