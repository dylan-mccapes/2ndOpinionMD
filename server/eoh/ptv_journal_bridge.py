"""
Mirror journal rows into PatientTimelineVision (ehr.patient_graph_vision).

- event_type ``journal_entry``: standard journal mirror.
- event_type ``patient_reported_outcome``: FORWARD / PRO payloads stored on the row
  (``JournalEntry.patient_reported_outcomes``) — explicit patient-reported outcomes.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from server.eoh.patient_timeline_vision import PatientTimelineVision, TimelineEventVision

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

EVENT_TYPE_JOURNAL = "journal_entry"
EVENT_TYPE_PATIENT_REPORTED_OUTCOME = "patient_reported_outcome"
EVENT_TYPE_ARTIFACT = "patient_artifact"
EVENT_TYPE_MOCK = "mock_timeline_event"
DISCOVERED_BY = "journal_mirror"
DISCOVERED_ARTIFACT = "vault_artifact_upload"
DISCOVERED_MOCK = "mock_timeline_ingest"


def journal_graph_event_id(journal_entry_id: str) -> str:
    return f"journal_{journal_entry_id}"


def _entry_timestamp_iso(entry: Any) -> str:
    dt = getattr(entry, "date", None) or getattr(entry, "created_at", None)
    if dt is None:
        return datetime.now(timezone.utc).isoformat()
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(timezone.utc).isoformat()
    return dt.isoformat() + "Z" if not str(dt).endswith("Z") else str(dt)


def _preview_for_entry(entry: Any, max_len: int = 800) -> str:
    parts: List[str] = []
    notes = getattr(entry, "notes", None) or ""
    if notes.strip():
        parts.append(notes.strip())
    sym = getattr(entry, "symptoms", None)
    if sym:
        parts.append(f"symptoms={json.dumps(sym, default=str)[:400]}")
    if not parts:
        parts.append("(journal entry)")
    text = " | ".join(parts)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def resolve_journal_mirror_event_type(entry: Any) -> str:
    raw = getattr(entry, "patient_reported_outcomes", None)
    if raw is None:
        return EVENT_TYPE_JOURNAL
    if isinstance(raw, dict) and raw:
        return EVENT_TYPE_PATIENT_REPORTED_OUTCOME
    if isinstance(raw, list) and len(raw) > 0:
        return EVENT_TYPE_PATIENT_REPORTED_OUTCOME
    return EVENT_TYPE_JOURNAL


def empty_user_vision(patient_id: str) -> PatientTimelineVision:
    built_at = datetime.now(timezone.utc).isoformat()
    return PatientTimelineVision(
        patient_id=str(patient_id),
        built_at=built_at,
        session_only=False,
        events={},
        arcs={},
        metadata={
            "pro": {
                "source": "2opmd",
                "forward": {"patient_reported_outcomes_channel": True},
                "mirrored_journal_ids": [],
            }
        },
    )


async def vision_row_exists(pool: "asyncpg.Pool", patient_id: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM ehr.patient_graph_vision WHERE patient_id = $1",
            str(patient_id),
        )
    return row is not None


async def ensure_user_ptv_row(pool: Optional["asyncpg.Pool"], patient_id: str) -> None:
    """Create an empty PTV JSON row if missing (idempotent)."""
    if pool is None:
        return
    if await vision_row_exists(pool, patient_id):
        return
    vision = empty_user_vision(str(patient_id))
    from server.eoh.patient_timeline_vision import save_timeline_vision_pg

    await save_timeline_vision_pg(pool, vision)
    await upsert_status_after_vision_write(pool, str(patient_id), vision)


async def upsert_status_after_vision_write(
    pool: "asyncpg.Pool", patient_id: str, vision: PatientTimelineVision
) -> None:
    """Keep ehr.patient_graph_status counts in sync; journal-only graphs stay not ready."""
    event_count = len(vision.events)
    edge_count = vision.count_edges()
    chart_count = 0
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*)::int AS c FROM ehr.patient_graph_chart WHERE patient_id = $1",
            patient_id,
        )
        if row:
            chart_count = int(row["c"] or 0)
    is_ready = event_count > 0 and chart_count > 0
    ts_real = 0
    from server.utils.parse_date import parse_clinical_date

    for e in vision.events.values():
        ts = (e.timestamp or "").strip().lower()
        if ts and ts not in ("unknown", "n/a", ""):
            if parse_clinical_date(e.timestamp) is not None:
                ts_real += 1
    ts_coverage = ts_real / event_count if event_count else 0.0

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ehr.patient_graph_status
                (patient_id, is_ready, event_count, edge_count, chart_count,
                 ts_coverage, built_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (patient_id)
            DO UPDATE SET
                is_ready    = EXCLUDED.is_ready,
                event_count = EXCLUDED.event_count,
                edge_count  = EXCLUDED.edge_count,
                chart_count = EXCLUDED.chart_count,
                ts_coverage = EXCLUDED.ts_coverage,
                built_at    = EXCLUDED.built_at,
                updated_at  = NOW()
            """,
            patient_id,
            is_ready,
            event_count,
            edge_count,
            chart_count,
            float(ts_coverage),
        )


