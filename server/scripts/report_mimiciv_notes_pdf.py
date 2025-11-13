#!/usr/bin/env python3
# server/scripts/report_mimiciv_notes_pdf.py

import os
import sys
import re
from typing import Optional, Dict, Set, Tuple, List

from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

# Candidate column names (auto-detects actual names in your table)
CAND_TEXT = ["text","note_text","notes","note","report","result","impression","findings"]
CAND_SOURCE = ["source_file","source","domain","note_type","section","file"]
CAND_CATEGORY = ["category","note_type","domain","section"]
CAND_CHARTTIME = ["charttime","note_time","chart_time","chartdate","chart_date"]

# --- RAG integrity SQL (mimic4_note coverage + ANN indexes) ---
SQL_RAG_M4N_COVERAGE = """
  SELECT
    COUNT(*) FILTER (WHERE source='mimic4_note') AS total,
    COUNT(*) FILTER (WHERE source='mimic4_note' AND embedding IS NOT NULL) AS embedded,
    COUNT(*) FILTER (WHERE source='mimic4_note' AND embedding IS NULL)     AS pending,
    ROUND(100.0*COUNT(*) FILTER (WHERE source='mimic4_note' AND embedding IS NOT NULL)
          / NULLIF(COUNT(*) FILTER (WHERE source='mimic4_note'),0), 2)     AS pct
  FROM rag_corpus;
"""

SQL_RAG_INDEXES = """
  SELECT i.indexname, x.indisvalid, x.indisready,
         pg_size_pretty(pg_relation_size(x.indexrelid)) AS size
  FROM pg_index x
  JOIN pg_class c ON c.oid = x.indexrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_indexes i ON i.indexname = c.relname
  WHERE i.tablename='rag_corpus'
    AND (i.indexname LIKE 'rag_corpus_embedding_ivfflat%' OR
         i.indexname LIKE 'rag_corpus_embedding_hnsw%')
  ORDER BY i.indexname;
"""

# ------------------------
# Helpers
# ------------------------
def get_cols(schema="text", table="mimiciv_notes") -> Set[str]:
    conn = connect()
    try:
        rows = q(conn, """
            SELECT lower(column_name) AS c
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
        """, (schema, table))
        return {r["c"] for r in rows}
    finally:
        conn.close()

def pick(cols: Set[str], candidates) -> Optional[str]:
    for c in candidates:
        if c in cols:
            return c
    return None

def ident_ok(name: str) -> bool:
    return bool(re.match(r"^[a-z_][a-z0-9_]*$", name or ""))

