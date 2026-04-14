"""
2ndOpinionMD Mock Server
========================
Covers all frontend API endpoints with static/seeded responses.
Zero mandatory external dependencies — no Postgres/Redis/OpenAI required.
Optional: local Ollama for graph-backed mock chat replies.

Start: python -m server.mock.run
Docs:  http://localhost:8100/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.mock.routers import auth, timeline, eoh, rag, journal, patient, doctor, chat, portal

app = FastAPI(
    title="2ndOpinionMD Mock Server",
    description=(
        "Full mock API for frontend UX development. "
        "All endpoints return deterministic, schema-valid responses. "
        "SSE streaming endpoints simulate real token generation timing. "
        "Chat endpoint can optionally call local Ollama after graph traversal."
    ),
    version="0.1.0-mock",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow Vite dev server
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(timeline.router)
app.include_router(eoh.router)
app.include_router(rag.router)      # no prefix — routes are /api/rag/*, /api/coding
app.include_router(journal.router)
app.include_router(patient.router)
app.include_router(doctor.router)
app.include_router(chat.router)
app.include_router(portal.router)

# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["meta"])
async def health():
    return {"status": "ok", "mock": True, "server": "2ndOpinionMD Mock Server v0.1.0"}


@app.get("/api/meta/ping", tags=["meta"])
async def ping():
    return {"status": "pong", "mock": True}


@app.get("/api/openapi.json", include_in_schema=False)
async def openapi_json():
    return app.openapi()
