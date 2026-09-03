# NASA Mission Control MCP — Plan

> Kaynak: `spec.md`  
> Kural: `.cursor/rules/nasa-mcp.mdc`  
> Amaç: Mevcut MVP iskeletini harden edip, portföy/demo seviyesine getirmek.

---

## Çalışma kuralları

1. **Bir section bitmeden sonrakine geçme.**
2. Her section sonunda Agent: değişen dosyaları linkler + doğrulama komutlarını yazar.
3. **Agent mocked test yazabilir;** section sonunda **en fazla 1** `pytest -q` çalıştırır.
4. Fail olursa kodu düzeltir; **pytest'i tekrar koşmaz** — komutu kullanıcıya bırakır.
5. **Agent yapamaz:** live NASA API, Inspector, quota, fail-fix-retry pytest döngüsü.
6. **Live / E2E doğrulama** (Inspector, Cursor, gerçek NASA) sana ait.
7. Spec dışı özellik ekleme (EPIC, Media, frontend, Redis, Streamable HTTP, MRTR).
8. Kod tekrarı yapma; önce `BaseNASAClient`, client'lar, `models.py` kontrol et.

### Package management

```text
Mevcut pip + .venv ile devam.
MVP hardening sırasında uv'ye geçiş yok.
```

---

## Mevcut durum

| Bölüm | Durum |
|-------|--------|
| Paket iskeleti (`pyproject.toml`, `src/nasa_mcp/`) | ✅ |
| `BaseNASAClient` + 4 NASA client | ✅ (Section B harden done) |
| 5 tool + 2 resource + 1 prompt | ✅ (polish edilecek) |
| Pydantic models | ✅ (küçük düzeltmeler) |
| Temel test dosyası | ✅ (section'lara dağıtılacak) |
| Cursor rules + `spec.md` | ✅ |
| Entry point (`if __name__ == "__main__"`) | ✅ |
| `.gitignore` | ✅ |
| `README.md` | ❌ |
| Shared HTTP client / lifespan | ❌ |
| `ALL` space weather | ❌ |
| Mock'lu solid testler | ❌ (B–E'de yazılacak) |

---

## Section A — Repo temeli

**Amaç:** Commit'lenebilir, import-safe temel.

### Yapılacaklar
- [x] `.gitignore` (`.venv/`, `__pycache__/`, `.env`, `.pytest_cache/`)
- [x] `server.py` sonuna **guard'lı** STDIO entry point:

```python
if __name__ == "__main__":
    mcp.run()
```

> Import sırasında server başlamamalı. Inspector, testler ve `mcp run` dosyayı import eder.

- [x] `.env.example` kontrol (sadece `NASA_API_KEY`)

### Agent doğrulaması
```bash
source .venv/bin/activate
python -c "from nasa_mcp.server import mcp; print('OK')"
```

### Senin doğrulaman
Import sonrası server process başlamadığını kontrol et.

---

## Section B — Client harden

**Amaç:** Test edilebilir, shared HTTP, güvenli hata/retry.

### Yapılacaklar
- [x] `BaseNASAClient`: dışarıdan `httpx2.AsyncClient` inject edilebilsin
- [x] Her request'te yeni client açılmasın; shared client kullanılsın
- [x] `Retry-After` çok büyükse üst sınır (cap) uygula
- [x] API key log / exception text'e sızmasın
- [x] Failed response cache'lenmesin

### Testler (Agent yazar + çalıştırır — mocked)
- [x] `tests/test_clients.py` — `BaseNASAClient` odaklı
- [x] 200 → success
- [x] 429 → retry
- [x] 500 → retry
- [x] timeout → `NASAError`
- [x] failed response → not cached
- [x] success → cached
- [x] API key exception/log içinde yok
- [x] `Retry-After` cap uygulanıyor

### Agent doğrulaması
```bash
source .venv/bin/activate
python -m pytest tests/test_clients.py -q
```

### Senin doğrulaman
İstersen aynı komutu tekrar çalıştır.

---

## Section C — Server lifespan

**Amaç:** Module-level client yerine MCP lifespan.

### Yapılacaklar
- [ ] `AppContext` (neows, donki, eonet, apod)
- [ ] Lifespan: shared `httpx2.AsyncClient` aç → client'ları kur → yield → kapat
- [ ] Tool'lar module-level `_apod_client` vs. yerine context'ten alsın
- [ ] Import sırasında network çağrısı olmasın

### Testler (Agent yazar + çalıştırır — mocked)
- [ ] Import `server.py` → HTTP yok
- [ ] Lifespan client oluşturur
- [ ] Lifespan shutdown HTTP client'ı kapatır

### Agent doğrulaması
```bash
python -c "from nasa_mcp.server import mcp; print(mcp)"
python -m pytest tests/ -q -k "lifespan or import"
```

### Senin doğrulaman
Import anında NASA'ya istek gitmediğini doğrula.

---

## Section D — Model & contract düzeltmeleri

**Amaç:** Spec boşluklarını ve küçük bug'ları kapat.

