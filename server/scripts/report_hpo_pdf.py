#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse, datetime
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)

def table_exists(conn, schema: str, table: str) -> bool:
    rows = q(conn, """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema=%s AND table_name=%s
        LIMIT 1
    """, (schema, table))
    return len(rows) > 0

def col_exists(conn, schema: str, table: str, col: str) -> bool:
    rows = q(conn, """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s AND column_name=%s
        LIMIT 1
    """, (schema, table, col))
    return len(rows) > 0

def first_existing(conn, candidates):
    for s, t in candidates:
        if table_exists(conn, s, t):
            return (s, t)
    return None

def safe_count(conn, schema, table):
    if not table_exists(conn, schema, table):
        return 0
    r = q(conn, f"SELECT COUNT(*) AS n FROM {schema}.{table}")
    return r[0]['n'] if r else 0

def pick_id_col(conn, schema: str, table: str, candidates):
    for c in candidates:
        if col_exists(conn, schema, table, c):
            return c
    return None

def pick_name_col(conn, schema: str, table: str):
    if col_exists(conn, schema, table, "name"):
        return "name"
    if col_exists(conn, schema, table, "label"):
        return "label"
    return None

def flow(story, content_width):
    conn = connect()

    # 1) Sizes for HPO tables
    sizes = q(conn, """
        SELECT n.nspname AS schema,
               c.relname AS "table",
               pg_total_relation_size(c.oid)::bigint AS size_bytes
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname='ontology'
          AND c.relkind='r'
          AND (c.relname ILIKE 'hpo%%' OR c.relname ILIKE 'hp%%')
        ORDER BY size_bytes DESC, "table"
    """)
    story.append(P("Coverage & Sizes", H2))
    story.append(TableFromRows(
        sizes, ["schema","table","size_bytes"],
        widths=[1.1*inch, 2.4*inch, 1.8*inch]
    ))

    # 2) Canonical table detection
    terms_tbl = first_existing(conn, [
        ("ontology","hpo_terms"),
        ("ontology","hpo"),
        ("ontology","hpo_nodes"),
    ])
    edges_tbl = first_existing(conn, [
        ("ontology","hpo_edges"),
        ("ontology","hpo_relations"),
    ])
    syn_tbl = first_existing(conn, [("ontology","hpo_synonyms")])
    links_tbl = first_existing(conn, [
        ("ontology","hpo_disease_links"),
        ("ontology","hpoa_links"),
    ])

    # Resolve common ID column names
    term_id_col = syn_id_col = None
    if terms_tbl:
        term_id_col = pick_id_col(conn, terms_tbl[0], terms_tbl[1], ["hpo_id","term_id","id"])
    if syn_tbl:
        syn_id_col = pick_id_col(conn, syn_tbl[0], syn_tbl[1], ["hpo_id","term_id","id"])

    edge_parent_col = edge_child_col = None
    if edges_tbl:
        edge_parent_col = pick_id_col(conn, edges_tbl[0], edges_tbl[1], ["parent_id","parent"])
        edge_child_col  = pick_id_col(conn, edges_tbl[0], edges_tbl[1], ["child_id","child"])

    # 3) Core counts
    terms_total = 0
    terms_active = terms_obsolete = None
    if terms_tbl:
        schema, table = terms_tbl
        terms_total = safe_count(conn, schema, table)
        if col_exists(conn, schema, table, "is_obsolete"):
            r = q(conn, f"""
                SELECT
                    COUNT(*) FILTER (WHERE COALESCE(is_obsolete,false)=false) AS active,
                    COUNT(*) FILTER (WHERE COALESCE(is_obsolete,false)=true)  AS obsolete
                FROM {schema}.{table}
            """)
            if r:
                terms_active = r[0]['active']
                terms_obsolete = r[0]['obsolete']

    edges_total = edges_tbl and safe_count(conn, *edges_tbl) or 0
    syn_total   = syn_tbl   and safe_count(conn, *syn_tbl)   or 0
    links_total = links_tbl and safe_count(conn, *links_tbl) or 0

    summary = [
        {"metric": "terms_total",     "value": terms_total},
        {"metric": "terms_active",    "value": terms_active if terms_active is not None else "n/a"},
        {"metric": "terms_obsolete",  "value": terms_obsolete if terms_obsolete is not None else "n/a"},
        {"metric": "edges_total",     "value": edges_total},
        {"metric": "synonyms_total",  "value": syn_total},
        {"metric": "disease_links",   "value": links_total},
    ]
    story.append(P("Key Counts", H2))
    story.append(TableFromRows(summary, ["metric","value"], widths=[2.0*inch, 1.3*inch]))

    # 4) Top synonyms
    if syn_tbl and terms_tbl and syn_id_col and term_id_col:
        syn_schema, syn_table   = syn_tbl
        term_schema, term_table = terms_tbl
        name_col = pick_name_col(conn, term_schema, term_table)
        topsyn = q(conn, f"""
            SELECT t.{term_id_col} AS hpo_id,
                   COALESCE({('t.'+name_col) if name_col else "' '::text"}, '') AS name,
                   COUNT(*) AS n_synonyms
            FROM {syn_schema}.{syn_table} s
            JOIN {term_schema}.{term_table} t
              ON t.{term_id_col} = s.{syn_id_col}
            GROUP BY 1,2
            ORDER BY n_synonyms DESC, hpo_id
            LIMIT 10
        """)
        story.append(P("Top terms by synonyms", H2))
        story.append(TableFromRows(
            topsyn, ["hpo_id","name","n_synonyms"],
            widths=[1.2*inch, 3.3*inch, 0.9*inch]
        ))

    # 5) Top parents by #children
    if edges_tbl and terms_tbl and edge_parent_col and term_id_col:
        e_schema, e_table = edges_tbl
        t_schema, t_table = terms_tbl
        name_col = pick_name_col(conn, t_schema, t_table)
        deg = q(conn, f"""
            SELECT e.{edge_parent_col} AS hpo_id,
                   COALESCE({('t.'+name_col) if name_col else "' '::text"}, '') AS name,
                   COUNT(*) AS n_children
            FROM {e_schema}.{e_table} e
            LEFT JOIN {t_schema}.{t_table} t
              ON t.{term_id_col} = e.{edge_parent_col}
            GROUP BY 1,2
            ORDER BY n_children DESC, hpo_id
            LIMIT 10
        """)
        story.append(P("Top parents by #children (is_a / hierarchical)", H2))
        story.append(TableFromRows(
            deg, ["hpo_id","name","n_children"],
            widths=[1.2*inch, 3.3*inch, 0.9*inch]
        ))

    # Extra timestamp (optional; build_doc adds one already)
    story.append(P(f"Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}", BODY))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()

    ai_obj = None
    if args.ai and os.environ.get("OPENAI_API_KEY"):
        conn = connect()
        signals = {
            "tables": q(conn, """
                SELECT n.nspname AS schema, c.relname AS "table",
                       pg_total_relation_size(c.oid)::bigint AS size_bytes
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='ontology' AND c.relkind='r'
                  AND (c.relname ILIKE 'hpo%%' OR c.relname ILIKE 'hp%%')
                ORDER BY size_bytes DESC, "table"
            """),
            "counts": {}
        }
        for sch, tbl, key in [
            ("ontology","hpo_terms","terms_total"),
            ("ontology","hpo_edges","edges_total"),
            ("ontology","hpo_synonyms","synonyms_total"),
            ("ontology","hpo_disease_links","disease_links"),
        ]:
            try:
                signals["counts"][key] = safe_count(conn, sch, tbl)
            except Exception:
                signals["counts"][key] = 0

        ai_obj = ai_analyze(
            system=("You are auditing an HPO (Human Phenotype Ontology) load in a Postgres DB. "
                    "Return only JSON: {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
                    "Focus on missing core tables, low counts, or absent hierarchy/synonyms."),
            user=signals
        )

    build_doc(
        args.out,
        "2ndOpinionMD — HPO Integrity Report",
        subtitle=None,
        build_flow=flow,
        ai_obj=ai_obj
    )

if __name__ == "__main__":
    main()
