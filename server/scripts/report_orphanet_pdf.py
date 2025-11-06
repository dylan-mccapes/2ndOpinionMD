#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)

TITLE = "05 • Orphanet — RAG Integrity"
SUB   = "Coverage, ANN index health, lengths, lexical indexes"

def table_exists(conn, schema, table):
    r = q(conn, """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema=%s AND table_name=%s
        LIMIT 1
    """, (schema, table))
    return bool(r)

def _stringify_rows(rows):
    out = []
    for r in rows:
        out.append({k: ("" if v is None else str(v)) for k, v in r.items()})
    return out

# ----- RAG/ANN sections -----
def embed_coverage(conn):
    return q(conn, """
      SELECT source,
             COUNT(*) AS total,
             COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
             COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
             ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
      FROM public.rag_corpus
      WHERE source='orphanet'
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
        AND i.indexname='rag_corpus_embedding_ann_orphanet'
      ORDER BY i.indexname
    """)

def length_stats(conn):
    # rag_corpus uses "text" for payload; keep broad fallback just in case
    return q(conn, """
      SELECT COUNT(*) AS total,
             MAX(length(COALESCE(NULLIF(text,''), NULLIF(content,''), title, ''))) AS max_len,
             percentile_disc(0.99) WITHIN GROUP (
               ORDER BY length(COALESCE(NULLIF(text,''), NULLIF(content,''), title, ''))
             ) AS p99_len,
             COUNT(*) FILTER (
               WHERE COALESCE(NULLIF(text,''), NULLIF(content,''), NULLIF(title,'')) IS NULL
             ) AS empty_rows
      FROM public.rag_corpus
      WHERE source='orphanet'
    """)

def trgm_info(conn):
    return q(conn, r"""
      SELECT i.indexname, replace(i.indexdef, chr(10),' ') AS indexdef
      FROM pg_indexes i
      WHERE (i.tablename, i.indexname) IN
        (('orphanet_diseases','orphanet_diseases_name_trgm'),
         ('orphanet_synonyms','orphanet_synonyms_syn_trgm'))
      ORDER BY i.indexname
    """)

