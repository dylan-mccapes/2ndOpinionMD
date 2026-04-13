import uuid
from fastapi import APIRouter, HTTPException
from server.mock.fixtures.journal import seed_entries, make_entry, MOCK_TIMELINE_BUNDLE

router = APIRouter(prefix="/api/journal", tags=["journal"])

# In-memory store — seeded on first import, persists per server session
_ENTRIES: list[dict] = seed_entries()


@router.get("")
@router.get("/")
async def list_entries():
    return _ENTRIES


@router.post("")
@router.post("/")
async def create_entry(body: dict = None):
    entry = make_entry(body or {}, f"jrn-{uuid.uuid4().hex[:8]}")
    _ENTRIES.append(entry)
    return entry


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str):
    global _ENTRIES
    before = len(_ENTRIES)
    _ENTRIES = [e for e in _ENTRIES if e["id"] != entry_id]
    if len(_ENTRIES) == before:
        raise HTTPException(status_code=404, detail="Entry not found")
    return None  # 204


@router.get("/timeline/{report_id}")
async def journal_timeline(report_id: str):
    return {**MOCK_TIMELINE_BUNDLE, "report_id": report_id}


@router.post("/query-ai")
async def query_ai(body: dict = None):
    question = (body or {}).get("question", "")
    return {
        "answer": (
            f"Based on your journal entries, the pattern most relevant to '{question}' "
            "is the correlation between poor sleep nights and next-day symptom severity spikes. "
            "This has appeared consistently across 8 of the last 12 journal entries. "
            "EoH M5 PSI assessment: index 1.4 — low-moderate symbolic distortion."
        ),
        "sources_used": 3,
        "confidence": "moderate",
    }
