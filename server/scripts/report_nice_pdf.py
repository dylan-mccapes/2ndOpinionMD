#!/usr/bin/env python3
import os, sys
from datetime import datetime
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

SRC = "nice"

def load():
    conn = connect()
    try:
        pres = q(conn, """
          SELECT
            (to_regclass('guidelines.docs') IS NOT NULL)      AS has_docs,
            (to_regclass('guidelines.sections') IS NOT NULL)  AS has_sections,
            (to_regclass('public.rag_corpus') IS NOT NULL)    AS has_rag,
            (to_regclass('public.rag_corpus_chunks') IS NOT NULL) AS has_chunks
        """)[0]

        counts = q(conn, f"""
          WITH d AS (SELECT COUNT(*)::bigint AS n FROM guidelines.docs WHERE source_key='{SRC}'),
               s AS (SELECT COUNT(*)::bigint AS n FROM guidelines.sections s
                     JOIN guidelines.docs d ON d.id=s.doc_id WHERE d.source_key='{SRC}'),
               r AS (SELECT COUNT(*)::bigint AS n FROM public.rag_corpus WHERE source='{SRC}'),
               c AS (SELECT COUNT(*)::bigint AS n,
                            COUNT(*) FILTER (WHERE embedding IS NULL)::bigint AS missing_emb
                     FROM public.rag_corpus_chunks WHERE source='{SRC}')
          SELECT
            (SELECT n FROM d) AS docs,
            (SELECT n FROM s) AS sections,
            (SELECT n FROM r) AS rag_rows,
            (SELECT n FROM c) AS chunks,
            (SELECT missing_emb FROM c) AS chunks_missing_emb
        """)[0]

        dup_docs = q(conn, """
          SELECT source_key, doc_key, COUNT(*)::bigint AS n
          FROM guidelines.docs
          WHERE version IS NULL
          GROUP BY 1,2 HAVING COUNT(*) > 1
          ORDER BY 1,2
        """)

        recent = q(conn, f"""
          SELECT id, doc_key, COALESCE(title,'') AS title,
                 to_char(COALESCE(fetched_at, now()), 'YYYY-MM-DD"T"HH24:MI') AS fetched_at,
                 COALESCE(length(text_full),0)::bigint AS text_len
          FROM guidelines.docs
          WHERE source_key='{SRC}'
          ORDER BY fetched_at DESC NULLS LAST
          LIMIT 12
        """)

        by_doc_sections = q(conn, f"""
          SELECT d.doc_key, COALESCE(d.title,'') AS title, COUNT(*)::bigint AS sections
          FROM guidelines.sections s
          JOIN guidelines.docs d ON d.id = s.doc_id
          WHERE d.source_key='{SRC}'
          GROUP BY 1,2
          ORDER BY sections DESC, d.doc_key
          LIMIT 15
        """)

        big_chunks = q(conn, f"""
          SELECT id, (meta->>'doc_key')::text AS doc_key,
                 GREATEST(length(text),0)::bigint AS chars
          FROM public.rag_corpus_chunks
          WHERE source='{SRC}'
          ORDER BY chars DESC
          LIMIT 10
        """)

        missing_emb = q(conn, f"""
          SELECT id, (meta->>'doc_key')::text AS doc_key
          FROM public.rag_corpus_chunks
          WHERE source='{SRC}' AND embedding IS NULL
          LIMIT 20
        """)

        samples = q(conn, f"""
          SELECT s.id, d.doc_key, COALESCE(s.heading,'(page)') AS heading,
                 substring(s.text for 200) AS preview
          FROM guidelines.sections s
          JOIN guidelines.docs d ON d.id=s.doc_id
          WHERE d.source_key='{SRC}'
          ORDER BY s.id
          LIMIT 12
        """)

        tables = q(conn, """
            WITH t AS (
                SELECT 'guidelines.docs' AS tbl, COUNT(*)::bigint AS rows FROM guidelines.docs
                UNION ALL SELECT 'guidelines.sections', COUNT(*) FROM guidelines.sections
                UNION ALL SELECT 'public.rag_corpus', COUNT(*) FROM public.rag_corpus
                UNION ALL SELECT 'public.rag_corpus_chunks', COUNT(*) FROM public.rag_corpus_chunks
            )
            SELECT tbl, rows FROM t ORDER BY tbl
        """)

        return pres, counts, dup_docs, recent, by_doc_sections, big_chunks, missing_emb, samples, tables
    finally:
        conn.close()

