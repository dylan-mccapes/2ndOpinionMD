#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from reportlab.lib.units import inch
from report_common import (
    build_doc,      # build_doc(out_path, title, subtitle, build_flow, ai_obj=None)
    TableFromRows,  # TableFromRows(rows, columns, widths=None)
    q,              # q(conn, sql, params=None) -> list[dict]
    P,              # P(text, style=None) -> Paragraph
    H2,             # heading style
    ai_analyze,     # ai_analyze(system, user) -> dict/obj for build_doc
)

TITLE = "04 • LOINC & RxNorm — RAG Integrity"
SUB   = "Embeddings coverage, ANN index health, and auxiliary search indexes"

# -------------------
# AI gating
# -------------------
def ai_enabled(args) -> tuple[bool, str]:
    if not os.getenv("OPENAI_API_KEY"):
        return (False, "AI disabled: OPENAI_API_KEY not set.")
    if not args.ai and not os.getenv("REPORT_AI"):
        return (False, "AI disabled: pass --ai or set REPORT_AI=1.")
    return (True, "AI enabled.")

# -------------------
# Queries
# -------------------
def embed_coverage(conn):
    sql = """
    SELECT source,
           COUNT(*) AS total,
           COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
           COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
           ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
    FROM public.rag_corpus
    WHERE source IN ('loinc','rxnorm')
    GROUP BY source
    ORDER BY source;
    """
    return q(conn, sql)

def ann_status(conn, indexname):
    # robust lists extraction via reloptions (pg14)
    sql = r"""
    SELECT
      i.indexname,
      x.indisvalid,
      x.indisready,
      COALESCE((
        SELECT option_value::int
        FROM pg_options_to_table(c.reloptions)
        WHERE option_name = 'lists'
      ), 0) AS lists,
      pg_size_pretty(pg_relation_size(x.indexrelid)) AS size
    FROM pg_index x
    JOIN pg_class c     ON c.oid = x.indexrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_indexes i   ON i.indexname = c.relname
    WHERE i.tablename = 'rag_corpus'
      AND i.indexname = %s
    ORDER BY i.indexname;
    """
    return q(conn, sql, (indexname,))

def length_stats(conn, source):
    sql = """
    SELECT
      COUNT(*)                           AS total,
      MAX(length(text))                  AS max_len,
      percentile_disc(0.99) WITHIN GROUP (ORDER BY length(text)) AS p99_len,
      COUNT(*) FILTER (WHERE text IS NULL OR length(text)=0)     AS empty_rows
    FROM public.rag_corpus
    WHERE source = %s;
    """
    return q(conn, sql, (source,))

def trgm_info(conn):
    sql = r"""
    SELECT i.indexname, replace(i.indexdef, chr(10),' ') AS indexdef
    FROM pg_indexes i
    WHERE (i.tablename, i.indexname) IN
          (('loinc_terms','loinc_long_common_name_trgm'),
           ('loinc_terms','loinc_shortname_trgm'),
           ('rxnorm_conso','rxnorm_conso_str_gin_idx'))
    ORDER BY i.indexname;
    """
    return q(conn, sql)

# -------------------
# Flow (render)
# -------------------
def flow(story, content_width, conn):
    story.append(P(TITLE))
    story.append(P(SUB))

    story.append(P("Overview", H2))

    # Coverage
    story.append(P("Embedding coverage", H2))
    cov = embed_coverage(conn)
    story.append(TableFromRows(
        cov,
        ["source","total","done","pending","pct"],
        widths=[1.2*inch, 1.1*inch, 1.1*inch, 1.2*inch, 0.8*inch],
    ))

    # ANN
    story.append(P("ANN (ivfflat) indexes", H2))
    ann_loinc = ann_status(conn, "rag_corpus_embedding_ann_loinc")
    ann_rx    = ann_status(conn, "rag_corpus_embedding_ann_rxnorm")
    story.append(TableFromRows(
        ann_loinc, ["indexname","indisvalid","indisready","lists","size"],
        widths=[3.2*inch, 0.9*inch, 0.9*inch, 0.8*inch, 1.2*inch]
    ))
    story.append(TableFromRows(
        ann_rx, ["indexname","indisvalid","indisready","lists","size"],
        widths=[3.2*inch, 0.9*inch, 0.9*inch, 0.8*inch, 1.2*inch]
    ))

    # Length sanity
    story.append(P("Payload length sanity", H2))
    ls_l = length_stats(conn, "loinc")
    ls_r = length_stats(conn, "rxnorm")
    story.append(P("LOINC"))
    story.append(TableFromRows(ls_l, ["total","max_len","p99_len","empty_rows"], widths=[1.0*inch]*4))
    story.append(P("RxNorm"))
    story.append(TableFromRows(ls_r, ["total","max_len","p99_len","empty_rows"], widths=[1.0*inch]*4))

    # TRGM/GIN
    story.append(P("Auxiliary lexical (TRGM/GIN) indexes", H2))
    trig = trgm_info(conn)
    if trig:
        story.append(TableFromRows(trig, ["indexname","indexdef"], widths=[2.6*inch, 4.6*inch]))
    else:
        story.append(P("No TRGM/GIN indexes detected."))

# -------------------
# Main
# -------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dsn", default="postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()

    use_ai, msg = ai_enabled(args)
    print(msg)

    with psycopg2.connect(args.dsn, cursor_factory=RealDictCursor) as conn:
        # Build AI signals if enabled
        ai_obj = None
        if use_ai:
            coverage = embed_coverage(conn)
            ann = {
                "loinc": (ann_status(conn, "rag_corpus_embedding_ann_loinc")[0]
                          if ann_status(conn, "rag_corpus_embedding_ann_loinc") else None),
                "rxnorm": (ann_status(conn, "rag_corpus_embedding_ann_rxnorm")[0]
                           if ann_status(conn, "rag_corpus_embedding_ann_rxnorm") else None),
            }
            lengths = {
                "loinc": (length_stats(conn, "loinc")[0] if length_stats(conn, "loinc") else None),
                "rxnorm": (length_stats(conn, "rxnorm")[0] if length_stats(conn, "rxnorm") else None),
            }
            meta = {"report": "loinc_rxnorm", "title": TITLE}

            system = (
                "You are auditing a Postgres-backed RAG corpus for LOINC and RxNorm. "
                "Given JSON signals about embedding coverage, ANN index health (valid/ready/lists/size), "
                "payload lengths, and TRGM presence, return a short JSON object with keys: "
                "{\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\","
                "\"actions\":[\"short imperative steps\"],"
                "\"highlights\":[\"notable numbers or anomalies\"]}. "
                "Be strict if ANN indexes are not ready/valid, lists are 0, or coverage < 99%."
            )
            user_payload = {"coverage": coverage, "ann": ann, "lengths": lengths, "meta": meta, "trgm": trgm_info(conn)}
            ai_obj = ai_analyze(system=system, user=user_payload)

        build_doc(
            out_path=args.out,
            title=TITLE,
            subtitle=SUB,
            build_flow=lambda story, w: flow(story, w, conn),
            ai_obj=ai_obj,   # <-- this renders the AI section panel
        )

if __name__ == "__main__":
    main()
