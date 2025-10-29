#!/usr/bin/env python3
# CDC Opioid — Audit & Integrity PDF
import os, json, math
from typing import Dict, Any, List, Tuple
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/20_cdc_opioid.pdf"
CRITICAL_TAGS = ["pdmp", "naloxone", "tapering", "nonopioid_preferred"]

# ----------------------------- Queries -----------------------------

def fetch_presence_and_counts(conn) -> Dict[str, Any]:
    row = q(conn, """
        SELECT
          (SELECT COUNT(*) FROM guidelines.cdc_docs)                 AS n_docs,
          (SELECT COUNT(*) FROM guidelines.cdc_sections)             AS n_sections,
          (SELECT COUNT(*) FROM guidelines.cdc_sections
             WHERE text_plain IS NULL OR length(text_plain)=0)       AS n_sections_empty,
          (SELECT COUNT(*) FROM guidelines.cdc_sections
             WHERE COALESCE(heading,'')='')                          AS n_sections_no_heading,
          (SELECT COUNT(*) FROM guidelines.cdc_sections
             WHERE COALESCE(rec_number,'')<>'')                      AS n_sections_with_rec
    """)[0]
    return {k:int(row.get(k,0) or 0) for k in row.keys()}

def fetch_docs_table(conn) -> List[Dict[str, Any]]:
    return q(conn, """
        SELECT slug, title, pub_date, url,
               (SELECT COUNT(*) FROM guidelines.cdc_sections s WHERE s.doc_id=d.doc_id) AS n_sections
        FROM guidelines.cdc_docs d
        ORDER BY n_sections DESC NULLS LAST, slug ASC
    """)

def fetch_rec_distribution(conn) -> List[Dict[str, Any]]:
    return q(conn, """
        SELECT rec_number, COUNT(*)::int AS n
        FROM guidelines.cdc_sections
        WHERE rec_number IS NOT NULL AND rec_number <> ''
        GROUP BY rec_number
        ORDER BY rec_number::text ASC
    """)

def fetch_tags_distribution(conn) -> List[Dict[str, Any]]:
    return q(conn, """
        SELECT tag, COUNT(*)::int AS n
        FROM (SELECT unnest(tags) AS tag FROM guidelines.cdc_sections) t
        GROUP BY tag
        ORDER BY n DESC, tag ASC
    """)

def fetch_xref_stats(conn) -> Dict[str, Any]:
    row_tot = q(conn, "SELECT COUNT(*)::int AS n FROM guidelines.section_code_map")[0]
    row_sec = q(conn, """
        SELECT COUNT(DISTINCT section_id)::int AS n_sections
        FROM guidelines.section_code_map
    """)[0]
    by_sys = q(conn, """
        SELECT system, COUNT(*)::int AS n
        FROM guidelines.section_code_map
        GROUP BY system
        ORDER BY n DESC, system ASC
    """)
    return {
        "mappings_total": int(row_tot["n"]),
        "sections_mapped": int(row_sec["n_sections"]),
        "by_system": by_sys,
    }

def fetch_rag_stats(conn) -> Dict[str, Any]:
    row = q(conn, """
        SELECT
          COUNT(*)::int AS total,
          COUNT(*) FILTER (WHERE embedding IS NULL)::int AS no_embed
        FROM public.rag_corpus
        WHERE source='cdc_opioid'
    """)[0]
    return {"rag_rows": int(row["total"]), "rag_no_embed": int(row["no_embed"])}

def has_index_like(conn, *, schemaname: str=None, tablename: str=None, name_like: str=None, def_like: str=None) -> bool:
    conds = []
    args: list = []
    if schemaname:
        conds.append("schemaname = %s"); args.append(schemaname)
    if tablename:
        conds.append("tablename = %s"); args.append(tablename)
    if name_like:
        conds.append("indexname ILIKE %s"); args.append(name_like)
    if def_like:
        conds.append("indexdef ILIKE %s"); args.append(def_like)

    where = " AND ".join(conds) if conds else "TRUE"
    sql = f"SELECT 1 FROM pg_indexes WHERE {where} LIMIT 1"
    return bool(q(conn, sql, tuple(args)))

def fetch_index_presence(conn) -> dict:
    return {
        "cdc_sections_ts_gin": has_index_like(
            conn, schemaname="guidelines", tablename="cdc_sections",
            def_like="%GIN%to_tsvector%text_plain%"
        ) or has_index_like(
            conn, schemaname="guidelines", tablename="cdc_sections",
            def_like="%GIN% text_plain %"
        ),
        "cdc_sections_tags_gin": has_index_like(
            conn, schemaname="guidelines", tablename="cdc_sections", def_like="%USING gin%tags%"
        ),
    }

