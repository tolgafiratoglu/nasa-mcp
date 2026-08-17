# NASA Mission Control MCP — Implementation Specification

## 1. Project Identity

**Name:** NASA Mission Control MCP

**One-liner:** A production-quality MCP server that turns multiple NASA data sources into semantically meaningful, AI-accessible tools with structured output.

**Goal:** Demonstrate MCP architecture — not merely wrap REST endpoints. An MCP-compatible host should discover NASA capabilities, select appropriate tools, combine results from multiple APIs, and produce mission-control-style briefings.

**What this is NOT:**
- A generic `call_nasa_api(endpoint, params)` wrapper
- A NASA chatbot
- A REST-to-MCP proxy

## 2. Runtime & Protocol

| Aspect | Decision |
|--------|----------|
| Language | Python 3.12+ |
| Protocol | MCP 2026-07-28 |
| SDK | MCP Python SDK v2 (stable) |
| Server class | `MCPServer` (not `FastMCP` — renamed in v2) |
| Transport | STDIO only (MVP) |
| HTTP client | `httpx2` (SDK v2 dependency, not `httpx`) |

### Key 2026-07-28 Protocol Facts

- `initialize`/`initialized` handshake removed. Every request is self-describing via `_meta` (carries `protocolVersion` + `clientCapabilities`; `clientInfo` is optional).
- `Mcp-Session-Id` removed. Any replica behind a round-robin load balancer can serve any request.
- `Mcp-Method` header required on all Streamable HTTP requests. `Mcp-Name` required only on `tools/call`, `resources/read`, `prompts/get`.
- Server-initiated requests (`elicitation/create`, `sampling/createMessage`, `roots/list`) removed. Replaced by Multi Round-Trip Requests (MRTR). Not used in MVP.
- `server/discover` is the optional discovery RPC (replaces handshake-based capability exchange).

### SDK v2 Import Map

```python
from mcp.server import MCPServer          # NOT FastMCP
from mcp.server import CacheHint
from mcp import Client                    # for testing
from mcp.types import ToolAnnotations
from mcp.server.mcpserver import MCPServerError  # NOT FastMCPError
```

Other v2 changes to remember:
- `McpError` → `MCPError`
- `ctx.fastmcp` → `ctx.mcp_server`
- `get_context()` removed — declare `ctx: Context` as parameter
- All wire type fields are `snake_case` in Python (`input_schema`, `is_error`)

## 3. Tools

### 3.1 Tool List

| Tool | NASA API | Description |
|------|----------|-------------|
| `search_asteroids` | NeoWs `/feed` | Search NEOs by close-approach date range |
| `get_asteroid` | NeoWs `/neo/{id}` | Detailed info for a specific asteroid |
| `get_space_weather` | DONKI | Space weather events by type and date |
| `get_earth_events` | EONET v3 | Active natural events (wildfires, storms, volcanoes...) |
| `get_apod` | APOD | Astronomy Picture of the Day |

### 3.2 Every Tool Must Have

- `async def`
- Typed inputs via type hints + `Annotated[..., Field(...)]`
- Pydantic `BaseModel` return type (structured output)
- `ToolAnnotations(read_only_hint=True)` — do NOT set `open_world_hint=False` (NASA APIs are open-world by nature; default `True` is correct)
- Clear docstring optimized for LLM tool selection
- NASA HTTP logic isolated from tool function body

### 3.3 Structured Output

The return type annotation IS the output schema. SDK automatically provides:
- `content` — text for the model
- `structured_content` — typed JSON for the application/frontend

```python
class Asteroid(BaseModel):
    name: str
    potentially_hazardous: bool
    diameter_min_m: float = Field(description="Minimum estimated diameter in meters.")
    diameter_max_m: float = Field(description="Maximum estimated diameter in meters.")
    miss_distance_km: float
    relative_velocity_kmh: float
    close_approach_date: str

@mcp.tool(
    title="Search near-Earth asteroids",
    annotations=ToolAnnotations(read_only_hint=True),
)
async def search_asteroids(
    start_date: Annotated[str, Field(description="Start date in YYYY-MM-DD format.")],
    end_date: Annotated[str, Field(description="End date in YYYY-MM-DD format.")],
    hazardous_only: Annotated[bool, Field(description="Filter to potentially hazardous asteroids only.")] = False,
) -> list[Asteroid]:
    """Search near-Earth asteroids by their close approach date to Earth.

    Returns asteroids with orbital data including estimated diameter,
    miss distance, and relative velocity. Date range limited to 7 days.
    """
    ...
```

