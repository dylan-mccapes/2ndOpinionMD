#!/usr/bin/env python3
import os, sys
from datetime import datetime
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, BODY, ai_analyze
)
from reportlab.platypus import Spacer

SQL_M3_COUNTS = """
SELECT 'm3_patients'   AS what, COUNT(*)::bigint AS n FROM ehr_mimic3.patients
UNION ALL SELECT 'm3_admissions', COUNT(*)       FROM ehr_mimic3.admissions
UNION ALL SELECT 'm3_labs',       COUNT(*)       FROM ehr_mimic3.labevents
UNION ALL SELECT 'm3_dx',         COUNT(*)       FROM ehr_mimic3.diagnoses_icd;
"""

SQL_M4_COUNTS = """
SELECT 'm4_patients'   AS what, COUNT(*)::bigint AS n FROM ehr_mimic4.patients
UNION ALL SELECT 'm4_admissions', COUNT(*)       FROM ehr_mimic4.admissions
UNION ALL SELECT 'm4_labs',       COUNT(*)       FROM ehr_mimic4.labevents
UNION ALL SELECT 'm4_dx',         COUNT(*)       FROM ehr_mimic4.diagnoses_icd
UNION ALL SELECT 'm4_icustays',   COUNT(*)       FROM ehr_mimic4.icustays;
"""

SQL_QUALITY = """
WITH
m3_adm AS (SELECT COUNT(*)::bigint n FROM ehr_mimic3.admissions),
m3_adm_w_dx AS (SELECT COUNT(DISTINCT hadm_id)::bigint n FROM ehr_mimic3.diagnoses_icd),
m4_adm AS (SELECT COUNT(*)::bigint n FROM ehr_mimic4.admissions),
m4_adm_w_dx AS (SELECT COUNT(DISTINCT hadm_id)::bigint n FROM ehr_mimic4.diagnoses_icd),
iv_join AS (
  SELECT COUNT(*)::bigint n
  FROM ehr_mimic4.admissions a
  JOIN ehr_mimic4.labevents l USING (hadm_id)
  WHERE l.charttime BETWEEN a.admittime AND a.dischtime
)
SELECT
  (SELECT n FROM iv_join)                          AS iv_labs_within_stay,
  (SELECT n FROM m3_adm_w_dx)::float / NULLIF((SELECT n FROM m3_adm),0) AS m3_adm_with_dx_rate,
  (SELECT n FROM m4_adm_w_dx)::float / NULLIF((SELECT n FROM m4_adm),0) AS m4_adm_with_dx_rate;
"""

def load_facts():
    conn = connect()
    try:
        m3 = q(conn, SQL_M3_COUNTS)
        m4 = q(conn, SQL_M4_COUNTS)
        qual = q(conn, SQL_QUALITY)
        quality = (qual[0] if qual else {"iv_labs_within_stay": 0, "m3_adm_with_dx_rate": 0.0, "m4_adm_with_dx_rate": 0.0})
    finally:
        conn.close()
    return m3, m4, quality

def main(out="db_integrity_reports/07_mimic.pdf", use_ai=False):
    m3, m4, quality = load_facts()

    # Verdict (structural): PASS only if all core tables are non-zero
    all_nonzero = all(int(r["n"]) > 0 for r in (m3 + m4))
    verdict_struct = "pass" if all_nonzero else "warn"

    def build_flow(story, content_width):
        source_line = (
            "Source: ehr_mimic3.{patients, admissions, d_labitems, labevents, "
            "d_icd_diagnoses, diagnoses_icd, icustays} + "
            "ehr_mimic4.{patients, admissions, d_labitems, labevents, "
            "d_icd_diagnoses, diagnoses_icd, icustays}"
        )
        story.append(P(source_line, BODY))
        story.append(P(f"Verdict (structural): {verdict_struct.upper()}", BODY))
        story.append(Spacer(1, 6))

        story.append(P("MIMIC-III — core counts", H2))
        story.append(TableFromRows(m3, columns=["what", "n"]))
        story.append(Spacer(1, 6))

        story.append(P("MIMIC-IV — core counts", H2))
        story.append(TableFromRows(m4, columns=["what", "n"]))
        story.append(Spacer(1, 6))

        story.append(P("Quality checks", H2))
        qc_rows = [
            {"metric": "iv_labs_within_stay", "value": int(quality.get("iv_labs_within_stay") or 0)},
            {"metric": "m3_adm_with_dx_rate", "value": round(float(quality.get("m3_adm_with_dx_rate") or 0.0), 4)},
            {"metric": "m4_adm_with_dx_rate", "value": round(float(quality.get("m4_adm_with_dx_rate") or 0.0), 4)},
        ]
        story.append(TableFromRows(qc_rows, columns=["metric", "value"]))

    # Optional AI PASS/WARN/FAIL box (same house style as 06)
    ai_obj = None
    if use_ai:
        ai_obj = ai_analyze(
            system=(
                "You are auditing MIMIC-IV note joins. "
                "Only WARN if (hadm_null / rows) > 0.25 or mapped_any is very low. "
                "Otherwise PASS with a brief note. Respond as JSON verdict+rationale."
            ),
            user={
                "rows": rows_total, "hadm_null": hadm_null, "mapped_any": mapped_any,
                "by_method": map_counts, "m3_counts": m3, "m4_counts": m4, "quality": quality
            }
        )

    title = "MIMIC (III/IV) — INTEGRITY REPORT"
    subtitle = None  # build_doc prints the Generated: timestamp
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, title, subtitle, build_flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/07_mimic.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI", "0").lower() in ("1", "true", "yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
