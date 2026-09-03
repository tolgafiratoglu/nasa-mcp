# NASA Mission Control MCP — Plan

> Source: `spec.md`  
> Rules: `.cursor/rules/nasa-mcp.mdc`  
> Goal: Harden the existing MVP into a portfolio-ready demo.

---

## Working rules

1. **Do not start the next section until the current one is done.**
2. At the end of each section, the Agent links changed files and writes verification commands.
3. **The Agent may write mocked tests** and run **at most one** `pytest -q` per section.
4. On failure, fix the code; **do not re-run pytest** — leave the command for the user.
5. **The Agent must not:** call live NASA APIs, launch Inspector, consume API quota, or loop fail-fix-retry pytest.
6. **Live / E2E verification** (Inspector, Cursor, real NASA) belongs to the user.
7. Do not add out-of-spec features (EPIC, Media, frontend, Redis, Streamable HTTP, MRTR).
8. Avoid duplication; check `BaseNASAClient`, existing clients, and `models.py` first.

### Package management

```text
Keep existing pip + .venv.
No migration to uv during MVP hardening.
```

---

## Current status

| Area | Status |
|------|--------|
| Package skeleton (`pyproject.toml`, `src/nasa_mcp/`) | ✅ |
| `BaseNASAClient` + 4 NASA clients | ✅ (Section B harden done) |
| 5 tools + 2 resources + 1 prompt | ✅ (to be polished) |
| Pydantic models | ✅ (minor fixes remaining) |
| Basic test file | ✅ (spread across sections) |
| Cursor rules + `spec.md` | ✅ |
| Entry point (`if __name__ == "__main__"`) | ✅ |
| `.gitignore` | ✅ |
| `README.md` | ❌ |
| Shared HTTP client / lifespan | ❌ |
| `ALL` space weather | ❌ |
| Solid mocked tests | ❌ (write in B–E; B done for base client) |

---

## Section A — Repository baseline

**Goal:** Commit-ready, import-safe foundation.

### Tasks
- [x] `.gitignore` (`.venv/`, `__pycache__/`, `.env`, `.pytest_cache/`)
- [x] Guarded STDIO entry point at the end of `server.py`:

```python
if __name__ == "__main__":
    mcp.run()
```

> Import must not start the server. Inspector, tests, and `mcp run` import the module.

- [x] Verify `.env.example` (only `NASA_API_KEY`)

### Agent verification
```bash
source .venv/bin/activate
python -c "from nasa_mcp.server import mcp; print('OK')"
```

### User verification
Confirm that import does not leave a hanging server process.

---

## Section B — Client harden

**Goal:** Injectable shared HTTP, safe errors and retries.

### Tasks
- [x] `BaseNASAClient`: accept injected `httpx2.AsyncClient`
- [x] Do not open a new client per request; reuse a shared client
- [x] Cap oversized `Retry-After` values
- [x] Never leak API key into logs or exception text
- [x] Do not cache failed responses

### Tests (Agent writes; at most one mocked run)
- [x] `tests/test_clients.py` — focused on `BaseNASAClient`
- [x] 200 → success
- [x] 429 → retry
- [x] 500 → retry
- [x] timeout → `NASAError`
- [x] failed response → not cached
- [x] success → cached
- [x] API key absent from exception/log text
- [x] `Retry-After` cap applied

### Agent verification
```bash
source .venv/bin/activate
python -m pytest tests/test_clients.py -q
```

### User verification
Re-run the same command if you want.

---

## Section C — Server lifespan

**Goal:** Replace module-level clients with MCP lifespan.

### Tasks
- [ ] `AppContext` (neows, donki, eonet, apod)
- [ ] Lifespan: open shared `httpx2.AsyncClient` → build clients → yield → close
- [ ] Tools take clients from context instead of module-level `_apod_client`, etc.
- [ ] Import must not perform network I/O

### Tests (Agent writes; at most one mocked run)
- [ ] Importing `server.py` performs no HTTP
- [ ] Lifespan creates clients
- [ ] Lifespan shutdown closes the shared HTTP client

### Agent verification
```bash
python -c "from nasa_mcp.server import mcp; print(mcp)"
python -m pytest tests/ -q -k "lifespan or import"
```

### User verification
Confirm no NASA request is made at import time.

---

## Section D — Model and contract fixes

**Goal:** Close spec gaps and small bugs.

