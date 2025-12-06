from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TimelineEvent, TimelineResponse


# ---------------------------------------------------------------------------
# Low-level DB helpers for timeline loading (psycopg2, sync-style)
# ---------------------------------------------------------------------------


def get_timeline_db_url() -> str:
    """
    Return a PostgreSQL URL suitable for psycopg2.

    Mirrors the seed_data behavior:
    - Prefer SYNC_DATABASE_URL
    - Fall back to DATABASE_URL
    - Strip async driver suffixes.
    """
    url = (
        os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql:///2ndopinionmd"
    )
    return url.replace("+asyncpg", "").replace("+psycopg", "")


def _load_timeline_sync(patient_id: str) -> List[Dict[str, Any]]:
    """
    Synchronous loader for a patient's timeline from ehr.patient_timeline.

    Returns a list of dicts with the main timeline fields.
    Safe to wrap in asyncio.to_thread from async routes.
    """
    conn = psycopg2.connect(get_timeline_db_url())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    patient_id,
                    ts,
                    event_type,
                    source,
                    structured,
                    text,
                    embedding,
                    meta
                FROM ehr.patient_timeline
                WHERE patient_id = %s
                ORDER BY ts
                """,
                (patient_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


async def load_patient_timeline(patient_id: str) -> List[Dict[str, Any]]:
    """
    Async wrapper to load a patient's timeline.
    Uses a background thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(_load_timeline_sync, patient_id)


# ---------------------------------------------------------------------------
# Higher-level timeline context for EoH / RAG
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticLandscape:
    """
    Very lightweight, timeline-derived diagnostic landscape.

    Semantics:
    - Each field is a non-negative weight.
    - We enforce that the *normalized* weights sum to ~1.0 when serialized.
    - This is NOT a calibrated probability model – it's a qualitative
      landscape used for EoH reasoning and UI.

    Fields roughly correspond to:
      - ra_like: rheumatoid arthritis
      - sle_like: systemic lupus erythematosus
      - psa_like: psoriatic arthritis / spondyloarthritis spectrum
      - sjogren_like: Sjögren’s
      - mixed_ctd_like: MCTD / overlap CTD
      - vasculitis_like: systemic vasculitis cluster
      - other: everything else / non-immune / noise
    """

    ra_like: float = 0.0
    sle_like: float = 0.0
    psa_like: float = 0.0
    sjogren_like: float = 0.0
    mixed_ctd_like: float = 0.0
    vasculitis_like: float = 0.0
    other: float = 1.0

    def to_normalized_dict(self) -> Dict[str, float]:
        raw = {
            "ra_like": float(self.ra_like or 0.0),
            "sle_like": float(self.sle_like or 0.0),
            "psa_like": float(self.psa_like or 0.0),
            "sjogren_like": float(self.sjogren_like or 0.0),
            "mixed_ctd_like": float(self.mixed_ctd_like or 0.0),
            "vasculitis_like": float(self.vasculitis_like or 0.0),
            "other": float(self.other or 0.0),
        }
        total = sum(v for v in raw.values() if v > 0)
        if total <= 0:
            # fall back to other=1.0 if nothing fired
            return {
                "ra_like": 0.0,
                "sle_like": 0.0,
                "psa_like": 0.0,
                "sjogren_like": 0.0,
                "mixed_ctd_like": 0.0,
                "vasculitis_like": 0.0,
                "other": 1.0,
            }
        return {k: v / total for k, v in raw.items()}


# ---------------------------------------------------------------------------
# Diagnostic landscape computation helper
# ---------------------------------------------------------------------------