def flow(story, content_width):
    conn = connect()

    # Title + subtitle (avoid passing numeric as positional to P())
    story.append(P(TITLE, H2))
    story.append(P(SUB, BODY))

    # Coverage & sizes (discover any orphanet_* tables)
    sizes = q(conn, """
        SELECT n.nspname AS schema, c.relname AS "table",
               pg_total_relation_size(c.oid)::bigint AS size_bytes
        FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='ontology'
          AND c.relkind='r'
          AND c.relname ILIKE 'orphanet%%'
        ORDER BY size_bytes DESC, "table"
    """)

    # Canonical presence
    has_dis  = table_exists(conn, "ontology", "orphanet_diseases")
    has_syn  = table_exists(conn, "ontology", "orphanet_synonyms")
    has_gene = table_exists(conn, "ontology", "orphanet_gene_links")
    has_ph   = table_exists(conn, "ontology", "orphanet_phenotype_links")

    # Key counts
    rows = []
    if has_dis:  rows += q(conn, "SELECT 'orphanet_diseases' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_diseases")
    if has_syn:  rows += q(conn, "SELECT 'orphanet_synonyms' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_synonyms")
    if has_gene: rows += q(conn, "SELECT 'orphanet_gene_links' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_gene_links")
    if has_ph:   rows += q(conn, "SELECT 'orphanet_phenotype_links' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_phenotype_links")

    # Name quality (blank names)
    blanks = []
    if has_dis:
        blanks = q(conn, """
            SELECT COUNT(*)::bigint AS blank_names
            FROM ontology.orphanet_diseases
            WHERE COALESCE(NULLIF(name,''),NULL) IS NULL
        """)

    # Top synonyms per disease
    topsyn = []
    if has_dis and has_syn:
        topsyn = q(conn, """
            SELECT d.orpha_code, d.name, COUNT(s.*)::bigint AS n_synonyms
            FROM ontology.orphanet_diseases d
            LEFT JOIN ontology.orphanet_synonyms s USING (orpha_code)
            GROUP BY d.orpha_code, d.name
            ORDER BY n_synonyms DESC, d.orpha_code
            LIMIT 10
        """)

    # Link orphan checks
    orphan_rows = []
    if has_gene and has_dis:
        orphan_rows += q(conn, """
            SELECT 'gene_links_orphan_disease' AS what, COUNT(*)::bigint AS n
            FROM ontology.orphanet_gene_links l
            LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
            WHERE d.orpha_code IS NULL
        """)
    if has_ph and has_dis:
        orphan_rows += q(conn, """
            SELECT 'phenotype_links_orphan_disease' AS what, COUNT(*)::bigint AS n
            FROM ontology.orphanet_phenotype_links l
            LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
            WHERE d.orpha_code IS NULL
        """)

    # ----- RAG coverage
    story.append(P("Embedding coverage", H2))
    story.append(TableFromRows(
        _stringify_rows(embed_coverage(conn)),
        ["source","total","done","pending","pct"],
        widths=[1.3*inch,1.1*inch,1.1*inch,1.2*inch,0.8*inch],
    ))

    # ----- ANN (ivfflat)
    story.append(P("ANN (ivfflat) index", H2))
    story.append(TableFromRows(
        _stringify_rows(list_ann(conn)),
        ["indexname","indisvalid","indisready","lists","size"],
        widths=[3.1*inch,0.8*inch,0.9*inch,0.8*inch,1.1*inch],
    ))

    # ----- Payload length sanity
    story.append(P("Payload length sanity", H2))
    story.append(TableFromRows(
        _stringify_rows(length_stats(conn)),
        ["total","max_len","p99_len","empty_rows"],
        widths=[1.0*inch]*4,
    ))

    # ----- TRGM/GIN
    story.append(P("Auxiliary lexical (TRGM/GIN) indexes", H2))
    trig = trgm_info(conn)
    if trig:
        story.append(TableFromRows(
            _stringify_rows(trig),
            ["indexname","indexdef"],
            widths=[2.6*inch, 4.6*inch]
        ))
    else:
        story.append(P("No TRGM/GIN indexes detected.", BODY))

    # ----- Coverage & sizes (Orphanet tables)
    story.append(P("Coverage & sizes (ontology.orphanet_*)", H2))
    story.append(TableFromRows(
        _stringify_rows(sizes),
        ["schema","table","size_bytes"],
        widths=[1.2*inch, 2.9*inch, 1.3*inch]
    ))

    # ----- Key counts
    story.append(P("Key counts", H2))
    story.append(TableFromRows(
        _stringify_rows(rows),
        ["what","n"],
        widths=[2.8*inch, 1.1*inch]
    ))

    # ----- Name quality
    if blanks:
        story.append(P("Name quality (blank disease names)", H2))
        story.append(TableFromRows(
            _stringify_rows(blanks),
            ["blank_names"],
            widths=[1.3*inch]
        ))

    # ----- Top synonyms
    if topsyn:
        story.append(P("Top diseases by #synonyms", H2))
        story.append(TableFromRows(
            _stringify_rows(topsyn),
            ["orpha_code","name","n_synonyms"],
            widths=[1.0*inch, 3.6*inch, 0.8*inch]
        ))

    # ----- Link orphan checks
    if orphan_rows:
        story.append(P("Link orphan checks", H2))
        story.append(TableFromRows(
            _stringify_rows(orphan_rows),
            ["what","n"],
            widths=[3.2*inch, 0.8*inch]
        ))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()

    ai_obj = None
    if args.ai and os.environ.get("OPENAI_API_KEY"):
        conn = connect()
        facts = {
            "tables": q(conn, """
                SELECT n.nspname AS schema, c.relname AS "table",
                       pg_total_relation_size(c.oid)::bigint AS size_bytes
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='ontology' AND c.relkind='r' AND c.relname ILIKE 'orphanet%%'
                ORDER BY size_bytes DESC, "table"
            """),
            "counts": q(conn, """
                WITH cc AS (
                  SELECT 'orphanet_diseases' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_diseases
                  UNION ALL SELECT 'orphanet_synonyms', COUNT(*)::bigint FROM ontology.orphanet_synonyms
                  UNION ALL SELECT 'orphanet_gene_links', COUNT(*)::bigint FROM ontology.orphanet_gene_links
                  UNION ALL SELECT 'orphanet_phenotype_links', COUNT(*)::bigint FROM ontology.orphanet_phenotype_links
                ) SELECT * FROM cc ORDER BY what
            """),
            "blank_names": q(conn, """
                SELECT COUNT(*)::bigint AS blank_names
                FROM ontology.orphanet_diseases
                WHERE COALESCE(NULLIF(name,''),NULL) IS NULL
            """),
            "orphans": q(conn, """
                SELECT what, n FROM (
                  SELECT 'gene_links_orphan_disease' AS what,
                         COUNT(*)::bigint AS n
                  FROM ontology.orphanet_gene_links l
                  LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
                  WHERE d.orpha_code IS NULL
                  UNION ALL
                  SELECT 'phenotype_links_orphan_disease',
                         COUNT(*)::bigint
                  FROM ontology.orphanet_phenotype_links l
                  LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
                  WHERE d.orpha_code IS NULL
                ) x ORDER BY what
            """),
            "coverage": embed_coverage(conn),
            "ann":      list_ann(conn),
            "lengths":  length_stats(conn),
        }
        ai_obj = ai_analyze(
            system=("You are auditing an Orphanet (Orphadata) load in Postgres. "
                    "Return only JSON: {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
                    "Focus on: low embedding coverage, invalid/empty ANN, excessive payload length, "
                    "missing core tables, blank names, and link orphans."),
            user=facts
        )

    build_doc(args.out, TITLE, subtitle=SUB, build_flow=flow, ai_obj=ai_obj)

if __name__ == "__main__":
    main()
