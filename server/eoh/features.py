# server/eoh/features.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import asyncpg


async def load_timeline_events(
    conn: asyncpg.Connection,
    patient_id: str,
) -> List[Dict[str, Any]]:
    """
    Lightweight loader for a patient's timeline from ehr.patient_timeline.

    Uses asyncpg directly so it can be reused by both recompute jobs and
    on-demand feature extraction.
    """
    rows = await conn.fetch(
        """
        SELECT id,
               patient_id,
               ts,
               event_type,
               source,
               structured,
               text,
               meta
        FROM ehr.patient_timeline
        WHERE patient_id = $1
        ORDER BY ts ASC, id ASC
        """,
        patient_id,
    )
    return [
        {
            "id": r["id"],
            "patient_id": r["patient_id"],
            "ts": r["ts"],
            "event_type": r["event_type"],
            "source": r["source"],
            "structured": r["structured"] or {},
            "text": r["text"] or "",
            "meta": r["meta"] or {},
        }
        for r in rows
    ]


async def extract_features_for_patient(
    conn: asyncpg.Connection,
    patient_id: str,
) -> Dict[str, Any]:
    """
    Turn ehr.patient_timeline rows into a simple feature dict.

    This is M0 scaffolding: transparent rules, easy to refactor later into
    more sophisticated feature engineering.
    """
    events = await load_timeline_events(conn, patient_id)

    now = datetime.now(timezone.utc)
    last_90d = now - timedelta(days=90)
    last_365d = now - timedelta(days=365)

    n_flares_90d = 0
    n_flares_365d = 0
    max_crp_recent = None
    has_biologic = False

    ra_evidence = 0.0
    sle_evidence = 0.0

    for ev in events:
        ts = ev["ts"]
        et = (ev["event_type"] or "").lower()
        structured = ev.get("structured") or {}
        text = (ev.get("text") or "").lower()

        # Flare counts
        if et == "flare":
            if ts >= last_90d:
                n_flares_90d += 1
            if ts >= last_365d:
                n_flares_365d += 1

        # Labs
        if et == "lab":
            name = (structured.get("test_name") or "").lower()
            if name in ("crp", "c-reactive protein"):
                val = structured.get("value")
                if isinstance(val, (int, float)):
                    if max_crp_recent is None or val > max_crp_recent:
                        max_crp_recent = val

        # Medications (very coarse biologic detector)
        if et in ("medication", "med_change"):
            med_name = (structured.get("medication_name") or "").lower()
            if any(
                key in med_name
                for key in [
                    "adalimumab",
                    "infliximab",
                    "etanercept",
                    "golimumab",
                    "certolizumab",
                    "rituximab",
                    "tocilizumab",
                    "tnf",
                ]
            ):
                has_biologic = True

        # Crude diagnostic evidence signals (until coding is fully wired)
        if "rheumatoid arthritis" in text or "anti-ccp" in text:
            ra_evidence += 1.0
        if "systemic lupus" in text or "sle " in text or "anti-dsdna" in text:
            sle_evidence += 1.0

    return {
        "n_flares_90d": n_flares_90d,
        "n_flares_365d": n_flares_365d,
        "max_crp_recent": max_crp_recent,
        "has_biologic": has_biologic,
        "ra_evidence": ra_evidence,
        "sle_evidence": sle_evidence,
    }