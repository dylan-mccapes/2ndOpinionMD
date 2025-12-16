# server/timeline/ingest_mimic4_patient.py
from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

import asyncpg

MIMIC4_PATIENT_ID_PREFIX = "MIMIC4_"

INGEST_SQL = """
WITH p AS (
  SELECT $1::bigint AS subject_id
),

dx AS (
  SELECT
    'diagnosis'::text                  AS event_type,
    'MIMIC4'::text                     AS source,
    -- Use admission time as the event timestamp (cast to timestamptz)
    COALESCE(a.admittime, a.dischtime)::timestamptz AS ts,
    jsonb_build_object(
      'subject_id',  d.subject_id,
      'hadm_id',     d.hadm_id,
      'seq_num',     d.seq_num,
      'icd_code',    d.icd_code,
      'icd_version', d.icd_version,
      'long_title',  d.long_title,
      'icd10_cat',   d.icd10_cat
    )                                   AS structured,
    d.long_title::text                  AS text
  FROM ehr_mimic4.v_diagnoses_icd10 d
  JOIN p ON d.subject_id = p.subject_id
  LEFT JOIN ehr_mimic4.admissions a
    ON d.hadm_id = a.hadm_id
),

px AS (
  SELECT
    'procedure'::text                  AS event_type,
    'MIMIC4'::text                     AS source,
    -- procedures_icd has no charttime; anchor to admission time
    COALESCE(a.admittime, a.dischtime)::timestamptz AS ts,
    jsonb_build_object(
      'subject_id',  pr.subject_id,
      'hadm_id',     pr.hadm_id,
      'seq_num',     pr.seq_num,
      'icd_code',    pr.icd_code,
      'icd_version', pr.icd_version,
      'long_title',  dp.long_title
    )                                  AS structured,
    dp.long_title::text                AS text
  FROM ehr_mimic4.procedures_icd pr
  JOIN p ON pr.subject_id = p.subject_id
  LEFT JOIN ehr_mimic4.d_icd_procedures dp
    ON pr.icd_code = dp.icd_code
   AND pr.icd_version = dp.icd_version
  LEFT JOIN ehr_mimic4.admissions a
    ON pr.hadm_id = a.hadm_id
),

icu AS (
  SELECT
    'icu_stay'::text                   AS event_type,
    'MIMIC4'::text                     AS source,
    ic.intime                          AS ts,
    jsonb_build_object(
      'subject_id',     ic.subject_id,
      'hadm_id',        ic.hadm_id,
      'stay_id',        ic.stay_id,
      'first_careunit', ic.first_careunit,
      'last_careunit',  ic.last_careunit,
      'los',            ic.los
    )                                  AS structured,
    format(
      'ICU stay in %s, LOS=%%.1f days',
      ic.first_careunit,
      ic.los
    )::text                            AS text
  FROM ehr_mimic4.icustays ic
  JOIN p ON ic.subject_id = p.subject_id
),

notes AS (
  SELECT
    'note'::text                       AS event_type,
    'MIMIC4'::text                     AS source,
    n.charttime                        AS ts,
    jsonb_build_object(
      'subject_id',  n.subject_id,
      'hadm_id',     n.hadm_id,
      'note_id',     n.note_id,
      'source_view', 'mimiciv_notes_resolved'
    )                                  AS structured,
    format('NOTE (note_id=%s)', n.note_id)::text AS text
  FROM text.mimiciv_notes_resolved n
  JOIN p ON n.subject_id = p.subject_id
),

labs AS (
  SELECT
    'lab'::text                        AS event_type,
    'MIMIC4'::text                     AS source,
    l.charttime                        AS ts,
    jsonb_build_object(
      'subject_id',  l.subject_id,
      'hadm_id',     l.hadm_id,
      'specimen_id', l.specimen_id,
      'itemid',      l.itemid,
      'label',       di.label,
      'value',       l.valuenum,
      'valueuom',    l.valueuom,
      'flag',        l.flag
    )                                  AS structured,
    format(
      '%s %s %s (flag=%s)',
      coalesce(di.label, 'LAB'),
      coalesce(l.valuenum::text, l.value::text),
      coalesce(l.valueuom, ''),
      coalesce(l.flag, '')
    )::text                            AS text
  FROM ehr_mimic4.labevents l
  JOIN p ON l.subject_id = p.subject_id
  LEFT JOIN ehr_mimic4.d_labitems di
    ON l.itemid = di.itemid
)

SELECT
  $2::text AS patient_id,
  ts,
  event_type,
  source,
  structured,
  text
FROM (
  SELECT ts, event_type, source, structured, text FROM dx
  UNION ALL
  SELECT ts, event_type, source, structured, text FROM px
  UNION ALL
  SELECT ts, event_type, source, structured, text FROM icu
  UNION ALL
  SELECT ts, event_type, source, structured, text FROM notes
  UNION ALL
  SELECT ts, event_type, source, structured, text FROM labs
) AS all_events
WHERE ts IS NOT NULL
ORDER BY ts;
"""

INSERT_SQL = """
INSERT INTO ehr.patient_timeline (patient_id, ts, event_type, source, structured, text)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT DO NOTHING;
"""

async def ingest_mimic4_patient(
    dsn: str,
    subject_id: int,
    patient_id: str | None = None,
) -> int:
    if patient_id is None:
        patient_id = f"{MIMIC4_PATIENT_ID_PREFIX}{subject_id}"

    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as conn:
        rows = await conn.fetch(INGEST_SQL, subject_id, patient_id)
        if not rows:
            print(f"No events found for subject_id={subject_id}")
            await pool.close()
            return 0

        print(f"Fetched {len(rows)} events for subject_id={subject_id}, inserting into ehr.patient_timeline...")

        async with conn.transaction():
            for r in rows:
                await conn.execute(
                    INSERT_SQL,
                    patient_id,
                    r["ts"],
                    r["event_type"],
                    r["source"],
                    r["structured"],
                    r["text"],
                )

    await pool.close()
    print(f"Done. Inserted {len(rows)} events (no cap) for patient_id={patient_id}.")
    return len(rows)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-id", type=int, required=True)
    parser.add_argument("--patient-id", type=str, default=None)
    parser.add_argument(
        "--dsn",
        type=str,
        default=os.getenv("DATABASE_URL", "postgresql://2ndopinionmd@localhost/2ndopinionmd"),
    )
    args = parser.parse_args()
    asyncio.run(ingest_mimic4_patient(args.dsn, args.subject_id, args.patient_id))

if __name__ == "__main__":
    main()