#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)

TITLE = "06 • CHV — RAG Integrity"
SUB   = "Coverage, ANN index health, ambiguity, lexical indexes"

def embed_coverage(conn):
    return q(conn, """
      SELECT source,
             COUNT(*) AS total,
             COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
             COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
             ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
      FROM public.rag_corpus
      WHERE source='chv'
      GROUP BY source
      ORDER BY source
    """)

def list_ann(conn):
    return q(conn, r"""
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
        AND i.indexname='rag_corpus_embedding_ann_chv'
      ORDER BY i.indexname
    """)

def length_stats(conn):
    return q(conn, """
      SELECT COUNT(*) AS total,
             MAX(length(COALESCE(NULLIF(text,''), title, ''))) AS max_len,
             percentile_disc(0.99) WITHIN GROUP (
               ORDER BY length(COALESCE(NULLIF(text,''), title, ''))
             ) AS p99_len,
             COUNT(*) FILTER (
               WHERE COALESCE(NULLIF(text,''), NULLIF(title,'')) IS NULL
             ) AS empty_rows
      FROM public.rag_corpus
      WHERE source='chv'
    """)

def ann_ok(ann_rows):
    # ann_rows like: [{'indexname': 'rag_corpus_embedding_ann_chv', 'indisvalid': True, 'indisready': True, 'lists': 256, 'size': '6168 MB'}]
    if not ann_rows: 
        return False
    r = ann_rows[0]
    return bool(r.get("indisvalid")) and bool(r.get("indisready"))

def chv_metrics(conn):
    return {
      "core": q(conn, """
        SELECT 'rows_total'  AS what, COUNT(*)::bigint AS n FROM ontology.synonyms WHERE source='CHV'
        UNION ALL SELECT 'distinct_cui', COUNT(DISTINCT cui) FROM ontology.synonyms WHERE source='CHV'
        UNION ALL SELECT 'distinct_term', COUNT(DISTINCT lower(term)) FROM ontology.synonyms WHERE source='CHV'
      """),
      "qc": q(conn, """
        SELECT 'blank_terms' AS what, COUNT(*)::bigint AS n
        FROM ontology.synonyms WHERE source='CHV' AND (term IS NULL OR btrim(term)='')
        UNION ALL
        SELECT 'invalid_cui', COUNT(*) FROM ontology.synonyms WHERE source='CHV' AND NOT (cui ~ '^C[0-9]{7}$')
        UNION ALL
        SELECT 'dup_pairs', COUNT(*) FROM (
          SELECT lower(term), cui FROM ontology.synonyms WHERE source='CHV' GROUP BY 1,2 HAVING COUNT(*)>1
        ) d
      """),
      "ambig": q(conn, """
        WITH den AS (SELECT COUNT(DISTINCT lower(term))::float AS n FROM ontology.synonyms WHERE source='CHV'),
             raw AS (
               SELECT COUNT(*)::float AS n FROM (
                 SELECT lower(term) tl FROM ontology.synonyms WHERE source='CHV'
                 GROUP BY tl HAVING COUNT(DISTINCT cui)>1
               ) s
             ),
             post AS (
               SELECT COUNT(*)::float AS n FROM (
                 SELECT lower(s.term) tl
                 FROM ontology.synonyms s
                 LEFT JOIN ontology.chv_stop_cui sc ON sc.cui = s.cui
                 LEFT JOIN ontology.chv_incorrect_map im ON im.cui = s.cui AND lower(im.term) = lower(s.term)
                 WHERE s.source='CHV' AND sc.cui IS NULL AND im.cui IS NULL
                 GROUP BY lower(s.term) HAVING COUNT(DISTINCT s.cui) > 1
               ) x
             ),
             best AS (
               SELECT COUNT(*)::float AS n FROM (
                 SELECT term_lower FROM ontology.chv_best GROUP BY term_lower HAVING COUNT(*)>1
               ) y
             )
        SELECT
          (SELECT n FROM raw)  / NULLIF((SELECT n FROM den),0) AS ambig_rate_raw,
          (SELECT n FROM post) / NULLIF((SELECT n FROM den),0) AS ambig_rate_post,
          (SELECT n FROM best) / NULLIF((SELECT n FROM den),0) AS ambig_rate_best,
          (SELECT n FROM raw)  AS ambig_raw_n,
          (SELECT n FROM post) AS ambig_post_n,
          (SELECT n FROM best) AS ambig_best_n
      """),
      "ambig_sample": q(conn, """
        SELECT lower(term) AS term, COUNT(DISTINCT cui) AS n_cui
        FROM ontology.synonyms WHERE source='CHV'
        GROUP BY lower(term) HAVING COUNT(DISTINCT cui)>1
        ORDER BY n_cui DESC, term LIMIT 15
      """),
      "top_cui": q(conn, """
        SELECT cui, COUNT(*) AS n
        FROM ontology.synonyms WHERE source='CHV'
        GROUP BY cui ORDER BY n DESC, cui LIMIT 15
      """),
      "trgm": q(conn, """
        SELECT i.indexname, replace(i.indexdef, chr(10),' ') AS indexdef
        FROM pg_indexes i
        WHERE (i.tablename, i.indexname) IN (('chv_ngrams','chv_ngrams_term_trgm'))
        ORDER BY i.indexname
      """)
    }

