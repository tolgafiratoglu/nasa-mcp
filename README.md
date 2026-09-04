# NASA Mission Control MCP

A portfolio-ready **Model Context Protocol (MCP)** server that turns NASA open data into semantic tools an AI host can discover, call, and chain — not a generic REST wrapper.

**One-liner:** Near-Earth asteroids, space weather, Earth natural events, and Astronomy Picture of the Day — structured for LLM tool use.

## Why MCP (not just another API client)

| Approach | What the host gets |
|----------|-------------------|
| Generic `call_nasa_api(endpoint, params)` | The model must know NASA URLs and schemas |
| **This project** | Named tools (`search_asteroids`, `get_space_weather`, …), Pydantic structured output, resources, and a briefing prompt |

The demo story is **search → inspect**: `search_asteroids` returns asteroid `id`s in `structured_content`; the host then calls `get_asteroid(id)` for detail.

## Architecture (short)

```text
MCP host (Cursor / Inspector)
        │  STDIO
        ▼
   MCPServer (tools / resources / prompts)
        │
   AppContext lifespan
        │  shared httpx2.AsyncClient
        ▼
   NeoWs · DONKI · EONET · APOD adapters
        │
   NASA Open APIs
```

- **SDK:** MCP Python SDK v2 (`MCPServer`), STDIO only
- **HTTP:** `httpx2` + retries / rate-limit backoff
- **Models:** Pydantic return types → `content` + `structured_content`
- **Observability:** SDK built-in OpenTelemetry (no custom tracing in MVP)

### Two cache layers

| Layer | What | Mechanism |
|-------|------|-----------|
| **MCP response cache** | `tools/list`, `resources/read` | Protocol `CacheHint` (`ttlMs` / `cacheScope`) for the client |
| **NASA upstream cache** | Raw NASA JSON | Per-adapter `cachetools.TTLCache` inside the server |

These are independent: protocol hints do not replace application caching, and vice versa.

## Surface

### Tools

| Tool | NASA source | Role |
|------|-------------|------|
| `search_asteroids` | NeoWs `/feed` | NEOs by close-approach date (max 7-day window); optional PHA filter |
| `get_asteroid` | NeoWs `/neo/{id}` | Detail for one asteroid (use `id` from search) |
| `get_space_weather` | DONKI | CME, flares, etc.; `event_type=ALL` fans out and merges newest-first |
| `get_earth_events` | EONET v3 | Open/closed natural events (wildfires, volcanoes, …) |
| `get_apod` | APOD | Astronomy Picture of the Day |

All tools use `ToolAnnotations(read_only_hint=True)`.

### Resources

| URI | Content |
|-----|---------|
| `nasa://glossary` | Short NEO / space-weather glossary |
| `nasa://eonet/categories` | EONET category reference |

### Prompt

| Name | Purpose |
|------|---------|
| `daily_mission_briefing` | Guides the host to combine asteroids, `ALL` space weather, Earth events, and APOD |

## Setup

Requirements: **Python 3.12+**, pip, a virtualenv.

```bash
git clone <this-repo>
cd nasa-mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # edit NASA_API_KEY if needed
```

### API key

| Key | Limits |
|-----|--------|
| `DEMO_KEY` | ~30 req/hour, ~50/day per IP (fine for a quick look; easy to hit) |
| Registered key | ~1000 req/hour — get one at [api.nasa.gov](https://api.nasa.gov/) |

Export before live runs:

```bash
export NASA_API_KEY=DEMO_KEY   # or your registered key
```

The key stays on the server; it is never sent to the MCP client.

## Run

### MCP Inspector (interactive)

```bash
source .venv/bin/activate
export NASA_API_KEY=DEMO_KEY
mcp dev src/nasa_mcp/server.py
```

Expect **5 tools**, **2 resources**, **1 prompt**.

### Cursor MCP config

Add something like this to your Cursor MCP settings (paths adjusted to your machine):

```json
{
  "mcpServers": {
    "nasa-mission-control": {
      "command": "/absolute/path/to/nasa-mcp/.venv/bin/python",
      "args": ["-m", "nasa_mcp.server"],
      "env": {
        "NASA_API_KEY": "DEMO_KEY"
      }
    }
  }
}
```

If `-m nasa_mcp.server` is not convenient, point at the file instead:

```json
{
  "mcpServers": {
    "nasa-mission-control": {
      "command": "/absolute/path/to/nasa-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/nasa-mcp/src/nasa_mcp/server.py"],
      "env": {
        "NASA_API_KEY": "DEMO_KEY"
      }
    }
  }
}
```

### Tests (mocked — no live NASA)

```bash
source .venv/bin/activate
python -m pytest tests/ -q
```

## Demo prompts

Try these in Cursor or Inspector after the server is connected:

- *Give me a mission briefing for the next 7 days.*
- *Which potentially hazardous asteroids are approaching Earth this week?* then *Tell me more about the closest one.*
- *Were there any major solar events recently?* (`get_space_weather` with `ALL` or `FLR` / `CME`)
- *Show active wildfires and volcanoes.*
- *What's today's astronomy picture? Explain it simply.*

### Primary demo (search → inspect)

```text
User: Which potentially hazardous asteroids are approaching Earth this week?
Host: search_asteroids(start_date=…, end_date=…, hazardous_only=true)

User: Tell me more about the closest one.
Host: get_asteroid(id)   ← id from previous structured_content
```

## Project layout

```text
src/nasa_mcp/
  server.py          # MCPServer, tools, resources, prompts, lifespan
  models.py          # Pydantic tool outputs
  validation.py      # Shared validators (e.g. bbox)
  clients/
    base.py          # httpx2, cache, retry, NASAError
    neows.py / donki.py / eonet.py / apod.py
tests/               # Mocked adapter + MCP contract tests
spec.md              # Product / protocol spec
planning.md          # Execution plan
```

## Out of MVP / future work

Not in this release (by design): Streamable HTTP, MRTR, Redis, auth, EPIC, NASA Media Library, map/React UI, Docker, OTLP exporter, eval dashboard.

## License / data

NASA API data is public; follow [api.nasa.gov](https://api.nasa.gov/) terms. This repo is a demonstration MCP server for portfolio use.