def compute_diagnostic_landscape_from_events(
    events: List[Dict[str, Any]]
) -> DiagnosticLandscape:
    """
    Heuristic baseline: infer a weak RA/SLE/PSA/etc landscape from the
    timeline.

    Priority order:
    1) If any event has `structured.diagnostic_landscape` with numeric
       fields, we respect that and normalize.
    2) Otherwise, we scan structured and text for disease hints.

    This is intentionally simple / interpretable and can be swapped
    out later for a calibrated model.
    """
    # 1) Respect any pre-computed landscape in structured
    for e in events:
        structured = e.get("structured") or {}
        if not isinstance(structured, dict):
            continue
        dl = structured.get("diagnostic_landscape")
        if isinstance(dl, dict) and dl:
            # Use only known keys; ignore extras
            return DiagnosticLandscape(
                ra_like=dl.get("ra_like", 0.0) or 0.0,
                sle_like=dl.get("sle_like", 0.0) or 0.0,
                psa_like=dl.get("psa_like", 0.0) or 0.0,
                sjogren_like=dl.get("sjogren_like", 0.0) or 0.0,
                mixed_ctd_like=dl.get("mixed_ctd_like", 0.0) or 0.0,
                vasculitis_like=dl.get("vasculitis_like", 0.0) or 0.0,
                other=dl.get("other", 0.0) or 0.0,
            )

    # 2) Weak keyword-based heuristic on structured + free text
    weights = {
        "ra_like": 0.0,
        "sle_like": 0.0,
        "psa_like": 0.0,
        "sjogren_like": 0.0,
        "mixed_ctd_like": 0.0,
        "vasculitis_like": 0.0,
        "other": 0.0,
    }

    def _bump(key: str, amount: float = 1.0) -> None:
        if key in weights:
            weights[key] += amount

    for e in events:
        structured = e.get("structured") or {}
        text = (e.get("text") or "").lower()

        if isinstance(structured, dict):
            dx_labels: List[str] = []
            for k in ("diagnoses", "diagnosis_labels", "dx_labels", "conditions"):
                v = structured.get(k)
                if isinstance(v, list):
                    dx_labels.extend([str(x).lower() for x in v])
                elif isinstance(v, str):
                    dx_labels.append(v.lower())

            raw_codes: List[str] = []
            for k in ("icd10", "icd10cm", "icd11", "snomed_codes", "codes"):
                v = structured.get(k)
                if isinstance(v, list):
                    raw_codes.extend([str(x).upper() for x in v])
                elif isinstance(v, str):
                    raw_codes.append(v.upper())

            haystack = " ".join(dx_labels + [text])

            # RA
            if (
                "rheumatoid arthritis" in haystack
                or " seropositive ra" in haystack
                or " ra " in f" {haystack} "
            ):
                _bump("ra_like", 2.0)
            if any(code.startswith("M05") or code.startswith("M06") for code in raw_codes):
                _bump("ra_like", 2.0)

            # SLE
            if "systemic lupus" in haystack or " sle " in f" {haystack} ":
                _bump("sle_like", 2.0)
            if any(code.startswith("M32") for code in raw_codes):
                _bump("sle_like", 2.0)

            # PsA / spondylo
            if "psoriatic arthritis" in haystack or "psoriatic arthropathy" in haystack:
                _bump("psa_like", 2.0)
            if "ankylosing spondylitis" in haystack or "axial spondyloarthritis" in haystack:
                _bump("psa_like", 1.5)
            if any(code.startswith("L40.5") or code.startswith("M45") for code in raw_codes):
                _bump("psa_like", 2.0)

            # Sjögren
            if "sjogren" in haystack or "sjögren" in haystack:
                _bump("sjogren_like", 2.0)

            # Mixed CTD / overlap
            if (
                "mixed connective" in haystack
                or "overlap connective" in haystack
                or "mctd" in haystack
            ):
                _bump("mixed_ctd_like", 2.0)

            # Vasculitis
            if "vasculitis" in haystack or "anca-associated" in haystack:
                _bump("vasculitis_like", 2.0)
            if any(code.startswith("M31") for code in raw_codes):
                _bump("vasculitis_like", 1.5)

        # Mild default bump to "other" for non-empty clinical content
        if text.strip():
            _bump("other", 0.2)

    return DiagnosticLandscape(
        ra_like=weights["ra_like"],
        sle_like=weights["sle_like"],
        psa_like=weights["psa_like"],
        sjogren_like=weights["sjogren_like"],
        mixed_ctd_like=weights["mixed_ctd_like"],
        vasculitis_like=weights["vasculitis_like"],
        other=weights["other"] or 1.0,
    )


@dataclass
class TimelineContext:
    patient_id: str
    events: List[Dict[str, Any]]
    event_count: int
    span_days: int
    key_signals: List[Dict[str, Any]]
    flare_features: List[Dict[str, Any]]
    diagnostic_landscape: DiagnosticLandscape
    context_text: str


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


