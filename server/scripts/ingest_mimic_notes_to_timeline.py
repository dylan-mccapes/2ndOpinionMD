# server/scripts/ingest_mimic_notes_to_timeline.py
from __future__ import annotations

import argparse
import json
import logging

import psycopg2
from psycopg2.extras import DictCursor, execute_values, Json
from openai import OpenAI

from server.timeline.models import TimelineEventCreate, EventType, EventSource
from server.timeline.seed_data import get_db_url

logger = logging.getLogger(__name__)


def fetch_mimic_notes(limit: int | None = None):
    conn = psycopg2.connect(get_db_url())
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            sql = """
                SELECT id, source, external_id, text, meta
                FROM rag_corpus
                WHERE source IN ('mimic3_note', 'mimic4_note')
                ORDER BY id
            """
            if limit:
                sql += " LIMIT %s"
                cur.execute(sql, (limit,))
            else:
                cur.execute(sql)
            rows = cur.fetchall()
            return rows
    finally:
        conn.close()


def note_to_event(row) -> TimelineEventCreate:
    meta = row["meta"] or {}
    src = row["source"]
    # You can tune this mapping once you see meta structure
    subject_id = meta.get("subject_id") or meta.get("patient_id") or "UNKNOWN"
    charttime = meta.get("charttime") or meta.get("note_time")  # ISO string ideally

    # Fallback: if no timestamp, treat as now (only for demo)
    from datetime import datetime, timezone
    if charttime:
        from dateutil.parser import parse as parse_dt
        ts = parse_dt(charttime)
    else:
        ts = datetime.now(timezone.utc)

    patient_id = f"{src.upper()}_{subject_id}"

    text = row["text"]
    meta_out = {
        "rag_corpus_id": row["id"],
        "source_corpus": src,
        "external_id": row["external_id"],
    }

    return TimelineEventCreate(
        patient_id=patient_id,
        ts=ts,
        event_type=EventType.NOTE,
        source=EventSource.EHR,
        structured={"note_type": meta.get("note_type"), "service": meta.get("service")},
        text=text,
        meta=meta_out,
    )


def embed_events(events):
    client = OpenAI()
    rows = []
    for e in events:
        event_type = e.event_type.value
        source = e.source.value
        emb_input = json.dumps(
            {
                "text": e.text,
                "structured": e.structured,
                "event_type": event_type,
                "source": source,
            },
            ensure_ascii=False,
        )
        try:
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=emb_input,
            ).data[0].embedding
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
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
    return rows


def insert_rows(rows):
    sql = """
        INSERT INTO ehr.patient_timeline
            (patient_id, ts, event_type, source, structured, text, embedding, meta)
        VALUES %s
    """
    conn = psycopg2.connect(get_db_url())
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Error inserting rows: %s", exc)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill MIMIC notes into ehr.patient_timeline"
    )
    parser.add_argument("--limit", type=int, help="Optional limit for testing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    rows = fetch_mimic_notes(limit=args.limit)
    logger.info("Fetched %d MIMIC notes", len(rows))

    events = [note_to_event(r) for r in rows]
    logger.info("Built %d timeline events", len(events))

    if args.dry_run:
        print(json.dumps([e.model_dump() for e in events[:5]], indent=2, default=str))
        return

    embedded = embed_events(events)
    insert_rows(embedded)
    logger.info("Inserted %d events into ehr.patient_timeline", len(embedded))


if __name__ == "__main__":
    main()
