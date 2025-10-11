#!/usr/bin/env python3
import argparse
from report_common import q, connect, build_doc, TableFromRows, P, H2
from reportlab.lib.units import inch

def flow(story, content_width):
    conn = connect()

    # Summary counts
    summary = q(conn, """
        SELECT 'icd10cm_mappings (ExtendedMap)' AS k, COUNT(*)::text AS v
          FROM ontology.snomed_map_icd10cm
        UNION ALL SELECT 'concepts', COUNT(*)::text FROM ontology.concepts
        UNION ALL SELECT 'descriptions', COUNT(*)::text FROM ontology.descriptions
        UNION ALL SELECT 'relationships', COUNT(*)::text FROM ontology.relationships
        UNION ALL SELECT 'refset_members', COUNT(*)::text FROM ontology.refset_members
        ORDER BY 1;
    """)
    story.append(P("Summary Counts", H2))
    story.append(TableFromRows(summary, ["k","v"], widths=[3.0*inch, 1.5*inch]))

    # Table sizes (top relations by total size)
    sizes = q(conn, """
        SELECT c.relname AS table, pg_total_relation_size(c.oid) AS size_bytes
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname='ontology' AND c.relkind='r'
        ORDER BY pg_total_relation_size(c.oid) DESC
        LIMIT 3;
        """)
    story.append(P("Table Sizes (total relation size)", H2))
    story.append(TableFromRows(sizes, ["schema","table","size_bytes"], widths=[1.3*inch, 2.8*inch, 1.3*inch]))

    # ExtendedMap coverage to ICD-10-CM
    cov = q(conn, """
        SELECT
          COUNT(*) AS rows_all,
          COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
          COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes
        FROM ontology.snomed_map_icd10cm;
    """)
    story.append(P("ExtendedMap → ICD-10-CM Coverage", H2))
    story.append(TableFromRows(cov, ["rows_all","rows_with_target","distinct_icd10cm_codes"], widths=[1.6*inch]*3))

    # Top ICD-10-CM targets
    top = q(conn, """
        SELECT NULLIF(trim(map_target),'') AS icd10cm_code, COUNT(*) AS snomed_mappings
        FROM ontology.snomed_map_icd10cm
        WHERE NULLIF(trim(map_target),'') IS NOT NULL
        GROUP BY 1
        ORDER BY snomed_mappings DESC, icd10cm_code
        LIMIT 10;
    """)
    story.append(P("Top 10 ICD-10-CM Targets (by SNOMED mappings)", H2))
    story.append(TableFromRows(top, ["icd10cm_code","snomed_mappings"], widths=[1.8*inch, 1.2*inch]))

    # Concepts by effective year — robust to 'YYYYMMDD' or 'YYYY-MM-DD'
    years = q(conn, """
        WITH x AS (
        SELECT
            CASE
            WHEN effective_time IS NULL THEN NULL
            WHEN (effective_time::text) ~ '^[0-9]{8}$'
                THEN to_date(effective_time::text, 'YYYYMMDD')
            WHEN (effective_time::text) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                THEN to_date(effective_time::text, 'YYYY-MM-DD')
            ELSE NULL
            END AS eff_date
        FROM ontology.descriptions
        )
        SELECT to_char(eff_date,'YYYY') AS year, COUNT(*) AS n
        FROM x
        WHERE eff_date IS NOT NULL
        GROUP BY 1
        ORDER BY 1;
    """)
    story.append(P("Concepts by Effective Year", H2))
    story.append(TableFromRows(years, ["year","n"], widths=[1.0*inch, 1.5*inch]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true", help="include AI analysis")
    args = ap.parse_args()

    ai_obj = None
    if args.ai:
        # small, stable payload for the AI
        conn = connect()
        cov = q(conn, """
            SELECT COUNT(*) AS rows_all,
                   COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS with_target
            FROM ontology.snomed_map_icd10cm;
        """)[0]
        sizes = q(conn, """
            SELECT c.relname AS table, pg_total_relation_size(c.oid) AS size_bytes
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='ontology' AND c.relkind='r'
            ORDER BY pg_total_relation_size(c.oid) DESC
            LIMIT 3;
        """)
        from report_common import ai_analyze
        ai_obj = ai_analyze("snomed", {"coverage": cov, "largest": sizes})

    build_doc(args.out, "2ndOpinionMD — SNOMED Integrity Report", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    main()