@dataclass
class TimelineEngine:
    """
    Minimal Timeline Engine v1.

    Responsibilities:
    - Read from ehr.patient_timeline (via AsyncSession or helper)
    - Insert events into ehr.patient_timeline
    - Provide basic TimelineContext for EoH / RAG
    """

    # ------------------------------------------------------------------
    # Context building (for EoH / RAG)
    # ------------------------------------------------------------------

    def _build_context_from_events(
        self,
        events: List[Dict[str, Any]],
        patient_id: str,
    ) -> TimelineContext:
        event_count = len(events)

        # Compute span in days (simple)
        span_days = 0
        if event_count:
            ts_values = [e.get("ts") for e in events if e.get("ts") is not None]
            if ts_values:
                ts_values = sorted(ts_values)
                span_days = (ts_values[-1] - ts_values[0]).days

        key_signals: List[Dict[str, Any]] = []
        flare_features: List[Dict[str, Any]] = []

        for e in events:
            etype = (e.get("event_type") or "").lower()
            structured = e.get("structured") or {}
            text = e.get("text") or ""

            if etype == "flare":
                flare_features.append(
                    {
                        "ts": e.get("ts"),
                        "text": text,
                        "structured": structured,
                    }
                )

            if etype in {"visit", "lab", "symptom", "imaging", "medication"}:
                key_signals.append(
                    {
                        "ts": e.get("ts"),
                        "event_type": etype,
                        "summary": text[:240],
                    }
                )

        # Diagnostic landscape derived from timeline (weak prior)
        diag = compute_diagnostic_landscape_from_events(events)

        # Build a simple context text blob
        ctx_lines: List[str] = []
        for e in events:
            ts = e.get("ts")
            etype = e.get("event_type")
            text = e.get("text") or ""
            ctx_lines.append(f"[{ts}] ({etype}) {text}")
        context_text = "\n".join(ctx_lines)

        return TimelineContext(
            patient_id=patient_id,
            events=events,
            event_count=event_count,
            span_days=span_days,
            key_signals=key_signals,
            flare_features=flare_features,
            diagnostic_landscape=diag,
            context_text=context_text,
        )

    async def build_timeline_context_from_events(
        self,
        events: List[Dict[str, Any]],
        patient_id: str,
    ) -> TimelineContext:
        """
        Build a TimelineContext from a list of raw event dicts.

        Used by rag_stream_custom_endpoints once events are loaded via
        load_patient_timeline().
        """
        # No heavy CPU here, so just call directly.
        return self._build_context_from_events(events, patient_id)

    # ------------------------------------------------------------------
    # Read path (existing API)
    # ------------------------------------------------------------------

    async def get_timeline(
        self,
        session: AsyncSession,
        patient_id: str,
        limit: int = 100,
        offset: int = 0,
        event_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TimelineResponse:
        """
        Return a chronologically ordered slice of the patient timeline.
        """
        params: Dict[str, Any] = {"pid": patient_id, "limit": limit, "offset": offset}
        where_clauses = ["patient_id = :pid"]

        if event_types:
            where_clauses.append("event_type = ANY(:event_types)")
            params["event_types"] = event_types

        if start_date:
            where_clauses.append("ts >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_clauses.append("ts <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where_clauses)

        # Main query
        rows_q = await session.execute(
            text(
                f"""
                SELECT id,
                       patient_id,
                       ts,
                       event_type,
                       source,
                       structured,
                       text,
                       meta
                FROM ehr.patient_timeline
                WHERE {where_sql}
                ORDER BY ts ASC, id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = rows_q.mappings().all()

        # Total count (for pagination metadata)
        count_q = await session.execute(
            text(
                f"""
                SELECT COUNT(*) AS n
                FROM ehr.patient_timeline
                WHERE {where_sql}
                """
            ),
            params,
        )
        total_events = int(count_q.scalar_one() or 0)

        events: List[TimelineEvent] = []
        for r in rows:
            events.append(
                TimelineEvent(
                    id=r["id"],
                    patient_id=r["patient_id"],
                    ts=r["ts"],
                    event_type=r["event_type"],
                    source=r["source"],
                    structured=r["structured"],
                    text=r["text"],
                    meta=r["meta"] or {},
                )
            )

        return TimelineResponse(
            patient_id=patient_id,
            events=events,
            total_events=total_events,
        )

    # ------------------------------------------------------------------
    # Write path (existing API)
    # ------------------------------------------------------------------

    async def store_event(
        self,
        session: AsyncSession,
        event: "TimelineEventCreate",
    ) -> int:
        """
        Insert a single timeline event. Returns new ID.
        """
        from .models import TimelineEventCreate  # avoid circular

        if not isinstance(event, TimelineEventCreate):
            raise TypeError("event must be TimelineEventCreate")

        q = await session.execute(
            text(
                """
                INSERT INTO ehr.patient_timeline
                    (patient_id, ts, event_type, source, structured, text, meta)
                VALUES
                    (:patient_id, :ts, :event_type, :source, :structured, :text, :meta)
                RETURNING id
                """
            ),
            {
                "patient_id": event.patient_id,
                "ts": event.ts,
                "event_type": event.event_type,
                "source": event.source,
                "structured": event.structured,
                "text": event.text,
                "meta": event.meta or {},
            },
        )
        new_id = int(q.scalar_one())
        # caller is responsible for committing
        return new_id

    async def store_events_batch(
        self,
        session: AsyncSession,
        events: Sequence["TimelineEventCreate"],
    ) -> List[int]:
        """
        Insert many events in one transaction.
        Returns list of new IDs.
        """
        from .models import TimelineEventCreate  # avoid circular

        ids: List[int] = []
        for e in events:
            ids.append(await self.store_event(session, e))
        return ids