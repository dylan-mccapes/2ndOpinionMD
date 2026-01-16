# server/timeline/seed_landscape_events_from_state.py

from __future__ import annotations

import os
from typing import Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, Json


def get_sync_db_url() -> str:
    url = (
        os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql:///2ndopinionmd"
    )
    return url.replace("+asyncpg", "").replace("+psycopg", "")


# Focus on the SLE patient that misbehaved; you can add others if you like.
TARGET_PATIENT_IDS = [
    "DEMO_RA_001",
    "DEMO_RA_002",
    "DEMO_RA_003",
    "DEMO_SLE_001",
    "DEMO_SLE_002",
    "DEMO_PSA_001",
    "DEMO_SJOGREN_001",
    "DEMO_MCTD_001",
    "DEMO_VASC_001",
    "DEMO_FIBRO_001",
]


def main() -> None:
    dsn = get_sync_db_url()
    conn = psycopg2.connect(dsn)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1) Pull diagnostic_landscape JSON from eoh.patient_state
            cur.execute(
                """
                SELECT patient_id,
                       raw -> 'diagnostic_landscape' AS dl
                FROM eoh.patient_state
                WHERE patient_id = ANY(%s)
                """,
                (TARGET_PATIENT_IDS,),
            )
            rows = cur.fetchall()

            if not rows:
                print("No patient_state rows found for target patients.")
                conn.rollback()
                return

            for row in rows:
                pid = row["patient_id"]
                dl: Dict[str, Any] = row["dl"] or {}

                if not dl:
                    print(f"[SKIP] {pid}: no diagnostic_landscape in patient_state.raw")
                    continue

                # Optional: "harden" SLE here if you want to be explicit
                # (feel free to tweak)
                if pid.startswith("DEMO_SLE_"):
                    # Make sure SLE dominates; keep others but small
                    dl.setdefault("sle_like", 0.8)
                    dl.setdefault("mctd_like", 0.15)
                    dl.setdefault("other", 0.05)

                # 2) Find a reasonable timestamp anchor in the timeline
                cur.execute(
                    """
                    SELECT ts
                    FROM ehr.patient_timeline
                    WHERE patient_id = %s
                    ORDER BY ts DESC
                    LIMIT 1
                    """,
                    (pid,),
                )
                ts_row = cur.fetchone()
                if ts_row and ts_row["ts"]:
                    ts = ts_row["ts"]
                else:
                    # Fallback: now() if somehow no timeline rows exist
                    cur.execute("SELECT NOW() AS ts")
                    ts = cur.fetchone()["ts"]

                # 3) Insert a baseline diagnostic_landscape event.
                #    If you want idempotency, you can CHECK for an existing event_type first.
                cur.execute(
                    """
                    INSERT INTO ehr.patient_timeline (
                        patient_id,
                        ts,
                        event_type,
                        source,
                        structured,
                        text,
                        meta
                    )
                    VALUES (
                        %s,
                        %s,
                        'eoh_baseline_landscape',
                        'seed_diagnostic_landscapes',
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        pid,
                        ts,
                        Json({"diagnostic_landscape": dl}),
                        "Seeded baseline diagnostic landscape for EoH/M50.",
                        Json({"kind": "eoh_baseline_landscape"}),
                    ),
                )
                print(f"[OK] Inserted baseline landscape event for {pid} at {ts}")

        conn.commit()
        print("Committed baseline landscape events.")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding baseline landscape events: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
