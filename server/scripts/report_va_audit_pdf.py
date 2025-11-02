#!/usr/bin/env python3
# VA/DoD Guidelines — Audit & Integrity PDF
import os
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/21_va.pdf"

def fetch_counts(conn):
    row = q(conn, """
        SELECT
          (SELECT count(*) FROM guidelines.va_docs)     AS n_docs,
          (SELECT count(*) FROM guidelines.va_sections) AS n_sections
    """)[0]
    return {k:int(row.get(k,0) or 0) for k in ("n_docs","n_sections")}

def fetch_rag(conn):
    return q(conn, """
        SELECT
          COUNT(*)::int AS rag_rows,
          COUNT(*) FILTER (WHERE embedding IS NULL)::int AS rag_no_embed
        FROM public.rag_corpus
        WHERE source='va_guidelines'
    """)[0]

def fetch_indexes(conn):
    def has_idx(sql, params=None):
        return bool(q(conn, sql, params))
    get = lambda sql, params=None: (q(conn, sql, params)[0] if q(conn, sql, params) else {})

    ann_row = get("""
      SELECT i.indexrelid::regclass::text AS name,
             pg_get_indexdef(i.indexrelid) AS def,
             pg_get_expr(i.indpred, i.indrelid) AS predicate
      FROM pg_index i
      JOIN pg_class t ON t.oid = i.indrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
      WHERE n.nspname='public' AND t.relname='rag_corpus'
        AND pg_get_indexdef(i.indexrelid) ILIKE '%USING ivfflat%'
        AND (pg_get_expr(i.indpred, i.indrelid) ILIKE '%source = ''va_guidelines''%'
             OR pg_get_expr(i.indpred, i.indrelid) ILIKE '%source=''va_guidelines''%')
      LIMIT 1
    """)
    return {
        "rag_va_ann": bool(ann_row),
        "rag_va_ann_name": ann_row.get("name"),
        "va_sections_tags_gin": has_idx("""
            SELECT 1 FROM pg_indexes
            WHERE schemaname='guidelines' AND tablename='va_sections'
              AND indexdef ILIKE '%USING gin%' AND indexdef ILIKE '%(tags)%'
            LIMIT 1
        """),
        "va_sections_ts_gin": has_idx("""
            SELECT 1 FROM pg_indexes
            WHERE schemaname='guidelines' AND tablename='va_sections'
              AND indexdef ILIKE '%USING gin%' AND indexdef ILIKE '%TO_TSVECTOR%'
            LIMIT 1
        """),
    }

def fetch_by_tag(conn, limit=15):
    return q(conn, f"""
      SELECT tag, COUNT(*)::int AS n
      FROM (SELECT unnest(tags) AS tag FROM guidelines.va_sections) t
      GROUP BY tag
      ORDER BY n DESC, tag ASC
      LIMIT {int(limit)}
    """)

def fetch_by_doc(conn, limit=12):
    return q(conn, f"""
      SELECT doc_slug, COUNT(*)::int AS n
      FROM guidelines.va_sections
      GROUP BY doc_slug
      ORDER BY n DESC, doc_slug ASC
      LIMIT {int(limit)}
    """)

def verdict_from(counts, rag, idx):
    if counts.get("n_docs",0)==0 or counts.get("n_sections",0)==0:
        return "fail", "No VA/DoD docs or sections were found."
    if rag.get("rag_rows",0)==0:
        return "fail", "No RAG rows for VA/DoD (source=va_guidelines)."
    problems = []
    if not idx.get("rag_va_ann"):
        problems.append("missing ANN index")
    if rag.get("rag_no_embed",0) > 0:
        problems.append("rows without embeddings")
    if problems:
        return "warn", "Health is mostly OK, but " + ", ".join(problems) + "."
    return "pass", "Docs, sections, RAG, embeddings, and ANN index look healthy."

def load():
    conn = connect()
    try:
        counts = fetch_counts(conn)
        rag    = fetch_rag(conn)
        idx    = fetch_indexes(conn)
        by_tag = fetch_by_tag(conn)
        by_doc = fetch_by_doc(conn)
        return {"counts":counts, "rag":rag, "indexes":idx, "by_tag":by_tag, "by_doc":by_doc}
    finally:
        conn.close()

def main(out=OUT, use_ai=False, brief=False):
    a = load()
    verdict, why = verdict_from(a["counts"], a["rag"], a["indexes"])

    ai_obj = None
    if use_ai:
        facts = {
            "counts": a["counts"],
            "rag": a["rag"],
            "indexes": a["indexes"],
            "by_tag": a["by_tag"][:10],
            "by_doc": a["by_doc"][:10],
        }
        ai_obj = ai_analyze(
            system=(
              "You audit a VA/DoD guidelines import (PDFs → sections) with a RAG corpus in Postgres. "
              "Return ONLY JSON like {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\",\"actions\":[\"...\",\"...\"]}. "
              "Rules: fail if no docs/sections or no RAG rows. Warn if ANN missing or any embeddings missing. Otherwise pass."
            ),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Table presence & counts", H2))
        story.append(TableFromRows([{
            "va_docs": a["counts"]["n_docs"],
            "va_sections": a["counts"]["n_sections"],
            "rag_rows": a["rag"]["rag_rows"],
            "rag_no_embed": a["rag"]["rag_no_embed"],
        }], ["va_docs","va_sections","rag_rows","rag_no_embed"]))
        story.append(Spacer(1, 8))

        story.append(P("Index presence", H2))
        story.append(TableFromRows([a["indexes"]],
          ["rag_va_ann","rag_va_ann_name","va_sections_tags_gin","va_sections_ts_gin"]))
        story.append(Spacer(1, 8))

        story.append(P("Top tags", H2))
        story.append(TableFromRows(a["by_tag"], ["tag","n"]))
        story.append(Spacer(1, 8))

        story.append(P("Most sectioned documents", H2))
        story.append(TableFromRows(a["by_doc"], ["doc_slug","n"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "VA / DoD — AUDIT & INTEGRITY", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    env = lambda k: os.getenv(k,"").lower() in ("1","true","yes","on")
    use_ai = ("--ai" in sys.argv) or env("AI")
    brief  = ("--brief" in sys.argv) or env("BRIEF")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai, brief=brief)

