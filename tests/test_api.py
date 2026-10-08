"""FastAPI chat/SSE tests — mocked Commander, no live LLM/NASA."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import set_commander_runner
from api.main import app


@pytest.fixture(autouse=True)
def _mock_commander():
    set_commander_runner(lambda message: f"Mock briefing for: {message}")
    yield
    set_commander_runner(None)


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_accepted_and_sse_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat", json={"message": "briefing please"})
        assert resp.status_code == 202
        request_id = resp.json()["request_id"]
        assert request_id

        events: list[dict] = []
        async with client.stream("GET", f"/api/chat/{request_id}/events") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: ") and line != "data: {}":
                    events.append(json.loads(line.removeprefix("data: ")))
                if line.startswith("event: done"):
                    break

        types = [e.get("type") for e in events]
        assert "status" in types
        assert "message" in types
        message = next(e for e in events if e["type"] == "message")
        assert "Mock briefing" in message["data"]["text"]
        assert "briefing" in message["data"]


@pytest.mark.asyncio
async def test_unknown_request_events_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/does-not-exist/events")
        assert resp.status_code == 404