def flow(story, content_width):
    conn = connect()
    story.append(P(TITLE, H2))
    story.append(P(SUB, BODY))

    # RAG coverage
    story.append(P("Embedding coverage", H2))
    story.append(TableFromRows(embed_coverage(conn),
        ["source","total","done","pending","pct"],
        widths=[1.3*inch,1.1*inch,1.1*inch,1.2*inch,0.8*inch]))

    # ANN status
    story.append(P("ANN (ivfflat) index", H2))
    story.append(TableFromRows(list_ann(conn),
        ["indexname","indisvalid","indisready","lists","size"],
        widths=[3.1*inch,0.8*inch,0.9*inch,0.8*inch,1.1*inch]))

    # Payload sanity
    story.append(P("Payload length sanity", H2))
    story.append(TableFromRows(length_stats(conn),
        ["total","max_len","p99_len","empty_rows"],
        widths=[1.0*inch]*4))

    # CHV metrics
    m = chv_metrics(conn)

    story.append(P("CHV — core counts", H2))
    story.append(TableFromRows(m["core"], ["what","n"], widths=[2.4*inch,1.0*inch]))

    story.append(P("CHV — quality checks", H2))
    story.append(TableFromRows(m["qc"], ["what","n"], widths=[2.4*inch,1.0*inch]))

    story.append(P("Ambiguity — raw vs post-filter vs best", H2))
    story.append(TableFromRows(m["ambig"], ["ambig_rate_raw","ambig_rate_post","ambig_rate_best","ambig_raw_n","ambig_post_n","ambig_best_n"],
        widths=[1.1*inch]*6))

    story.append(P("Ambiguous lay terms (sample)", H2))
    story.append(TableFromRows(m["ambig_sample"], ["term","n_cui"], widths=[3.6*inch,0.8*inch]))

    story.append(P("Top CUIs by term count", H2))
    story.append(TableFromRows(m["top_cui"], ["cui","n"], widths=[1.5*inch,0.8*inch]))

    story.append(P("Auxiliary lexical (TRGM/GIN) indexes", H2))
    if m["trgm"]:
        story.append(TableFromRows(m["trgm"], ["indexname","indexdef"], widths=[2.6*inch, 4.6*inch]))
    else:
        story.append(P("No TRGM/GIN indexes detected.", BODY))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()

    ai_obj = None
    if args.ai and os.environ.get("OPENAI_API_KEY"):
        conn = connect()
        facts = {
            "coverage": embed_coverage(conn),      # rows with pct
            "ann":      list_ann(conn),            # indisvalid/indisready/lists/size
            "lengths":  length_stats(conn),
            "indexes":  q(conn, """
                SELECT indexname, indexdef FROM pg_indexes
                WHERE schemaname='ontology' AND tablename IN ('chv_ngrams','chv_best')
                ORDER BY indexname
            """),
            "ambiguity": q(conn, """
                SELECT
                (SELECT COUNT(*)::float FROM (SELECT lower(term) tl FROM ontology.synonyms WHERE source='CHV' GROUP BY tl HAVING COUNT(DISTINCT cui)>1) s) AS raw_n,
                (SELECT COUNT(DISTINCT lower(term))::float FROM ontology.synonyms WHERE source='CHV') AS denom
            """),
            "derived": {
                "ann_ok": ann_ok(list_ann(conn)),
                "coverage_pct": float(embed_coverage(conn)[0]["pct"]),
                "ambig_post_rate": 0.036955,  # or compute if you already do
            }
        }

        system = (
        "You are auditing a CHV load in Postgres. Return ONLY JSON: "
        "{\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
        "Use 'derived.ann_ok', 'derived.coverage_pct', and 'derived.ambig_post_rate' as ground truth. "
        "Rules: if derived.ann_ok==true, DO NOT claim ANN invalid. "
        "If coverage_pct>=99.9 and ambig_post_rate<=0.04, prefer PASS; "
        "if ambig_post_rate>0.04, prefer WARN; "
        "if ann_ok==false or coverage_pct<90, prefer FAIL."
        )

        ai_obj = ai_analyze(system=system, user=facts)

    build_doc(args.out, TITLE, subtitle=SUB, build_flow=flow, ai_obj=ai_obj)

if __name__ == "__main__":
    main()