# ------------------------
# Data fetch
# ------------------------
def load(text_col: str,
         chart_col: Optional[str],
         source_col: Optional[str],
         cat_col: Optional[str]):
    """
    Returns:
      counts, breakdown, joinab, window, cats, map_counts, mapped_any,
      rag_cov, rag_idx
    """
    conn = connect()
    try:
        # Core counts (robust, no exotic cols)
        counts = q(conn, """
          SELECT 'rows' AS what, COUNT(*)::bigint AS n FROM text.mimiciv_notes
          UNION ALL
          SELECT 'subjects', COUNT(DISTINCT subject_id) FROM text.mimiciv_notes
          UNION ALL
          SELECT 'hadm_nonnull', COUNT(*) FROM text.mimiciv_notes WHERE hadm_id IS NOT NULL
          UNION ALL
          SELECT 'hadm_null', COUNT(*) FROM text.mimiciv_notes WHERE hadm_id IS NULL;
        """)

        # Breakdown by source/category when available
        breakdown = []
        if source_col and ident_ok(source_col):
            breakdown = q(conn, f"""
              SELECT COALESCE({source_col}, '(unknown)') AS source,
                     COUNT(*)::bigint AS n,
                     SUM((hadm_id IS NULL)::int)::bigint AS hadm_null,
                     ROUND(AVG(length({text_col}))::numeric,1) AS avg_len
              FROM text.mimiciv_notes
              GROUP BY 1
              ORDER BY n DESC, source
              LIMIT 25;
            """)
        elif cat_col and ident_ok(cat_col):
            breakdown = q(conn, f"""
              SELECT COALESCE({cat_col}, '(unknown)') AS source,
                     COUNT(*)::bigint AS n,
                     SUM((hadm_id IS NULL)::int)::bigint AS hadm_null,
                     ROUND(AVG(length({text_col}))::numeric,1) AS avg_len
              FROM text.mimiciv_notes
              GROUP BY 1
              ORDER BY n DESC, source
              LIMIT 25;
            """)

        # Joinability to admissions by existing hadm_id
        joinab = q(conn, """
          SELECT
            SUM((n.hadm_id IS NOT NULL AND a.hadm_id IS NULL)::int)::bigint AS hadm_not_in_admissions,
            SUM((n.hadm_id IS NOT NULL AND a.hadm_id IS NOT NULL)::int)::bigint AS hadm_in_admissions
          FROM text.mimiciv_notes n
          LEFT JOIN ehr_mimic4.admissions a USING (hadm_id);
        """)[0]

        # Notes inside admission window (only if we have a usable chart time & hadm_id)
        window = {"notes_within_stay_window": None}
        if chart_col and ident_ok(chart_col):
            window = q(conn, f"""
              SELECT COUNT(*)::bigint AS notes_within_stay_window
              FROM text.mimiciv_notes n
              JOIN ehr_mimic4.admissions a USING (hadm_id)
              WHERE n.{chart_col} BETWEEN a.admittime AND a.dischtime;
            """)[0]

        # Top categories if present
        cats = []
        if cat_col and ident_ok(cat_col):
            cats = q(conn, f"""
              SELECT {cat_col} AS category, COUNT(*)::bigint AS n
              FROM text.mimiciv_notes
              GROUP BY 1
              ORDER BY n DESC NULLS LAST
              LIMIT 10;
            """)

        # Mapping coverage from helper map table
        map_counts = q(conn, """
          SELECT method, COUNT(*)::bigint AS mapped
          FROM text.mimiciv_notes_hadm_map
          GROUP BY 1
          ORDER BY 1;
        """)
        mapped_any_row = q(conn, """
          SELECT COUNT(DISTINCT note_id)::bigint AS mapped_any
          FROM text.mimiciv_notes_hadm_map;
        """)
        mapped_any = int(mapped_any_row[0]["mapped_any"]) if mapped_any_row else 0

        # RAG integrity (mimic4_note coverage + ANN indexes)
        rag_cov = q(conn, SQL_RAG_M4N_COVERAGE)[0]
        rag_idx = q(conn, SQL_RAG_INDEXES)

        return counts, breakdown, joinab, window, cats, map_counts, mapped_any, rag_cov, rag_idx
    finally:
        conn.close()