def fetch_ann_details(conn):
    rows = q(conn, """
      SELECT
        i.indexrelid::regclass::text AS indexname,
        pg_get_indexdef(i.indexrelid)      AS indexdef,
        pg_get_expr(i.indpred, i.indrelid) AS predicate,
        COALESCE(
          (regexp_match(pg_get_indexdef(i.indexrelid), 'WITH\\s*\\(.*lists\\s*=\\s*([0-9]+).*?\\)'))[1]::int,
          NULL
        ) AS lists
      FROM pg_index i
      JOIN pg_class t ON t.oid = i.indrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
      WHERE n.nspname='public'
        AND t.relname='rag_corpus'
        AND pg_get_indexdef(i.indexrelid) ILIKE '%USING ivfflat%'
        AND (pg_get_expr(i.indpred, i.indrelid) ILIKE '%source = ''cdc_opioid''%'
             OR pg_get_expr(i.indpred, i.indrelid) ILIKE '%source=''cdc_opioid''%')
      LIMIT 1
    """)
    return rows[0] if rows else None

def fetch_embed_stats(conn):
    return q(conn, """
      SELECT
        COUNT(*)::int AS total,
        COUNT(*) FILTER (WHERE embedding IS NULL)::int AS no_embed,
        round( CASE WHEN COUNT(*)=0 THEN 0
                    ELSE 100.0 * (COUNT(*) FILTER (WHERE embedding IS NOT NULL))::numeric / COUNT(*)
              END, 2) AS pct
      FROM public.rag_corpus
      WHERE source='cdc_opioid'
    """)[0]

# ----------------------------- Verdict & AI -----------------------------

def verdict_from(present, rag, idx, tags, recs, ann_present: bool):
    if present["n_docs"] == 0:  return "fail", "No CDC documents were found."
    if present["n_sections"] == 0: return "fail", "No CDC sections were parsed."

    warnings = []
    if rag["rag_rows"] == 0:
        warnings.append("CDC corpus is not present in RAG.")
    if rag["rag_no_embed"] > 0:
        warnings.append("Some CDC RAG rows are missing embeddings.")
    if not ann_present:
        warnings.append("ANN index for CDC RAG is missing.")
    if not idx["cdc_sections_ts_gin"]:
        warnings.append("Text-search GIN index on CDC sections is missing.")

    have = {r["rec_number"] for r in (recs or []) if r.get("rec_number")}
    expected = {f"R{i}" for i in range(1,13)}
    missing_recs = sorted(list(expected - have))
    if missing_recs:
        warnings.append(f"Missing recommendation identifiers: {', '.join(missing_recs)}")

    tags_set = {t["tag"] for t in (tags or [])}
    critical = {"pdmp","naloxone","tapering","nonopioid_preferred"}
    if not critical.issubset(tags_set):
        warnings.append("Not all critical tags present.")

    return ("warn", "; ".join(warnings)) if warnings else ("pass", "CDC tables, RAG, ANN, and indexes look healthy.")

def ai_block(use_ai: bool, facts: Dict[str, Any]):
    if not use_ai:
        return None
    return ai_analyze(
        system=(
            "You are auditing a CDC Opioid Guidelines import in PostgreSQL. "
            "Return ONLY compact JSON like "
            "{\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\","
            "\"actions\":[\"...\",\"...\"]}. "
            "Rules: fail if no docs or no sections. Warn if RAG rows==0 or have missing embeddings, "
            "or if ANN/text indexes are missing, or if recommendation coverage misses R1..R12, "
            "or if critical tags (pdmp,naloxone,tapering,nonopioid_preferred) are absent."
        ),
        user=facts
    )

# ----------------------------- Loader & PDF -----------------------------

def load() -> Dict[str, Any]:
    conn = connect()
    try:
        present = fetch_presence_and_counts(conn)
        docs    = fetch_docs_table(conn)
        recs    = fetch_rec_distribution(conn)
        tags    = fetch_tags_distribution(conn)
        xref    = fetch_xref_stats(conn)
        rag     = fetch_rag_stats(conn)
        idx     = fetch_index_presence(conn)
        ann     = fetch_ann_details(conn)
        emb     = fetch_embed_stats(conn)

        return {
            "present": present,
            "docs": docs,
            "recs": recs,
            "tags": tags,
            "xref": xref,
            "rag": rag,
            "indexes": idx,
            "ann": ann,
            "embed": emb,
        }
    finally:
        conn.close()