For `list[T]` returns, SDK wraps as `{"result": [...]}` in `structured_content` and flattens each item to a separate `TextContent` block in `content`.

### 3.4 Tool Specifications

**`search_asteroids`**
```
Inputs:  start_date (str), end_date (str), hazardous_only (bool = False)
Returns: list[Asteroid]
Source:  NeoWs /feed
Notes:   NASA limits date range to 7 days. Validate and reject wider ranges.
```

**`get_asteroid`**
```
Inputs:  asteroid_id (str)
Returns: AsteroidDetail
Source:  NeoWs /neo/{id}
Notes:   Enables multi-tool reasoning: search → inspect pattern.
```

**`get_space_weather`**
```
Inputs:  event_type (Literal["CME", "FLR", "GST", "IPS", "MPC", "RBE", "HSS"]),
         start_date (str), end_date (str)
Returns: list[SpaceWeatherEvent]
Source:  DONKI /{event_type}
```

**`get_earth_events`**
```
Inputs:  categories (list[str] = []), days (int = 7),
         status (Literal["open", "closed", "all"] = "open"),
         bbox (str | None = None)
Returns: list[EarthEvent]
Source:  EONET v3 /events
Notes:   Returns GeoJSON-compatible coordinates. Categories: wildfires,
         volcanoes, severeStorms, seaLakeIce, etc.
```

**`get_apod`**
```
Inputs:  date (str | None = None)
Returns: APODResult
Source:  APOD
Notes:   Simple but strong for visual demo. Returns image URL + explanation.
```

## 4. Resources

| URI | Content | Cache Hint |
|-----|---------|------------|
| `nasa://glossary` | Definitions of NEO, CME, AU, miss distance, potentially hazardous asteroid, solar flare, geomagnetic storm, etc. | `ttl_ms=86_400_000, scope="public"` |
| `nasa://eonet/categories` | EONET event categories with IDs and descriptions | `ttl_ms=86_400_000, scope="public"` |

