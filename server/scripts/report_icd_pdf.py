#!/usr/bin/env python3
import argparse
from report_common import q, connect, build_doc, TableFromRows, P, H2
from reportlab.lib.units import inch

def flow(story, content_width):
    conn = connect()

    story.append(P("Overview (via SNOMED ExtendedMap)", H2))
    cov = q(conn, """
        SELECT
          COUNT(*) AS rows_all,
          COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
          COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes
        FROM ontology.snomed_map_icd10cm;
    """)
    story.append(TableFromRows(cov, ["rows_all","rows_with_target","distinct_icd10cm_codes"], widths=[1.6*inch]*3))

    # Buckets: plain / with placeholders / invalid
    buckets = q(conn, """
        SELECT
          COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL AND map_target !~ '[X?]') AS valid_plain,
          COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL AND map_target ~  '[X?]') AS valid_with_placeholders,
          COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NULL OR map_target !~ '^[A-Z0-9]') AS truly_invalid
        FROM ontology.snomed_map_icd10cm;
    """)
    story.append(P("Validity buckets (regex-based approximation)", H2))
    story.append(TableFromRows(buckets, ["valid_plain","valid_with_placeholders","truly_invalid"], widths=[1.6*inch]*3))

    top = q(conn, """
        SELECT NULLIF(trim(map_target),'') AS icd10cm_code, COUNT(*) AS snomed_mappings
        FROM ontology.snomed_map_icd10cm
        WHERE NULLIF(trim(map_target),'') IS NOT NULL
        GROUP BY 1 ORDER BY snomed_mappings DESC, icd10cm_code LIMIT 15;
    """)
    story.append(P("Most mapped ICD-10-CM codes", H2))
    story.append(TableFromRows(top, ["icd10cm_code","snomed_mappings"], widths=[1.8*inch, 1.2*inch]))

    native = q(conn, """
        SELECT 'icd10cm' AS table, COUNT(*) AS rows FROM ontology.icd10cm
        UNION ALL
        SELECT 'icd11'   AS table, COUNT(*) AS rows FROM ontology.icd11;
    """)
    story.append(P("Native ICD tables (if present)", H2))
    story.append(TableFromRows(native, ["table","rows"], widths=[1.5*inch, 1.0*inch]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true", help="include AI analysis")
    args = ap.parse_args()

    ai_obj = None
    if args.ai:
        conn = connect()
        cov = q(conn, """
            SELECT COUNT(*) AS rows_all,
                   COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS with_target,
                   COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct
            FROM ontology.snomed_map_icd10cm;
        """)[0]
        buckets = q(conn, """
            SELECT
              COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL AND map_target !~ '[X?]') AS valid_plain,
              COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL AND map_target ~  '[X?]') AS valid_with_placeholders,
              COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NULL OR map_target !~ '^[A-Z0-9]') AS truly_invalid
            FROM ontology.snomed_map_icd10cm;
        """)[0]
        from report_common import ai_analyze
        ai_obj = ai_analyze("icd", {"coverage": cov, "buckets": buckets})

    build_doc(args.out, "ICD Integrity Report (Manual Verification)", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    main()
