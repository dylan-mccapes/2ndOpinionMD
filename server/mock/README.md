# 2ndOpinionMD Mock Server

Full API mock for frontend UX development. Covers all 41 endpoints the frontend calls.
Zero external services — no Postgres, Redis, Ollama, or OpenAI needed.

## Start

```bash
# From project root (WSL or Windows, inside .BeatingHeart venv)
python -m server.mock.run
```

### Start in a specific UX mode

```bash
# Patient mode (default)
python -m server.mock.run --role patient

# Doctor portal mode
python -m server.mock.run --role doctor

# Use a specific Norman timeline export (decrypted-PDF derived PTV JSON)
python -m server.mock.run \
  --role doctor \
  --timeline-json "artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
```

### Graph-backed mock chat (LLM demo path)

By default, `POST /api/chat/send` runs a lightweight graph demo pipeline:

1. `graph_reduce`
2. `graph_hybrid_search` (`semantic=true`)
3. `graph_bfs_expand`
4. Ask local Ollama model (`eoh-llama-lucifer`) to summarize findings

This demonstrates the agentic graph workflow in UX sandbox mode.

You can disable this and use static replies:

```bash
python -m server.mock.run --no-llm
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
VITE_DEV_USER_TYPE=doctor   # or patient
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

- **Timeline**: loaded from Norman PTV JSON via `server/dev_fixtures.py` (override with `--timeline-json` / `DEV_TIMELINE_VISION_FILE`)
- **Journal**: in-memory, resets on server restart, seeded with 3 realistic entries
- **Chat**: in-memory, seeded with 5 messages; new messages can use local graph+LLM demo pipeline (`reduce -> semantic seeds -> BFS -> answer`)
- **Everything else**: static JSON matching frontend TypeScript schemas exactly

## Ports

| Service | Port |
|---------|------|
| Mock server | 8100 |
| Real backend | 8000 |
| Vite dev server | 3000 |

Switch between mock and real backend by changing `VITE_API_BASE` in `frontend/.env.local`.