### Kilitleyen kararlar
- [ ] `Asteroid.id` zorunlu kalsın (search → inspect)
- [ ] `get_space_weather` event_type: `ALL | CME | FLR | GST | IPS | MPC | RBE | HSS`
- [ ] `"ALL"` = MCP convenience → DONKI fan-out + merge (newest first)
- [ ] Boş liste = başarı (`[]`); `NO_DATA` sadece detail lookup'ta
- [ ] Tool'da `categories: list[str] | None = None` (mutable `[]` yok)
- [ ] APOD: `media_type` image/video; `hdurl` opsiyonel kalsın
- [ ] Bbox verilirse 4 sayı validate edilsin

### Testler (Agent yazar + çalıştırır)
- [ ] Model/schema validation testleri
- [ ] NeoWs 7-day range reject
- [ ] bbox malformed reject
- [ ] APOD optional `hdurl` absent OK
- [ ] `Asteroid.id` required

### Agent doğrulaması
```bash
python -m pytest tests/ -q -k "model or contract or validation"
```

---

## Section E — Tools / resources / prompt polish

**Amaç:** Domain surface'i demo'ya hazır hale getir.

### Yapılacaklar
- [ ] 5 tool docstring + `Field(description=...)` gözden geçir
- [ ] Hepsi `ToolAnnotations(read_only_hint=True)`
- [ ] Server'da raw NASA parse mümkünse client'a taşı (SOLID)
- [ ] `nasa://glossary` / `nasa://eonet/categories` kısa ve net kalsın
- [ ] `daily_mission_briefing` → `ALL` space weather + search → inspect teşviki
- [ ] Cache hints: `tools/list` 60s public; `resources/read` 24h public

### Testler (Agent yazar + çalıştırır — mocked MCP)
- [ ] `Client(mcp)` — 5 tool listed
- [ ] Her tool `read_only_hint=True`
- [ ] `structured_content` shape
- [ ] `search_asteroids` result includes `id`
- [ ] NASA failure → `is_error=True` (mock)
- [ ] Resources + prompt contract

### Agent doğrulaması
```bash
python -m pytest tests/test_server.py -q
```

### Senin doğrulaman (Inspector — live)
```bash
source .venv/bin/activate
mcp dev src/nasa_mcp/server.py
```
Kontrol: 5 tool, 2 resource, 1 prompt görünür.

---

## Section F — Test suite tamamlama

**Amaç:** Eksik coverage'ı kapat; integration matrix'i tamamla. İlk test burada değil, B–E'de yazıldı.

### Yapılacaklar
- [ ] `tests/fixtures/` — örnek NASA JSON'ları tamamla
- [ ] Adapter testleri: neows, donki, eonet, apod
- [ ] Error matrix: invalid arg, empty list, unknown asteroid
- [ ] Live NASA çağrısı otomatik testte olmasın

### Agent doğrulaması
```bash
python -m pytest tests/ -q
```

### Senin doğrulaman
Full suite yeşil.

---

## Section G — README & demo

**Amaç:** CV / portfolio yüzü.

### Yapılacaklar
- [ ] README: ne / neden MCP / mimari (kısa)
- [ ] Kurulum + `NASA_API_KEY`
- [ ] Inspector: `mcp dev src/nasa_mcp/server.py`
- [ ] Cursor MCP config örneği
- [ ] Tool / resource / prompt tablosu
- [ ] Demo prompt'lar
- [ ] İki cache layer kısa açıklama
- [ ] Future: Streamable HTTP, frontend, EPIC… (MVP dışı)

### Senin doğrulaman
README ile sıfırdan kurulum yapabilmek.

---

## Section H — Senin live E2E kabul

**Amaç:** MVP "bitti" kararı. Agent burada kod yazmaz.

### Checklist
- [ ] Inspector'da 5 tool + 2 resource + 1 prompt
- [ ] `get_apod` gerçek veri
- [ ] `get_space_weather` ile `ALL` veya tek tip
- [ ] `get_earth_events` open events
- [ ] Cursor'da: *Give me a mission briefing for the next 7 days.*
- [ ] pytest yeşil (Section F sonrası)

### Ana demo senaryosu (search → inspect)

```text
User: Which potentially hazardous asteroids are approaching Earth this week?
Host: search_asteroids(...)

User: Tell me more about the closest one.
Host: get_asteroid(id)   ← önceki structured_content'teki id
```

Bu senaryo projenin asıl mesajını gösterir: LLM semantic tool keşfi + structured output'un bir tool'dan diğerine taşınması.

### Demo komutları
```bash
source .venv/bin/activate
export NASA_API_KEY=...   # veya DEMO_KEY (limitli)
mcp dev src/nasa_mcp/server.py
python -m pytest tests/ -v
```

---

## MVP dışı (şimdilik yok)

Streamable HTTP · MRTR · Redis · Auth · EPIC · Media Library · Leaflet · React UI · Docker · OTLP exporter · Eval dashboard

---

## İlerleme sırası

```text
A  Repo temeli
B  Client harden        + BaseNASAClient mocked tests
C  Server lifespan      + lifespan/import tests
D  Model & contract     + validation tests
E  Surface polish       + MCP contract tests
F  Test suite completion
G  README
H  Senin live E2E       ← MVP bitti
```

---

## Sonraki adım

**Section A** ile başla.
