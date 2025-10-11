#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)

def flow(story, content_width):
    conn = connect()

    # ---------- LOINC ----------
    story.append(P("LOINC — Coverage & Checks", H2))
    loinc_counts = q(conn, """
        SELECT 'loinc_terms' AS what, COUNT(*)::bigint AS n FROM ontology.loinc_terms
    """)
    story.append(TableFromRows(loinc_counts, ["what","n"], widths=[2.6*inch, 1.0*inch]))

    loinc_top_classes = q(conn, """
        SELECT class, COUNT(*)::bigint AS n
        FROM ontology.loinc_terms
        GROUP BY class
        ORDER BY n DESC, class
        LIMIT 15
    """)
    if loinc_top_classes:
        story.append(P("LOINC — Top classes", H2))
        story.append(TableFromRows(loinc_top_classes, ["class","n"], widths=[3.2*inch, 1.0*inch]))

    # ---------- RxNorm ----------
    story.append(P("RxNorm — Coverage & Checks", H2))
    rxnorm_counts = q(conn, """
        SELECT * FROM (
          SELECT 'rxnorm_conso' AS what, COUNT(*)::bigint AS n FROM ontology.rxnorm_conso
          UNION ALL
          SELECT 'rxnorm_distinct_rxcui', COUNT(DISTINCT rxcui)::bigint FROM ontology.rxnorm_conso
          UNION ALL
          SELECT 'rxnorm_ndc', COUNT(*)::bigint FROM ontology.rxnorm_ndc
        ) t ORDER BY what
    """)
    story.append(TableFromRows(rxnorm_counts, ["what","n"], widths=[2.6*inch, 1.2*inch]))

    rxnorm_blank_str = q(conn, """
        SELECT 'conso_blank_str' AS what,
               COUNT(*)::bigint AS n
        FROM ontology.rxnorm_conso
        WHERE COALESCE(NULLIF(str,''), NULL) IS NULL
    """)
    story.append(TableFromRows(rxnorm_blank_str, ["what","n"], widths=[2.6*inch, 1.2*inch]))

    rxnorm_top_tty = q(conn, """
        SELECT tty, COUNT(*)::bigint AS n
        FROM ontology.rxnorm_conso
        GROUP BY tty
        ORDER BY n DESC, tty
        LIMIT 15
    """)
    if rxnorm_top_tty:
        story.append(P("RxNorm — Top TTY", H2))
        story.append(TableFromRows(rxnorm_top_tty, ["tty","n"], widths=[2.6*inch, 1.2*inch]))

    # Note: build_doc already prints a Generated timestamp in header

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true", help="include compact AI assessment block")
    args = ap.parse_args()

    ai_obj = None
    if args.ai and os.environ.get("OPENAI_API_KEY"):
        conn = connect()
        facts = {
            "loinc": {
                "counts": q(conn, "SELECT 'loinc_terms' AS what, COUNT(*) AS n FROM ontology.loinc_terms"),
                "top_classes": q(conn, """
                    SELECT class, COUNT(*) AS n
                    FROM ontology.loinc_terms
                    GROUP BY class
                    ORDER BY n DESC, class
                    LIMIT 10
                """),
            },
            "rxnorm": {
                "counts": q(conn, """
                    SELECT * FROM (
                      SELECT 'rxnorm_conso' AS what, COUNT(*) AS n FROM ontology.rxnorm_conso
                      UNION ALL
                      SELECT 'rxnorm_distinct_rxcui', COUNT(DISTINCT rxcui) FROM ontology.rxnorm_conso
                      UNION ALL
                      SELECT 'rxnorm_ndc', COUNT(*) AS n FROM ontology.rxnorm_ndc
                    ) t ORDER BY what
                """),
                "blank_str": q(conn, """
                    SELECT COUNT(*) AS n_blank
                    FROM ontology.rxnorm_conso
                    WHERE COALESCE(NULLIF(str,''), NULL) IS NULL
                """),
                "top_tty": q(conn, """
                    SELECT tty, COUNT(*) AS n
                    FROM ontology.rxnorm_conso
                    GROUP BY tty
                    ORDER BY n DESC, tty
                    LIMIT 10
                """),
            }
        }
        ai_obj = ai_analyze(
            system=("You are auditing LOINC and RxNorm loads in a Postgres DB. "
                    "Return only JSON: {\"verdict\":\"pass|warn|fail|info\",\"rationale\":\"<=3 sentences\"}. "
                    "Consider: table presence, counts plausibility, blank strings, categorical skew, etc."),
            user=facts
        )

    build_doc(
        args.out,
        "2ndOpinionMD — LOINC & RxNorm Integrity Report",
        subtitle=None,
        build_flow=flow,
        ai_obj=ai_obj
    )

if __name__ == "__main__":
    main()

