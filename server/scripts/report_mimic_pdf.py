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

SQL_EMBED = """
  SELECT source,
         COUNT(*) AS total,
         COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
         COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
         ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
  FROM public.rag_corpus
  WHERE source IN ('mimic3_dx','mimic3_proc','mimic3_labitems','mimic4_dx','mimic4_proc','mimic4_labitems')
  GROUP BY source ORDER BY source
"""

SQL_ANN = r"""
  SELECT i.indexname, x.indisvalid, x.indisready,
         COALESCE( (SELECT option_value::int
                    FROM pg_options_to_table(c.reloptions)
                    WHERE option_name='lists'), 0) AS lists,
         pg_size_pretty(pg_relation_size(x.indexrelid)) AS size
  FROM pg_index x
  JOIN pg_class c ON c.oid=x.indexrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  JOIN pg_indexes i ON i.indexname=c.relname
  WHERE i.tablename='rag_corpus'
    AND i.indexname LIKE 'rag_corpus_embedding_ann_mimic%%'
  ORDER BY i.indexname
"""

def load_facts():
    conn = connect()
    try:
        m3 = q(conn, SQL_M3_COUNTS)
        m4 = q(conn, SQL_M4_COUNTS)
        qual = q(conn, SQL_QUALITY)
        emb = q(conn, SQL_EMBED)
        ann = q(conn, SQL_ANN)
        quality = (qual[0] if qual else {"iv_labs_within_stay": 0, "m3_adm_with_dx_rate": 0.0, "m4_adm_with_dx_rate": 0.0})
    finally:
        conn.close()
    return m3, m4, quality, emb, ann

def main(out="db_integrity_reports/07_mimic.pdf", use_ai=False):
    m3, m4, quality, emb, ann = load_facts()

    all_nonzero = all(int(r["n"]) > 0 for r in (m3 + m4))
    verdict_struct = "pass" if all_nonzero else "warn"

    def build_flow(story, content_width):
        story.append(P("MIMIC-III/IV structured load status", BODY))
        story.append(P(f"Verdict (structural): {verdict_struct.upper()}", BODY))

        story.append(P("Embedding coverage (RAG corpus)", H2))
        story.append(TableFromRows(emb, columns=["source","total","done","pending","pct"]))

        story.append(P("ANN (ivfflat) indexes", H2))
        story.append(TableFromRows(ann, columns=["indexname","indisvalid","indisready","lists","size"]))

        story.append(P("MIMIC-III — core counts", H2))
        story.append(TableFromRows(m3, columns=["what","n"]))

        story.append(P("MIMIC-IV — core counts", H2))
        story.append(TableFromRows(m4, columns=["what","n"]))

        story.append(P("Quality checks", H2))
        qc_rows = [
            {"metric": "iv_labs_within_stay", "value": int(quality.get("iv_labs_within_stay") or 0)},
            {"metric": "m3_adm_with_dx_rate", "value": round(float(quality.get("m3_adm_with_dx_rate") or 0.0), 4)},
            {"metric": "m4_adm_with_dx_rate", "value": round(float(quality.get("m4_adm_with_dx_rate") or 0.0), 4)},
        ]
        story.append(TableFromRows(qc_rows, columns=["metric","value"]))

    ai_obj = None
    if use_ai:
        ai_obj = ai_analyze(
            system=("You are auditing structured MIMIC-III/IV loads and their RAG readiness. "
                    "Return only JSON: {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
                    "Consider: missing core tables, low embedding coverage, invalid/absent ANN."),
            user={"m3_counts": m3, "m4_counts": m4, "quality": quality, "embed": emb, "ann": ann}
        )

    title = "07 • MIMIC (III/IV) — RAG Integrity"
    build_doc(out, title, subtitle=None, build_flow=build_flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/07_mimic.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI", "0").lower() in ("1", "true", "yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