def verdict_from(pres, counts, dup_docs):
    if not pres["has_docs"]:
        return "fail", "guidelines.docs table missing."
    if counts["docs"] == 0:
        return "warn", "No NICE documents loaded."
    problems = []
    if not pres["has_sections"]:
        problems.append("guidelines.sections table missing")
    if pres["has_sections"] and counts["sections"] == 0:
        problems.append("0 sections")
    if pres["has_rag"] and counts["rag_rows"] == 0:
        problems.append("0 rag_corpus rows")
    if pres["has_chunks"] and counts["chunks"] == 0:
        problems.append("0 rag_corpus_chunks rows")
    if pres["has_chunks"] and counts["chunks_missing_emb"] > 0:
        problems.append(f"{counts['chunks_missing_emb']} chunks missing embeddings")
    if dup_docs:
        problems.append("duplicate (source_key, doc_key) rows where version IS NULL")

    if problems:
        return "warn", "; ".join(problems)
    return "pass", "NICE docs, sections, RAG rows, chunks, and embeddings look healthy."

def main(out="db_integrity_reports/13_guidelines_nice.pdf", use_ai=False):
    pres, counts, dup_docs, recent, by_doc_sections, big_chunks, missing_emb, samples, tables = load()
    verdict, why = verdict_from(pres, counts, dup_docs)

    ai_obj = None
    if use_ai:
        facts = {
            "tables_present": pres,
            "counts": counts,
            "dup_docs": dup_docs[:5],
            "top_docs_by_sections": by_doc_sections[:8],
            "missing_embeddings": len(missing_emb),
        }
        ai_obj = ai_analyze(
            system=(
              "You are auditing NICE guideline ingestion and chunk embeddings in PostgreSQL. "
              "Return ONLY JSON like {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\"}. "
              "Rules: fail if docs table missing; warn if 0 docs/sections/rag/chunks or any missing embeddings/duplicates; otherwise pass."
            ),
            user=facts
        )

    def flow(story, cw):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Table presence & row counts (all rows)", H2))
        story.append(TableFromRows(tables, ["tbl","rows"]))
        story.append(Spacer(1, 8))

        story.append(P("Core counts (NICE)", H2))
        story.append(TableFromRows([counts], ["docs","sections","rag_rows","chunks","chunks_missing_emb"]))
        story.append(Spacer(1, 8))

        if dup_docs:
            story.append(P("Duplicates (version IS NULL)", H2))
            story.append(TableFromRows(dup_docs, ["source_key","doc_key","n"]))
            story.append(Spacer(1, 8))

        if by_doc_sections:
            story.append(P("Top docs by section count", H2))
            story.append(TableFromRows(by_doc_sections, ["doc_key","title","sections"]))
            story.append(Spacer(1, 8))

        if recent:
            story.append(P("Most recently loaded docs", H2))
            story.append(TableFromRows(recent, ["id","doc_key","title","fetched_at","text_len"]))
            story.append(Spacer(1, 8))

        if big_chunks:
            story.append(P("Largest chunks (by characters)", H2))
            story.append(TableFromRows(big_chunks, ["id","doc_key","chars"]))
            story.append(Spacer(1, 8))

        if missing_emb:
            story.append(P("Chunks missing embeddings (sample)", H2))
            story.append(TableFromRows(missing_emb, ["id","doc_key"]))
            story.append(Spacer(1, 8))

        if samples:
            story.append(P("Sample sections", H2))
            story.append(TableFromRows(samples, ["id","doc_key","heading","preview"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "NICE Guidelines — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    out = "db_integrity_reports/13_guidelines_nice.pdf"
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)

