# server/scripts/ingest_timeline_labs.py
from __future__ import annotations

import argparse
import json
import logging
import os

import psycopg2
from psycopg2.extras import execute_values, Json
from openai import OpenAI

from server.timeline.ingest_utils import make_lab_event
from server.timeline.seed_data import get_db_url  # reuse

logger = logging.getLogger(__name__)


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
            logger.error(f"Embedding failed for event {e}: {exc}")
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
        logger.info("Inserted %d timeline events", len(rows))
    except Exception as exc:
        conn.rollback()
        logger.error("Error inserting rows: %s", exc)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest real-world lab JSON into ehr.patient_timeline"
    )
    parser.add_argument("--input-path", required=True, help="Path to lab JSON bundle")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print events instead of inserting",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    with open(args.input_path) as f:
        payload = json.load(f)

    patient_id = payload["patient_id"]
    labs = payload["labs"]
    events = [make_lab_event(patient_id, lab) for lab in labs]
    logger.info("Generated %d lab events for %s", len(events), patient_id)

    if args.dry_run:
        print(json.dumps([e.model_dump() for e in events], indent=2, default=str))
        return

    rows = embed_events(events)
    insert_rows(rows)


if __name__ == "__main__":
    main()
