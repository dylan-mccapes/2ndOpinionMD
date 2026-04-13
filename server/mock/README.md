# 2ndOpinionMD Mock Server

Full API mock for frontend UX development. Covers all 41 endpoints the frontend calls.
Zero external services — no Postgres, Redis, Ollama, or OpenAI needed.

## Start

```bash
# From project root (WSL or Windows, inside .BeatingHeart venv)
python -m server.mock.run
```

- Mock server: http://localhost:8100
- Swagger UI: http://localhost:8100/docs
- ReDoc: http://localhost:8100/redoc
- OpenAPI JSON: http://localhost:8100/openapi.json

## Point the frontend at the mock

```bash
# frontend/.env.local
VITE_API_BASE=http://localhost:8100
VITE_DEV_BYPASS_AUTH=true
```

Then:

```bash
cd frontend && npm run dev
# → http://localhost:3000 — all API calls hit the mock
```

## What's mocked

| Group | Endpoints | Notes |
|-------|-----------|-------|
| Auth | 9 | All return success instantly |
| Timeline | 6 | Loads real Norman PTV events via dev_fixtures |
| EoH | 2 | Static flare report + router plan with full EoH schemas |
| RAG/Streaming | 4 | Live SSE stream — shows all animation phases in StreamingDisplay |
| Journal | 5 | In-memory store, seeded with 3 entries, CRUD works |
| Patient portal | 3 | Returns Dr. House as linked doctor |
| Doctor portal | 5 | Returns Norman as patient |
| Chat | 4 | In-memory store, seeded with 5 messages, send/anchor works |
| Portal utilities | 3 | Static encounter note and transcription |

## Data

- **Timeline**: loaded from `artifacts/timeline_ollama_20260329_1805/` via `server/dev_fixtures.py`
- **Journal**: in-memory, resets on server restart, seeded with 3 realistic entries
- **Chat**: in-memory, seeded with 5 messages showing EoH reasoning
- **Everything else**: static JSON matching frontend TypeScript schemas exactly

## Ports

| Service | Port |
|---------|------|
| Mock server | 8100 |
| Real backend | 8000 |
| Vite dev server | 3000 |

Switch between mock and real backend by changing `VITE_API_BASE` in `frontend/.env.local`.
