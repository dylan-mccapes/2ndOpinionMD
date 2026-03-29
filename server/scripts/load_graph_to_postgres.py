"""Load pre-built PatientTimelineVision graph + PatientTimelineChart embeddings
into Postgres tables (ehr.patient_graph_vision, ehr.patient_graph_chart,
ehr.patient_graph_status).

Usage:
    python scripts/load_graph_to_postgres.py \\
        --vision "artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843_enriched.json" \\
        --chart  "artifacts/timeline_full_20260327_1717/patient_chart_index_v2.jsonl" \\
        --patient-id NORMAN_ROBERTS
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent  # 2ndOpinionMD-MVP/

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)

import asyncpg
from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.eoh.patient_timeline_chart import PatientTimelineChart
from server.utils.parse_date import parse_clinical_date

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger("load_graph_pg")


async def ensure_tables(conn) -> None:
    """Create tables if they don't exist (idempotent)."""
    sql_path = parent_of_server / "database" / "schemas" / "ehr_patient_graph.sql"
    if sql_path.exists():
        sql = sql_path.read_text()
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                try:
                    await conn.execute(statement)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning("SQL statement warning: %s", e)
    else:
        logger.warning("Schema file not found at %s — tables must already exist", sql_path)


async def load_vision_to_pg(conn, vision: PatientTimelineVision) -> int:
    """Upsert the full vision graph as JSONB. Returns event count."""
    await conn.execute(
        """
        INSERT INTO ehr.patient_graph_vision (patient_id, graph_json, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (patient_id)
        DO UPDATE SET graph_json = EXCLUDED.graph_json,
                      updated_at = NOW()
        """,
        vision.patient_id,
        json.dumps(vision.to_dict(), ensure_ascii=False),
    )
    n = len(vision.events)
    logger.info("Vision stored: %d events, %d edges", n, vision.count_edges())
    return n


async def load_chart_to_pg(conn, patient_id: str, chart: PatientTimelineChart) -> int:
    """Replace chart embeddings for patient. Returns rows written."""
    await conn.execute(
        "DELETE FROM ehr.patient_graph_chart WHERE patient_id = $1",
        patient_id,
    )
    rows = [
        (
            patient_id,
            p.event_id,
            p.event_type,
            p.timestamp,
            p.preview[:500],
            json.dumps(p.embedding),
        )
        for p in chart._points
    ]
    if rows:
        await conn.executemany(
            """
            INSERT INTO ehr.patient_graph_chart
                (patient_id, event_id, event_type, ts_text, preview, embedding)
            VALUES ($1, $2, $3, $4, $5, $6::vector)
            """,
            rows,
        )
    logger.info("Chart stored: %d embeddings for %s", len(rows), patient_id)
    return len(rows)


async def update_status(
    conn,
    patient_id: str,
    vision: PatientTimelineVision,
    chart_count: int,
) -> bool:
    """Upsert readiness metadata in patient_graph_status. Returns is_ready."""
    event_count = len(vision.events)
    edge_count = vision.count_edges()

    # Compute non-fallback timestamp coverage
    ts_real = 0
    for e in vision.events.values():
        ts = (e.timestamp or "").strip().lower()
        if ts and ts not in ("unknown", "n/a", ""):
            if parse_clinical_date(e.timestamp) is not None:
                ts_real += 1
    ts_coverage = ts_real / event_count if event_count else 0.0

    is_ready = event_count > 0 and chart_count > 0

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
        ts_coverage,
    )
    logger.info(
        "Status: ready=%s  events=%d  edges=%d  chart=%d  ts_coverage=%.1f%%",
        is_ready, event_count, edge_count, chart_count, ts_coverage * 100,
    )
    return is_ready


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load graph + chart into Postgres")
    parser.add_argument("--vision", required=True, help="Path to PatientTimelineVision JSON")
    parser.add_argument("--chart", required=True, help="Path to PatientTimelineChart JSONL index")
    parser.add_argument(
        "--patient-id", default=None,
        help="Override patient_id (default: read from vision JSON)",
    )
    args = parser.parse_args()

    def resolve(p: str) -> Path:
        path = Path(p)
        return path.resolve() if path.is_absolute() else (parent_of_server / p).resolve()

    vision_path = resolve(args.vision)
    chart_path = resolve(args.chart)

    logger.info("Loading vision from %s", vision_path)
    vision = PatientTimelineVision.load(str(vision_path))
    if not vision.events:
        logger.error("Vision has no events, aborting")
        sys.exit(1)

    patient_id = args.patient_id or vision.patient_id
    if args.patient_id:
        vision.patient_id = patient_id

    logger.info(
        "Patient: %s  Events: %d  Edges: %d",
        patient_id, len(vision.events), vision.count_edges(),
    )

    logger.info("Loading chart from %s", chart_path)
    chart = PatientTimelineChart()
    chart_count = chart.load_index(chart_path)
    logger.info("Chart points: %d", chart_count)

    dsn = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)
    if not dsn:
        dsn = "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

    logger.info("Connecting to Postgres...")
    conn = await asyncpg.connect(dsn)
    try:
        await ensure_tables(conn)
        t0 = time.perf_counter()
        await load_vision_to_pg(conn, vision)
        await load_chart_to_pg(conn, patient_id, chart)
        is_ready = await update_status(conn, patient_id, vision, chart_count)
        elapsed = time.perf_counter() - t0
        logger.info("Done in %.1fs. Graph ready for EoHD: %s", elapsed, is_ready)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
