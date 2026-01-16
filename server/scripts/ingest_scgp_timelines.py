# server/scripts/ingest_scgp_timelines.py

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import List

import asyncpg

from server.timeline.scgp_parser import ScgpEvent, parse_scgp_rtf


async def _insert_events(conn: asyncpg.Connection, events: List[ScgpEvent]) -> int:
    if not events:
        return 0

    rows = [
        (
            e.patient_id,
            e.ts,
            e.event_type,
            e.source,
            json.dumps(e.structured),
            e.text,
            json.dumps(e.meta),
        )
        for e in events
    ]

    await conn.executemany(
        """
        INSERT INTO ehr.patient_timeline
            (patient_id, ts, event_type, source, structured, text, meta)
        VALUES
            ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb)
        """,
        rows,
    )
    return len(rows)


async def main_async(args: argparse.Namespace) -> None:
    events = parse_scgp_rtf(args.path)

    if args.patient_prefix:
        # Optional override in case you want to namespace these by environment/run
        for e in events:
            e.patient_id = f"{args.patient_prefix}_{e.patient_id}"

    if args.dry_run:
        print(f"[DRY RUN] Parsed {len(events)} events")
        by_patient: dict[str, int] = {}
        for e in events:
            by_patient[e.patient_id] = by_patient.get(e.patient_id, 0) + 1
        for pid, n in sorted(by_patient.items()):
            print(f"  {pid}: {n} events")
        return

    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set and --database-url was not provided")

    conn = await asyncpg.connect(database_url)
    try:
        inserted = await _insert_events(conn, events)
    finally:
        await conn.close()

    print(f"Inserted {inserted} SCGP synthetic timeline events into ehr.patient_timeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest SCGP synthetic patient timelines into ehr.patient_timeline")
    parser.add_argument(
        "--path",
        required=True,
        help="Path to synthetic-patient-timelines.rtf",
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL DATABASE_URL; defaults to $DATABASE_URL",
    )
    parser.add_argument(
        "--patient-prefix",
        help="Optional prefix to prepend to patient_id (e.g. DEV, DEMO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report counts without writing to the database",
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