Resources provide contextual knowledge to the LLM. The glossary helps the model interpret tool results correctly (e.g., understanding what "potentially hazardous" means in NASA's classification).

```python
mcp = MCPServer(
    "NASA Mission Control",
    cache_hints={
        "tools/list": CacheHint(ttl_ms=60_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=86_400_000, scope="public"),
    },
)
```

Note: `ttlMs`/`cacheScope` default to `0`/`"private"` (immediately stale, never shared). These are protocol-level hints for MCP clients, NOT access control mechanisms. Safe for NASA data since all content is identical for every caller.

## 5. Prompts

**`daily-mission-briefing`**

```python
@mcp.prompt(title="Daily Mission Briefing")
def daily_mission_briefing() -> str:
    """Generate today's NASA Mission Control briefing."""
    return (
        "Create today's NASA Mission Control Briefing.\n\n"
        "Include:\n"
        "- Near-Earth asteroids approaching this week (flag any potentially hazardous)\n"
        "- Recent significant space weather events\n"
        "- Currently active major natural events on Earth\n"
        "- Today's Astronomy Picture of the Day\n\n"
        "Investigate anything unusual in more detail."
    )
```

This prompt triggers multi-tool orchestration: the LLM discovers and calls `search_asteroids`, `get_space_weather`, `get_earth_events`, `get_apod`, and optionally `get_asteroid` for notable objects.

## 6. NASA Client Architecture

```
NASA APIs
    │
    ▼
┌──────────────────────────┐
│ BaseNASAClient           │
│                          │
│ httpx2.AsyncClient       │
│ API key management       │
│ Timeout handling         │
│ Rate-limit headers       │
│ Retry with backoff       │
│ TTLCache (cachetools)    │
│ Structured error mapping │
└─────────────┬────────────┘
              │
    ┌─────────┼─────────┬──────────┐
    ▼         ▼         ▼          ▼
 NeoWs    DonkiClient EonetClient ApodClient
 Client
```

### 6.1 Base Client Responsibilities

- `httpx2.AsyncClient` with configurable timeout (default 30s)
- NASA API key from `NASA_API_KEY` environment variable
- Read `X-RateLimit-Remaining` headers; back off before hitting limits
- Retry on 429/5xx with exponential backoff (max 3 attempts)
- Per-client `cachetools.TTLCache` for upstream NASA responses

### 6.2 Upstream Cache TTLs (Initial)

| Client | TTL | Rationale |
|--------|-----|-----------|
| ApodClient | 6h | Changes once per day |
| NeoWsClient | 15min | Orbital data updates infrequently |
| DonkiClient | 10min | Space weather events arrive periodically |
| EonetClient | 5min | Natural events can change status rapidly |

### 6.3 Error Handling

NASA HTTP errors must be mapped to structured, informative tool errors — not raw stack traces.

```python
class NASAError(Exception):
    """Base exception for NASA API errors."""
    def __init__(self, error_type: str, message: str, retryable: bool = False):
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
```

Error types:
- `UPSTREAM_RATE_LIMIT` — NASA 429 (retryable)
- `UPSTREAM_TIMEOUT` — Request timeout (retryable)
- `UPSTREAM_ERROR` — NASA 5xx (retryable)
- `INVALID_PARAMETERS` — Bad date format, range too wide, etc. (not retryable)
- `NO_DATA` — Valid request but empty result set (not retryable)

In the tool layer, `NASAError` is caught and returned as a clear error result that the model can read and reason about, not a protocol-level `MCPError`.

## 7. Two Cache Layers

These are distinct and must not be confused:

| Layer | What it caches | Mechanism | Who benefits |
|-------|---------------|-----------|--------------|
| **MCP Response Cache** | `tools/list`, `resources/read` responses | `ttlMs`/`cacheScope` (protocol-level) | MCP client (avoids re-fetching tool schema, glossary) |
| **NASA Upstream Cache** | Raw NASA API responses | `cachetools.TTLCache` (application-level) | Server internals (avoids re-hitting NASA per tool call) |

## 8. Testing

### Strategy: `Client(mcp)` In-Memory Testing

SDK v2 provides `Client(server_object)` — connects directly in memory, no transport, no subprocess, no JSON-RPC framing.

```python
from mcp import Client
from nasa_mcp.server import mcp

async def test_search_asteroids():
    async with Client(mcp) as client:
        result = await client.call_tool("search_asteroids", {
            "start_date": "2026-08-18",
            "end_date": "2026-08-25",
        })
        assert not result.is_error
        assert result.structured_content is not None
        assert "result" in result.structured_content
```

### Test Categories

- **NASA adapter unit tests** — Mock `httpx2` responses, verify parsing/error handling
- **MCP contract tests** — `Client(mcp)` with mocked NASA clients, verify tool schemas, structured output, validation, error paths
- **Resource tests** — Verify glossary content, category list
- **Prompt tests** — Verify prompt message construction

### Test Pyramid

```
            Host integration (manual: Cursor + Inspector)
                     ▲
                    / \
                   /   \
             MCP contract (Client(mcp))
                 /       \
                /         \
        NASA adapter unit tests (mocked HTTP)
```

## 9. Observability

**Do NOT write custom tracing code.** SDK v2 includes OpenTelemetry middleware by default.

Every `MCPServer(...)` emits one `SERVER` span per inbound message:
- Span name: `tools/call search_asteroids`
- Attributes: `mcp.method.name`, `mcp.protocol.version`
- GenAI attributes: `gen_ai.operation.name` = `execute_tool`, `gen_ai.tool.name` = `search_asteroids`
- Error tools set span status to error automatically

Cost: near-zero (depends only on `opentelemetry-api`, no-op without exporter).

To activate, add exporter later:
```bash
uv add opentelemetry-sdk opentelemetry-exporter-otlp
```
Server code does not change.

When both sides use SDK, W3C trace context propagates automatically (client span → server span in one trace).

## 10. Logging

STDIO transport: `stdout` belongs to the protocol stream. Never use `print()`.

All logging via Python `logging` module → `stderr`. SDK configures this. Use `logging.getLogger(__name__)` in all modules.

## 11. Repository Structure

```
nasa-mcp/
├── src/
│   └── nasa_mcp/
│       ├── __init__.py
│       ├── server.py          # MCPServer + tools + resources + prompts
│       ├── models.py          # All Pydantic models (tool outputs)
│       └── clients/
│           ├── __init__.py
│           ├── base.py        # BaseNASAClient (httpx2, cache, retry, errors)
│           ├── neows.py       # NeoWsClient
│           ├── donki.py       # DonkiClient
│           ├── eonet.py       # EonetClient
│           └── apod.py        # ApodClient
├── tests/
│   ├── __init__.py
│   ├── test_server.py         # MCP contract tests via Client(mcp)
│   └── test_clients.py        # NASA adapter unit tests
├── pyproject.toml
├── .env.example
└── README.md
```

No separate `tools/`, `resources/`, `prompts/` directories for 5 tools. Split when it grows.

## 12. Environment

```env
# .env.example
NASA_API_KEY=your_api_key_here
```

- `DEMO_KEY`: 30 req/hour, 50 req/day per IP
- Registered key: 1000 req/hour
- Server reads from `NASA_API_KEY` env var
- Key never sent to MCP client

## 13. Explicitly NOT in MVP

| Feature | Reason to defer |
|---------|----------------|
| Streamable HTTP transport | STDIO sufficient for Cursor/Inspector |
| MRTR implementation | Model handles tool chaining without server-side questions |
| Redis cache | In-memory TTLCache sufficient for single-instance |
| Authentication/OAuth | Local-only MVP |
| EPIC tool | Second iteration |
| NASA Media Library tool | Second iteration |
| Leaflet/interactive map | Frontend phase |
| React frontend | Frontend phase |
| OTLP exporter backend | SDK traces are free; export when needed |
| Eval dashboard | Document in README, implement later |
| Docker | Not needed for local dev |

All of these are documented as future architecture in README.

## 14. Demo Scenarios

### Primary Demo
```
User: "Give me a mission briefing for the next 7 days."

LLM orchestration:
├── search_asteroids(start_date, end_date, hazardous_only=True)
├── get_asteroid(id)          ← for notable objects
├── get_space_weather(event_type="all", ...)
├── get_earth_events(days=7, status="open")
└── get_apod()

Output: Structured Mission Briefing
```

The value is not the answer — it's the LLM discovering tools, selecting the right ones, and orchestrating multi-tool reasoning.

### Secondary Demos
- "What potentially hazardous asteroids are approaching Earth this week?"
- "Were there any major solar events recently?"
- "Show active wildfires and volcanoes around the Pacific."
- "What's today's astronomy picture? Explain it simply."

## 15. Key Technical Decisions — Rationale

| Decision | Why |
|----------|-----|
| Domain tools, not generic REST wrapper | LLM needs semantic tool descriptions for tool selection |
| Pydantic structured output | Dual-channel: `content` for LLM, `structured_content` for UI |
| `read_only_hint=True` only | All tools are read-only; `open_world_hint` left as default `True` (NASA = external, changing data) |
| Annotations are hints only | `readOnlyHint` informs host approval policies, not a security mechanism |
| NASA HTTP isolated from tools | Tool functions call client methods; never touch `httpx2` directly |
| Two separate cache layers | MCP response cache (protocol) ≠ NASA upstream cache (application) |
| `Client(mcp)` testing | In-memory, no transport — SDK's recommended test pattern |
| Built-in OTel, no custom tracing | SDK traces every request by default; adding code is redundant |
| `logging` not `print()` | STDIO stdout is protocol-owned |
| `httpx2` not `httpx` | SDK v2 dependency; `httpx` will cause import errors |
