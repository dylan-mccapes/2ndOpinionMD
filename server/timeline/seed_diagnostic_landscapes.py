# server/timeline/seed_diagnostic_landscapes.py
from __future__ import annotations
import asyncio
import json
import asyncpg
from datetime import datetime

DSN = "postgresql://localhost/2ndopinionmd"

LANDSCAPES = {
    "DEMO_RA_001":   {"ra_like": 0.8, "sle_like": 0.05, "psa_like": 0.05, "sjogren_like": 0.05, "other": 0.05},
    "DEMO_RA_002":   {"ra_like": 0.85, "sle_like": 0.05, "psa_like": 0.05, "other": 0.05},
    "DEMO_RA_003":   {"ra_like": 0.75, "psa_like": 0.1, "fibro_like": 0.05, "other": 0.1},
    "DEMO_SLE_001":  {"sle_like": 0.8, "ra_like": 0.05, "mctd_like": 0.1, "other": 0.05},
    "DEMO_SLE_002":  {"sle_like": 0.7, "mctd_like": 0.2, "ra_like": 0.05, "other": 0.05},
    "DEMO_PSA_001":  {"psa_like": 0.8, "ra_like": 0.1, "other": 0.1},
    "DEMO_SJOGREN_001": {"sjogren_like": 0.8, "sle_like": 0.1, "other": 0.1},
    "DEMO_MCTD_001": {"mctd_like": 0.7, "ra_like": 0.15, "sle_like": 0.1, "other": 0.05},
    "DEMO_VASC_001": {"vasculitis_like": 0.8, "sle_like": 0.1, "other": 0.1},
    "DEMO_FIBRO_001": {"fibro_like": 0.8, "ra_like": 0.05, "sle_like": 0.05, "other": 0.1},
}

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # Optional sanity check: does table exist?
        # await conn.execute("SELECT 1 FROM eoh.patient_state LIMIT 1;")

        for pid, landscape in LANDSCAPES.items():
            # Upsert row, assuming patient_id is UNIQUE or PRIMARY KEY
            result = await conn.execute(
                """
                INSERT INTO eoh.patient_state (patient_id, updated_at, raw)
                VALUES ($1, NOW(), jsonb_build_object('diagnostic_landscape', $2::jsonb))
                ON CONFLICT (patient_id)
                DO UPDATE SET
                    raw = jsonb_set(
                        COALESCE(eoh.patient_state.raw, '{}'::jsonb),
                        '{diagnostic_landscape}',
                        EXCLUDED.raw->'diagnostic_landscape',
                        true
                    ),
                    updated_at = NOW()
                """,
                pid,
                json.dumps(landscape),
            )
            print(f"{result} for {pid}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())