def main(out=OUT, use_ai=False, brief=False):
    a = load()
    ann_present = bool(a.get("ann"))
    verdict, why = verdict_from(a["present"], a["rag"], a["indexes"], a["tags"], a["recs"], ann_present)

    facts = {
        "presence": a["present"],
        "docs_top": (a["docs"][:10] if a["docs"] else []),
        "recs": a["recs"],
        "tags": a["tags"],
        "xref": a["xref"],
        "rag": a["rag"],
        "indexes": a["indexes"],
        "critical_tags": CRITICAL_TAGS,
    }
    ai_obj = ai_block(use_ai, facts)

    DOC_LIMIT = 10 if brief else 25
    TAG_LIMIT = 15 if brief else 50

    def clamp(lst, n): return (lst or [])[:n]

    def flow(story, content_width):
        # Verdict
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Presence & counts
        story.append(P("Table presence & counts", H2))
        story.append(TableFromRows([{
            "cdc_docs": a["present"]["n_docs"],
            "cdc_sections": a["present"]["n_sections"],
            "sections_empty": a["present"]["n_sections_empty"],
            "sections_no_heading": a["present"]["n_sections_no_heading"],
            "sections_with_rec": a["present"]["n_sections_with_rec"],
        }], ["cdc_docs","cdc_sections","sections_empty","sections_no_heading","sections_with_rec"]))
        story.append(Spacer(1, 8))

        # Documents ingested (top)
        story.append(P("Documents ingested (top by sections)", H2))
        story.append(TableFromRows(
            clamp(a["docs"], DOC_LIMIT),
            ["slug","title","pub_date","n_sections","url"]
        ))
        story.append(Spacer(1, 8))

        # Recommendation coverage
        story.append(P("Recommendation coverage (R1–R12)", H2))
        story.append(TableFromRows(a["recs"] or [], ["rec_number","n"]))
        story.append(Spacer(1, 8))

        # Tags distribution
        story.append(P("Tags distribution", H2))
        story.append(TableFromRows(clamp(a["tags"], TAG_LIMIT), ["tag","n"]))
        story.append(Spacer(1, 8))

        # Cross-references
        story.append(P("Cross-references (standard codes)", H2))
        story.append(TableFromRows(
            [{"mappings_total": a["xref"]["mappings_total"], "sections_mapped": a["xref"]["sections_mapped"]}],
            ["mappings_total","sections_mapped"]
        ))
        story.append(TableFromRows(a["xref"]["by_system"] or [], ["system","n"]))
        story.append(Spacer(1, 8))

        # RAG corpus
        story.append(P("RAG corpus (source='cdc_opioid')", H2))
        story.append(TableFromRows(
            [{"rag_rows": a["rag"]["rag_rows"], "rag_no_embed": a["rag"]["rag_no_embed"]}],
            ["rag_rows","rag_no_embed"]
        ))
        story.append(Spacer(1, 8))

        # Index presence (TS + ANN)
        story.append(P("Index presence", H2))
        story.append(TableFromRows([{
            "cdc_sections_ts_gin": a["indexes"]["cdc_sections_ts_gin"],
            "cdc_sections_tags_gin": a["indexes"]["cdc_sections_tags_gin"],
            "rag_cdc_ann": bool(a["ann"])
        }], ["cdc_sections_ts_gin","cdc_sections_tags_gin","rag_cdc_ann"]))

        # Embedding coverage
        story.append(P("Embedding coverage (CDC in RAG)", H2))
        story.append(TableFromRows([{
            "rag_rows": a["embed"]["total"],
            "rag_no_embed": a["embed"]["no_embed"],
            "embed_pct": f"{a['embed']['pct']}%"
        }], ["rag_rows","rag_no_embed","embed_pct"]))
        story.append(Spacer(1,8))

        # ANN index details
        story.append(P("ANN index (ivfflat) details", H2))
        if a["ann"]:
            story.append(TableFromRows([{
                "index": a["ann"]["indexname"],
                "lists": a["ann"]["lists"]
            }], ["index","lists"]))
        else:
            story.append(TableFromRows([{"index":"(missing)","lists":None}], ["index","lists"]))
        story.append(Spacer(1,8))


    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "CDC OPIOID GUIDELINES — AUDIT & INTEGRITY", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    env = lambda k: os.getenv(k,"").lower() in ("1","true","yes","on")
    use_ai = ("--ai" in sys.argv) or env("AI")
    brief  = ("--brief" in sys.argv) or env("BRIEF")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai, brief=brief)

