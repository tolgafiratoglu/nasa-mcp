# NASA AI Mission Control — Demo Guide

Step-by-step demo for interviews and local verification.

> Values in example timelines (counts, distances, durations) are **illustrative**.
> Live NASA data and LLM routing determine real outputs.

## Prerequisites

```bash
cd nasa-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,agents,api,otel]"

cp .env.example .env
# Set NASA_API_KEY (registered key recommended: https://api.nasa.gov/)
# Gemini: GEMINI_API_KEY or ~/.config/rag/.env (same as travel-rag)
# Or: LLM_PROVIDER=qwen + local Ollama
```

## Demo A — MCP only (Inspector)

```bash
export NASA_API_KEY=DEMO_KEY   # or your key
mcp dev src/nasa_mcp/server.py
```

1. Confirm **5 tools**, **2 resources**, **1 prompt**.
2. Call `search_asteroids` with a 7-day window and `hazardous_only=true`.
3. Copy an `id` from the result → call `get_asteroid` (**search → inspect**).

## Demo B — Multi-agent CLI

```bash
export LLM_PROVIDER=gemini
export NASA_API_KEY=...
export OTEL_CONSOLE=1          # optional: print OTel spans to stderr/stdout

python -m agents.cli "Are there any hazardous asteroids approaching Earth this week?"
python -m agents.cli "Give me a mission briefing for the next 7 days."
```

Expected routing (policy):

| Prompt | Expected |
|--------|----------|
| Hazardous asteroids… | `asteroid_analyst` only |
| Today's astronomy picture… | `get_apod` (no specialists) |
| Mission briefing… | 3 specialists + `get_apod` |

## Demo C — Web Mission Control

Terminal 1:

```bash
export OTEL_CONSOLE=1
python -m api.main
# http://127.0.0.1:8100
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
# http://localhost:3100
```

In the UI:

1. Ask: *Mission briefing for this week.*
2. Watch the **left** panel: Agent Timeline → Tool Calls → Execution.
3. Read the Commander reply in the **center**.
4. Briefing cards on the **right** fill when tool results parse into structured payloads.
5. Click an asteroid row → follow-up *Tell me more about…* (search → inspect).

## Latency baseline (fill after your first live run)

| Path | Your measurement | Notes |
|------|------------------|-------|
| `get_apod` only | _____ ms | Single tool |
| Asteroid search + detail | _____ ms | Specialist + 1–2 tools |
| Full briefing | _____ ms | 3 specialists + APOD; not parallel by default |

Record wall-clock from Execution panel `total … ms` or CLI wall time.

## Why multi-agent? (talking point)

A single prompt can call all five MCP tools. Multi-agent still helps:

1. **Tool whitelist per specialist** — safer than one agent with every NASA tool.
2. **Isolated prompts** — each specialist stays on-domain.
3. **Testable routing policy** — evaluation asserts expected specialists per query class.
4. **Observable delegation** — timeline shows who ran and which tools fired.

## Why Strands, not AutoGen?

- AutoGen is in **maintenance mode**; Microsoft points new work at Agent Framework.
- Strands has **native MCP STDIO** clients and a simple **agents-as-tools** pattern.
- One orchestration framework keeps the portfolio story explainable.