def _annotations_for_journal_mirror(entry: Any, event_type: str) -> dict:
    ann: dict = {
        "source": "journal",
        "journal_entry_id": str(entry.id),
        "user_id": str(entry.user_id),
    }
    if event_type == EVENT_TYPE_PATIENT_REPORTED_OUTCOME:
        raw = getattr(entry, "patient_reported_outcomes", None)
        ann["forward_patient_reported_outcomes"] = raw
    return ann


def _apply_journal_event_to_vision(vision: PatientTimelineVision, entry: Any) -> None:
    eid = journal_graph_event_id(str(entry.id))
    event_type = resolve_journal_mirror_event_type(entry)
    ts = _entry_timestamp_iso(entry)
    preview = _preview_for_entry(entry)
    ann = _annotations_for_journal_mirror(entry, event_type)

    if eid in vision.events:
        del vision.events[eid]

    ev = TimelineEventVision(
        event_id=eid,
        event_type=event_type,
        timestamp=ts,
        preview=preview,
        discovered_by=[DISCOVERED_BY],
        annotations=ann,
    )
    vision.events[eid] = ev

    pro = vision.metadata.setdefault(
        "pro",
        {
            "source": "2opmd",
            "forward": {"patient_reported_outcomes_channel": True},
            "mirrored_journal_ids": [],
        },
    )
    mids: List[str] = pro.setdefault("mirrored_journal_ids", [])
    jid = str(entry.id)
    if jid not in mids:
        mids.append(jid)


async def mirror_journal_entry_to_ptv(pool: Optional["asyncpg.Pool"], user_id: str, entry: Any) -> None:
    if pool is None:
        return
    patient_id = str(user_id)
    await ensure_user_ptv_row(pool, patient_id)
    from server.eoh.patient_timeline_vision import load_timeline_vision_pg, save_timeline_vision_pg

    vision = await load_timeline_vision_pg(pool, patient_id)
    if vision is None:
        vision = empty_user_vision(patient_id)
    if vision.patient_id != patient_id:
        vision.patient_id = patient_id

    _apply_journal_event_to_vision(vision, entry)
    await save_timeline_vision_pg(pool, vision)
    await upsert_status_after_vision_write(pool, patient_id, vision)


async def remove_journal_mirror_from_ptv(pool: Optional["asyncpg.Pool"], user_id: str, journal_entry_id: str) -> None:
    if pool is None:
        return
    patient_id = str(user_id)
    from server.eoh.patient_timeline_vision import load_timeline_vision_pg, save_timeline_vision_pg

    vision = await load_timeline_vision_pg(pool, patient_id)
    if not vision:
        return
    eid = journal_graph_event_id(str(journal_entry_id))
    if eid in vision.events:
        del vision.events[eid]
    pro = vision.metadata.get("pro") or {}
    mids = pro.get("mirrored_journal_ids") or []
    jid = str(journal_entry_id)
    if isinstance(mids, list) and jid in mids:
        pro = dict(pro)
        pro["mirrored_journal_ids"] = [x for x in mids if x != jid]
        vision.metadata["pro"] = pro
    await save_timeline_vision_pg(pool, vision)
    await upsert_status_after_vision_write(pool, patient_id, vision)


