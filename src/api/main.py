"""NASA AI Mission Control API — FastAPI entrypoint (port 8100)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

logging.basicConfig(level=logging.INFO)

try:
    from agents.tracing import setup_tracing

    setup_tracing()
except Exception:  # pragma: no cover - optional observability
    logging.getLogger(__name__).debug("Tracing setup skipped", exc_info=True)

app = FastAPI(
    title="NASA AI Mission Control API",
    description="HTTP/SSE bridge from the web UI to Strands Mission Commander.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def run() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8100, reload=False)


if __name__ == "__main__":
    run()