### Locked decisions
- [ ] Keep `Asteroid.id` required (search → inspect)
- [ ] `get_space_weather` event_type: `ALL | CME | FLR | GST | IPS | MPC | RBE | HSS`
- [ ] `"ALL"` = MCP convenience → DONKI fan-out + merge (newest first)
- [ ] Empty list = success (`[]`); `NO_DATA` only for detail lookups
- [ ] Tool signature: `categories: list[str] | None = None` (no mutable `[]`)
- [ ] APOD: `media_type` image/video; `hdurl` remains optional
- [ ] Validate bbox as four numbers when provided

### Tests (Agent writes; at most one mocked run)
- [ ] Model/schema validation tests
- [ ] NeoWs 7-day range rejection
- [ ] Malformed bbox rejection
- [ ] APOD optional `hdurl` absent is OK
- [ ] `Asteroid.id` required

### Agent verification
```bash
python -m pytest tests/ -q -k "model or contract or validation"
```

---

## Section E — Tools / resources / prompt polish

**Goal:** Make the domain surface demo-ready.

### Tasks
- [ ] Review 5 tool docstrings + `Field(description=...)`
- [ ] All tools use `ToolAnnotations(read_only_hint=True)`
- [ ] Move raw NASA parsing from server into clients where practical (SOLID)
- [ ] Keep `nasa://glossary` / `nasa://eonet/categories` short and clear
- [ ] `daily_mission_briefing` → encourage `ALL` space weather + search → inspect
- [ ] Cache hints: `tools/list` 60s public; `resources/read` 24h public

### Tests (Agent writes; at most one mocked MCP run)
- [ ] `Client(mcp)` — 5 tools listed
- [ ] Every tool has `read_only_hint=True`
- [ ] `structured_content` shape
- [ ] `search_asteroids` result includes `id`
- [ ] NASA failure → `is_error=True` (mock)
- [ ] Resources + prompt contract

### Agent verification
```bash
python -m pytest tests/test_server.py -q
```

### User verification (Inspector — live)
```bash
source .venv/bin/activate
mcp dev src/nasa_mcp/server.py
```
Check: 5 tools, 2 resources, 1 prompt are visible.

---

## Section F — Test suite completion

**Goal:** Close coverage gaps and finish the integration matrix. First tests are written in B–E, not here.

### Tasks
- [ ] Complete `tests/fixtures/` sample NASA JSON
- [ ] Adapter tests: neows, donki, eonet, apod
- [ ] Error matrix: invalid arg, empty list, unknown asteroid
- [ ] Automated tests must not call live NASA

### Agent verification
```bash
python -m pytest tests/ -q
```

### User verification
Full suite green.

---

## Section G — README and demo

**Goal:** CV / portfolio surface.

### Tasks
- [ ] README: what / why MCP / short architecture
- [ ] Setup + `NASA_API_KEY`
- [ ] Inspector: `mcp dev src/nasa_mcp/server.py`
- [ ] Cursor MCP config example
- [ ] Tool / resource / prompt table
- [ ] Demo prompts
- [ ] Short note on the two cache layers
- [ ] Future work: Streamable HTTP, frontend, EPIC… (out of MVP)

### User verification
A new developer can install and run from README alone.

---

## Section H — Live E2E acceptance (user)

**Goal:** Declare MVP complete. The Agent does not write code here.

### Checklist
- [ ] Inspector shows 5 tools + 2 resources + 1 prompt
- [ ] `get_apod` returns real data
- [ ] `get_space_weather` with `ALL` or a single type
- [ ] `get_earth_events` open events
- [ ] In Cursor: *Give me a mission briefing for the next 7 days.*
- [ ] pytest green (after Section F)

### Primary demo scenario (search → inspect)

```text
User: Which potentially hazardous asteroids are approaching Earth this week?
Host: search_asteroids(...)

User: Tell me more about the closest one.
Host: get_asteroid(id)   ← id from previous structured_content
```

This scenario shows the project's real message: LLM semantic tool discovery and carrying structured output from one tool into the next.

### Demo commands
```bash
source .venv/bin/activate
export NASA_API_KEY=...   # or DEMO_KEY (rate-limited)
mcp dev src/nasa_mcp/server.py
python -m pytest tests/ -v
```

---

## Out of MVP (not now)

Streamable HTTP · MRTR · Redis · Auth · EPIC · Media Library · Leaflet · React UI · Docker · OTLP exporter · Eval dashboard

---

## Progress order

```text
A  Repo baseline
B  Client harden          + BaseNASAClient mocked tests
C  Server lifespan        + lifespan/import tests
D  Model & contract       + validation tests
E  Surface polish         + MCP contract tests
F  Test suite completion
G  README
H  User live E2E          ← MVP done
```

---

## Next step

**Section C — Server lifespan.**