async def add_patient_artifact_event(
    pool: Optional["asyncpg.Pool"],
    user_id: str,
    *,
    filename: str,
    content_type: Optional[str],
    size_bytes: int,
    document_type: str,
    document_date: Optional[str],
    notes: Optional[str],
    text_snippet: Optional[str],
    # sha256 of raw file bytes — provided by callers that have the bytes
    content_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append a lightweight vault document node to PTV (no full timeline PDF pipeline).

    Returns a dict with ``event_id``, ``artifact_id``, ``sha256``, and
    ``is_duplicate`` so callers can reflect dedup state back to the UI.
    """
    if pool is None:
        raise RuntimeError("Database pool unavailable")
    patient_id = str(user_id)
    await ensure_user_ptv_row(pool, patient_id)
    from server.eoh.patient_timeline_vision import load_timeline_vision_pg, save_timeline_vision_pg
    from server.eoh.event_dedup import artifact_id_from_bytes, artifact_catalog_entry

    vision = await load_timeline_vision_pg(pool, patient_id)
    if vision is None:
        vision = empty_user_vision(patient_id)

    # ── Artifact-level dedup ──────────────────────────────────────────────
    sha = content_sha256 or ""
    if sha:
        artifact_id = f"art_{sha[:16]}"
    else:
        artifact_id = f"art_{uuid.uuid4().hex[:16]}"

    artifacts: List[Dict[str, Any]] = vision.metadata.setdefault("artifacts", [])
    existing = next((a for a in artifacts if a.get("artifact_id") == artifact_id), None)
    if existing:
        # Same file uploaded again — touch last_seen_at, return is_duplicate=True
        existing["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        await save_timeline_vision_pg(pool, vision)
        return {
            "event_id": existing.get("event_id", artifact_id),
            "artifact_id": artifact_id,
            "sha256": sha,
            "is_duplicate": True,
        }

    # ── Build event node ──────────────────────────────────────────────────
    eid = f"artifact_{artifact_id}"
    preview = (text_snippet or "").strip()[:800]
    if not preview:
        preview = f"{filename} ({size_bytes} bytes)"
    ts = datetime.now(timezone.utc).isoformat()
    ann: Dict[str, Any] = {
        "artifact_id": artifact_id,
        "artifact_sha256": sha,
        "artifact_filename": filename,
        "filename": filename,
        "mime": content_type or "",
        "size_bytes": size_bytes,
        "document_type": document_type,
        "document_date": document_date or "",
        "notes": notes or "",
        "source_artifacts": [{"artifact_id": artifact_id, "sha256": sha}],
    }
    vision.add_event(
        eid,
        EVENT_TYPE_ARTIFACT,
        ts,
        preview[:800],
        DISCOVERED_ARTIFACT,
        ann,
    )

    # ── Update artifact catalog in PTV metadata ───────────────────────────
    catalog_entry = artifact_catalog_entry(
        artifact_id=artifact_id,
        sha256=sha,
        filename=filename,
        mime=content_type or "",
        size_bytes=size_bytes,
        document_type=document_type,
        document_date=document_date,
        user_notes=notes,
        ingest_tier="A",
        events_extracted=0,
    )
    catalog_entry["event_id"] = eid
    artifacts.append(catalog_entry)

    await save_timeline_vision_pg(pool, vision)
    await upsert_status_after_vision_write(pool, patient_id, vision)
    return {
        "event_id": eid,
        "artifact_id": artifact_id,
        "sha256": sha,
        "is_duplicate": False,
    }


async def add_mock_timeline_events(
    pool: Optional["asyncpg.Pool"],
    user_id: str,
    events: List[Dict[str, Any]],
) -> int:
    """Append dev/mock clinical events to PTV for Epistemic Vault testing."""
    if pool is None:
        raise RuntimeError("Database pool unavailable")
    if not events:
        return 0
    patient_id = str(user_id)
    await ensure_user_ptv_row(pool, patient_id)
    from server.eoh.patient_timeline_vision import load_timeline_vision_pg, save_timeline_vision_pg

    vision = await load_timeline_vision_pg(pool, patient_id)
    if vision is None:
        vision = empty_user_vision(patient_id)
    n = 0
    for raw in events:
        if not isinstance(raw, dict):
            continue
        eid = str(raw.get("event_id") or f"mock_{uuid.uuid4().hex[:12]}")
        title = str(raw.get("title") or raw.get("preview") or "Mock event")
        ts = str(raw.get("timestamp") or raw.get("date") or datetime.now(timezone.utc).isoformat())
        et = str(raw.get("event_type") or EVENT_TYPE_MOCK)
        ann = raw.get("annotations") if isinstance(raw.get("annotations"), dict) else {}
        ann = {**ann, "source": "mock_timeline_ingest"}
        vision.add_event(eid, et, ts, title[:800], DISCOVERED_MOCK, ann)
        n += 1
    await save_timeline_vision_pg(pool, vision)
    await upsert_status_after_vision_write(pool, patient_id, vision)
    return n