# ------------------------
# Main
# ------------------------
def main(out="db_integrity_reports/08_mimiciv_notes.pdf", use_ai=False):
    cols = get_cols()
    text_col = pick(cols, CAND_TEXT)
    if not text_col:
        print("❌ Could not find a text/content column (tried: %s)" % ", ".join(CAND_TEXT))
        sys.exit(2)
    chart_col = pick(cols, CAND_CHARTTIME)
    source_col = pick(cols, CAND_SOURCE)
    cat_col = pick(cols, CAND_CATEGORY)

    (counts, breakdown, joinab, window, cats,
     map_counts, mapped_any, rag_cov, rag_idx) = load(
        text_col, chart_col, source_col, cat_col
    )

    summary = {r["what"]: int(r["n"]) for r in counts}
    total = summary.get("rows", 0)
    hadm_null = summary.get("hadm_null", 0)
    hadm_nonnull = summary.get("hadm_nonnull", 0)
    null_rate = (hadm_null / total) if total else 0.0
    hadm_in = int(joinab.get("hadm_in_admissions") or 0)
    hadm_not_in = int(joinab.get("hadm_not_in_admissions") or 0)
    hadm_with_vals = hadm_in + hadm_not_in
    bad_rate = (hadm_not_in / hadm_with_vals) if hadm_with_vals else 0.0

    # Verdict rubric (same as before)
    if total == 0:
        verdict = "fail"
    elif bad_rate > 0.10:
        verdict = "warn"
    elif null_rate > 0.30 and mapped_any < (0.05 * total):
        verdict = "warn"
    else:
        verdict = "pass"

    def flow(story, content_width):
        # Detected columns line
        cols_line = f"Detected → text: <b>{text_col}</b>"
        cols_line += f", chart time: <b>{chart_col}</b>" if chart_col else ", chart time: <i>none</i>"
        if source_col:
            cols_line += f", source: <b>{source_col}</b>"
        if cat_col:
            cols_line += f", category: <b>{cat_col}</b>"
        story.append(P(cols_line, BODY))
        story.append(Spacer(1, 6))

        # Verdict
        story.append(P(f"Verdict (structural): {verdict.upper()}", BODY))
        story.append(Spacer(1, 8))

        # Core counts
        story.append(P("Core counts", H2))
        story.append(TableFromRows(
            [{"what": k, "n": v} for k, v in summary.items()],
            ["what","n"]
        ))
        story.append(Spacer(1, 8))

        # By source/category (top 25)
        if breakdown:
            story.append(P("By source/category (top 25)", H2))
            story.append(TableFromRows(breakdown, ["source","n","hadm_null","avg_len"]))
            story.append(Spacer(1, 8))

        # Mapping coverage
        story.append(P("Mapping coverage (notes_hadm_map)", H2))
        story.append(TableFromRows(map_counts or [], ["method","mapped"]))
        story.append(Spacer(1, 4))
        story.append(TableFromRows(
            [{"metric":"mapped_any_notes","value": mapped_any},
             {"metric":"null_rate","value": round(null_rate, 4)},
             {"metric":"bad_hadm_rate","value": round(bad_rate, 4)}],
            ["metric","value"]
        ))
        story.append(Spacer(1, 8))

        # Joinability & window sanity
        story.append(P("Joinability & window sanity", H2))
        jr = [
            {"metric":"hadm_in_admissions", "value": hadm_in},
            {"metric":"hadm_not_in_admissions", "value": hadm_not_in},
        ]
        if window.get("notes_within_stay_window") is not None:
            jr.append({"metric":"notes_within_stay_window", "value": int(window["notes_within_stay_window"])})
        story.append(TableFromRows(jr, ["metric","value"]))
        story.append(Spacer(1, 8))

        # Top categories
        if cats:
            story.append(P("Top categories", H2))
            story.append(TableFromRows(cats, ["category","n"]))
            story.append(Spacer(1, 8))

        # --- NEW: RAG integrity for mimic4_note ---
        story.append(P("RAG integrity — mimic4_note", H2))
        story.append(TableFromRows(
            [{"metric":"total",   "value": int(rag_cov.get("total") or 0)},
             {"metric":"embedded","value": int(rag_cov.get("embedded") or 0)},
             {"metric":"pending", "value": int(rag_cov.get("pending") or 0)},
             {"metric":"pct",     "value": float(rag_cov.get("pct") or 0.0)}],
            ["metric","value"]
        ))
        story.append(Spacer(1, 6))
        story.append(P("ANN indexes (global rag_corpus)", BODY))
        story.append(TableFromRows(rag_idx, ["indexname","indisvalid","indisready","size"]))
        story.append(Spacer(1, 8))

    ai_obj = None
    if use_ai:
        ai_obj = ai_analyze(
            system=("You are auditing MIMIC-IV-Note integrity. "
                    "Only WARN if (bad_hadm_rate > 0.10) or (null_rate > 0.30 and mapped_any < 5% of rows). "
                    "Otherwise PASS. Respond only with JSON {verdict,rationale} (<=3 concise sentences)."),
            user={
                "counts": summary,
                "columns_detected": {
                    "text": text_col, "chart": chart_col,
                    "source": source_col, "category": cat_col
                },
                "null_rate": null_rate,
                "joinability": {"hadm_in": hadm_in, "hadm_not_in": hadm_not_in, "bad_rate": bad_rate},
                "mapping": {"mapped_any": mapped_any, "by_method": map_counts},
                "window": window,
                "rag_m4n": rag_cov,
                "rag_indexes": rag_idx[:5],
            }
        )

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "MIMIC-IV Notes — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/08_mimiciv_notes.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
