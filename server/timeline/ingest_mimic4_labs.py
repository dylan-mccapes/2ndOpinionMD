# server/timeline/ingest_mimic4_labs.py

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Iterable
import json

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values, Json
from datetime import timezone

from openai import OpenAI

from server.timeline.models import EventType, EventSource, LabResult, TimelineEventCreate
from server.timeline.engine import get_timeline_db_url

logger = logging.getLogger(__name__)


def get_conn():
    url = get_timeline_db_url()
    return psycopg2.connect(url)


def iter_mimic4_lab_rows(
    subject_ids: Iterable[int],
    itemids: Iterable[int] | None = None,
    limit_per_subject: int = 2000,
):
    """
    Stream joined rows from ehr_mimic4.labevents + d_labitems for a given cohort.
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for sid in subject_ids:
                params: Dict[str, Any] = {"sid": sid, "limit": limit_per_subject}
                item_filter = ""
                if itemids:
                    params["itemids"] = list(itemids)
                    item_filter = "AND le.itemid = ANY(%(itemids)s)"

                cur.execute(
                    f"""
                    SELECT
                        le.subject_id,
                        le.hadm_id,
                        le.charttime,
                        le.itemid,
                        le.valuenum,
                        le.valueuom,
                        le.value,
                        li.label,
                        li.category,
                        li.fluid
                    FROM ehr_mimic4.labevents AS le
                    JOIN ehr_mimic4.d_labitems AS li
                      ON le.itemid = li.itemid
                    WHERE le.subject_id = %(sid)s
                      {item_filter}
                    ORDER BY le.charttime ASC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                for row in cur:
                    yield row
    finally:
        conn.close()


def lab_row_to_timeline_event(row: Dict[str, Any]) -> TimelineEventCreate:
    """
    Map a single MIMIC-IV lab event row to a TimelineEventCreate.
    """
    from server.timeline.models import LabResult  # local import to avoid cycles

    # Internal patient_id: keep it explicit so you don't collide with synthetic IDs
    patient_id = f"MIMIC4_{row['subject_id']}"

    # Build structured LabResult
    val = row["valuenum"]
    unit = row["valueuom"] or ""

    lab_struct = LabResult(
        test_name=row["label"],      # human-readable label from d_labitems
        value=val,
        unit=unit,
        reference_range="",          # MIMIC doesn't have per-row ref; can backfill later
        flag=None,                   # we can compute later if you want
    ).model_dump()

    # Short narrative text for embedding / RAG:
    numeric_str = f"{val} {unit}".strip() if val is not None else (row["value"] or "").strip()
    text_bits = [
        f"Lab: {row['label']}",
        f"Value: {numeric_str}" if numeric_str else "",
        f"Category: {row['category']}",
        f"Fluid: {row['fluid']}",
    ]
    text = ". ".join(b for b in text_bits if b) + "."

    meta = {
        "source": "mimic4_labevents",
        "subject_id": int(row["subject_id"]),
        "hadm_id": int(row["hadm_id"]) if row["hadm_id"] is not None else None,
        "itemid": int(row["itemid"]),
        "category": row["category"],
        "fluid": row["fluid"],
    }

    return TimelineEventCreate(
        patient_id=patient_id,
        ts=row["charttime"].replace(tzinfo=timezone.utc),
        event_type=EventType.LAB,
        source=EventSource.EHR,  # or EventSource.MIMIC4 if you add it
        structured=lab_struct,
        text=text,
        meta=meta,
    )


def embed_and_insert(events: List[TimelineEventCreate]) -> int:
    """
    Mirror the pattern from seed_data.seed_patient_data:
    embed each event and bulk insert into ehr.patient_timeline.
    """
    if not events:
        return 0

    client = OpenAI()
    rows = []

    for e in events:
        event_type = e.event_type.value if hasattr(e.event_type, "value") else e.event_type
        source = e.source.value if hasattr(e.source, "value") else e.source

        # Build a plain string for the embeddings API
        # (You can tweak this formatting later if you want different weighting.)
        try:
            structured_str = json.dumps(e.structured or {}, ensure_ascii=False, sort_keys=True)
        except Exception:
            structured_str = "{}"

        emb_input = (
            f"Event type: {event_type}\n"
            f"Source: {source}\n"
            f"Text: {e.text}\n"
            f"Structured: {structured_str}"
        )

        try:
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=emb_input,  # <-- now a string, valid for the API
            )
            emb = resp.data[0].embedding
        except Exception as exc:
            logger.error(f"Embedding failed for lab event {e.meta}: {exc}")
            emb = None

        rows.append(
            (
                e.patient_id,
                e.ts,
                event_type,
                source,
                Json(e.structured or {}),
                e.text,
                emb,
                Json(e.meta or {}),
            )
        )

    sql = """
        INSERT INTO ehr.patient_timeline
            (patient_id, ts, event_type, source, structured, text, embedding, meta)
        VALUES %s
    """

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
        logger.info(f"Inserted {len(rows)} lab events into ehr.patient_timeline")
        return len(rows)
    except Exception as exc:
        conn.rollback()
        logger.error(f"Error inserting lab events: {exc}")
        raise
    finally:
        conn.close()


def ingest_mimic4_labs_for_subjects(subject_ids: Iterable[int], itemids=None, limit_per_subject: int = 2000):
    batch: List[TimelineEventCreate] = []
    for row in iter_mimic4_lab_rows(subject_ids, itemids=itemids, limit_per_subject=limit_per_subject):
        batch.append(lab_row_to_timeline_event(row))
        if len(batch) >= 512:
            embed_and_insert(batch)
            batch.clear()

    if batch:
        embed_and_insert(batch)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-ids", type=str, required=True,
                        help="Comma-separated list of MIMIC-IV subject_ids")
    parser.add_argument("--limit-per-subject", type=int, default=2000)
    args = parser.parse_args()

    subject_ids = [int(x.strip()) for x in args.subject_ids.split(",") if x.strip()]
    ingest_mimic4_labs_for_subjects(subject_ids, limit_per_subject=args.limit_per_subject)
