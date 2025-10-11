#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import connect, q, build_doc, TableFromRows, P, H2, ai_analyze

def table_exists(conn, schema, table):
    r = q(conn, """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema=%s AND table_name=%s LIMIT 1
    """, (schema, table))
    return bool(r)

def flow(story, content_width):
    conn = connect()

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
    story.append(P("Coverage & Sizes", H2))
    story.append(TableFromRows(sizes, ["schema","table","size_bytes"],
                               widths=[1.2*inch, 2.9*inch, 1.3*inch]))

    # Canonical tables (best effort)
    has_dis  = table_exists(conn, "ontology", "orphanet_diseases")
    has_syn  = table_exists(conn, "ontology", "orphanet_synonyms")
    has_gene = table_exists(conn, "ontology", "orphanet_gene_links")
    has_ph   = table_exists(conn, "ontology", "orphanet_phenotype_links")

    # Core counts
    rows = []
    if has_dis:  rows += q(conn, "SELECT 'orphanet_diseases' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_diseases")
    if has_syn:  rows += q(conn, "SELECT 'orphanet_synonyms' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_synonyms")
    if has_gene: rows += q(conn, "SELECT 'orphanet_gene_links' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_gene_links")
    if has_ph:   rows += q(conn, "SELECT 'orphanet_phenotype_links' AS what, COUNT(*)::bigint AS n FROM ontology.orphanet_phenotype_links")
    story.append(P("Key Counts", H2))
    story.append(TableFromRows(rows, ["what","n"], widths=[2.8*inch, 1.1*inch]))

    # Name quality
    if has_dis:
        blanks = q(conn, """
            SELECT COUNT(*)::bigint AS blank_names
            FROM ontology.orphanet_diseases
            WHERE COALESCE(NULLIF(name,''),NULL) IS NULL
        """)
        story.append(P("Name Quality", H2))
        story.append(TableFromRows(blanks, ["blank_names"], widths=[1.3*inch]))

    # Top synonyms per disease
    if has_dis and has_syn:
        topsyn = q(conn, """
            SELECT d.orpha_code, d.name, COUNT(s.*)::bigint AS n_synonyms
            FROM ontology.orphanet_diseases d
            LEFT JOIN ontology.orphanet_synonyms s ON s.orpha_code=d.orpha_code
            GROUP BY d.orpha_code, d.name
            ORDER BY n_synonyms DESC, d.orpha_code
            LIMIT 10
        """)
        story.append(P("Top diseases by synonyms", H2))
        story.append(TableFromRows(topsyn, ["orpha","name","n_synonyms"],
                                   widths=[0.9*inch, 3.6*inch, 0.8*inch]))

    # Orphan checks (links referencing missing disease)
    orphan_rows = []
    if has_gene and has_dis:
        orphan_rows += q(conn, """
            SELECT 'gene_links_orphan_disease' AS what,
                   COUNT(*)::bigint AS n
            FROM ontology.orphanet_gene_links l
            LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
            WHERE d.orpha_code IS NULL
        """)
    if has_ph and has_dis:
        orphan_rows += q(conn, """
            SELECT 'phenotype_links_orphan_disease' AS what,
                   COUNT(*)::bigint AS n
            FROM ontology.orphanet_phenotype_links l
            LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code = l.orpha_code
            WHERE d.orpha_code IS NULL
        """)
    if orphan_rows:
        story.append(P("Link Orphan Checks", H2))
        story.append(TableFromRows(orphan_rows, ["what","n"], widths=[3.2*inch, 0.8*inch]))

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
                FROM ontology.orphanet_diseases WHERE COALESCE(NULLIF(name,''),NULL) IS NULL
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
        }
        ai_obj = ai_analyze(
            system=("You are auditing an Orphanet (Orphadata) load in Postgres. "
                    "Return only JSON: {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
                    "Consider table presence, counts plausibility, missing names, and link orphans."),
            user=facts
        )

    build_doc(
        args.out,
        "2ndOpinionMD — Orphanet Integrity Report",
        subtitle=None,
        build_flow=flow,
        ai_obj=ai_obj
    )

if __name__ == "__main__":
    main()

