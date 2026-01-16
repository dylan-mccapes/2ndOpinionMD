# server/eoh/recompute_state.py

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import asyncpg

from .features import extract_features_for_patient
from .modules.m13_flare_risk import (
    compute_flare_risk,
    MODULE_NAME as M13_NAME,
    MODULE_VERSION as M13_VERSION,
)
from .modules.m17_diagnostic_landscape import (
    compute_diagnostic_landscape,
    MODULE_NAME as M17_NAME,
    MODULE_VERSION as M17_VERSION,
)


async def recompute_for_patient(conn: asyncpg.Connection, patient_id: str) -> None:
    features = await extract_features_for_patient(conn, patient_id)

    # M13 – flare risk
    flare = compute_flare_risk(features)

    # M17 – diagnostic landscape
    diag = compute_diagnostic_landscape(features)

    # Merge into one state dict (you can add stability_band, flare_tendency here too)
    state: Dict[str, Any] = {}
    state.update(flare)
    state.update(diag)

    # Upsert into eoh.patient_state
    await conn.execute(
        """
        INSERT INTO eoh.patient_state AS s (
            patient_id,
            updated_at,
            ra_flare_30d_prob,
            ra_flare_90d_prob,
            p_ra,
            p_sle,
            p_psa,
            p_sjogren,
            p_mctd,
            p_vasculitis,
            p_other,
            raw
        )
        VALUES (
            $1,
            now(),
            $2,
            $3,
            $4,
            $5,
            $6,
            $7,
            $8,
            $9,
            $10,
            $11
        )
        ON CONFLICT (patient_id) DO UPDATE
        SET
            updated_at        = EXCLUDED.updated_at,
            ra_flare_30d_prob = EXCLUDED.ra_flare_30d_prob,
            ra_flare_90d_prob = EXCLUDED.ra_flare_90d_prob,
            p_ra              = EXCLUDED.p_ra,
            p_sle             = EXCLUDED.p_sle,
            p_psa             = EXCLUDED.p_psa,
            p_sjogren         = EXCLUDED.p_sjogren,
            p_mctd            = EXCLUDED.p_mctd,
            p_vasculitis      = EXCLUDED.p_vasculitis,
            p_other           = EXCLUDED.p_other,
            raw               = EXCLUDED.raw;
        """,
        patient_id,
        flare.get("ra_flare_30d_prob"),
        flare.get("ra_flare_90d_prob"),
        diag.get("p_ra"),
        diag.get("p_sle"),
        diag.get("p_psa"),
        diag.get("p_sjogren"),
        diag.get("p_mctd"),
        diag.get("p_vasculitis"),
        diag.get("p_other"),
        state,
    )

    # Optionally log module_run entries for auditability
    await conn.execute(
        """
        INSERT INTO eoh.module_run (
            patient_id, module_name, module_version,
            status, output_json
        )
        VALUES ($1, $2, $3, $4, $5)
        """,
        patient_id,
        M13_NAME,
        M13_VERSION,
        "success",
        flare,
    )

    await conn.execute(
        """
        INSERT INTO eoh.module_run (
            patient_id, module_name, module_version,
            status, output_json
        )
        VALUES ($1, $2, $3, $4, $5)
        """,
        patient_id,
        M17_NAME,
        M17_VERSION,
        "success",
        diag,
    )


async def main() -> None:
    dsn = os.getenv("DATABASE_URL") or os.getenv("EOH_DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set DATABASE_URL or EOH_DATABASE_URL for eoh.recompute_state")

    conn = await asyncpg.connect(dsn=dsn)
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT patient_id FROM ehr.patient_timeline ORDER BY patient_id"
        )
        for r in rows:
            pid = r["patient_id"]
            print(f"[EoH] recomputing state for {pid}")
            await recompute_for_patient(conn, pid)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())