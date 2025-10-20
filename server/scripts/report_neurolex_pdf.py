#!/usr/bin/env python3
import os
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

OUT = "db_integrity_reports/17_neurolex.pdf"

def load():
    conn = connect()
    try:
        presence = q(conn, """
          SELECT
            (to_regclass('ontology.neurolex') IS NOT NULL) AS has_terms,
            (to_regclass('ontology.neurolex_annotations') IS NOT NULL) AS has_ann,
            COALESCE((SELECT COUNT(*) FROM ontology.neurolex),0)::int AS n_terms,
            COALESCE((SELECT COUNT(*) FROM ontology.neurolex_annotations),0)::int AS n_ann
        """)[0]

        totals = q(conn, """
          SELECT
            COUNT(*)::int AS terms,
            COUNT(*) FILTER (WHERE label IS NULL OR label='')::int AS null_label,
            COUNT(*) FILTER (WHERE iri   IS NULL OR iri='')::int AS null_iri,
            COUNT(*) FILTER (WHERE definition IS NULL OR definition='')::int AS null_definition,
            COUNT(*) FILTER (WHERE array_length(synonyms,1) IS NULL OR array_length(synonyms,1)=0)::int AS no_synonyms
          FROM ontology.neurolex
        """)[0]

        syn_hist = q(conn, """
          SELECT COALESCE(array_length(synonyms,1),0)::int AS syn_count, COUNT(*)::int AS n
          FROM ontology.neurolex
          GROUP BY 1 ORDER BY 1
        """)

        top_labels = q(conn, """
          SELECT label, COUNT(*)::int AS n
          FROM ontology.neurolex
          GROUP BY 1 HAVING COUNT(*)>1
          ORDER BY n DESC, label LIMIT 20
        """)

        top_props = q(conn, """
          SELECT prop_label, COUNT(*)::int AS n
          FROM ontology.neurolex_annotations
          GROUP BY 1 ORDER BY n DESC, prop_label LIMIT 20
        """)

        xref_prefixes = q(conn, """
          SELECT split_part(value,':',1) AS prefix, COUNT(*)::int AS n
          FROM ontology.neurolex_annotations
          WHERE prop_label='hasDbXref' AND COALESCE(value,'')<>''
          GROUP BY 1 ORDER BY n DESC, prefix LIMIT 20
        """)

        samples = q(conn, """
          SELECT ilx_id, label,
                 COALESCE(array_length(synonyms,1),0)::int AS n_synonyms,
                 LEFT(COALESCE(definition,''),120) AS definition_snip
          FROM ontology.neurolex
          ORDER BY random() LIMIT 12
        """)

        return presence, totals, syn_hist, top_labels, top_props, xref_prefixes, samples
    finally:
        conn.close()

def verdict_from(presence, totals):
    if not presence["has_terms"]:
        return "fail", "NeuroLex term table is missing."
    if int(presence["n_terms"] or 0) == 0:
        return "warn", "NeuroLex table exists but has 0 rows."
    if int(totals.get("null_label",0))>0 or int(totals.get("null_iri",0))>0:
        return "warn", "NULLs present in required fields (label/iri)."
    return "pass", "NeuroLex terms present with basic coverage."

def main(out=OUT, use_ai=False):
    presence, totals, syn_hist, top_labels, top_props, xref_prefixes, samples = load()
    verdict, why = verdict_from(presence, totals)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": presence,
            "totals": totals,
            "synonyms_histogram_sample": syn_hist[:12],
            "top_props_sample": top_props[:10]
        }
        ai_obj = ai_analyze(
            system=("You audit a NeuroLex/InterLex import in PostgreSQL. "
                    "Return ONLY JSON like {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 sentences\","
                    "\"actions\":[\"...\"]}. Rules: fail if table missing; warn if 0 rows or key NULLs; pass otherwise."),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        story.append(P("Presence & counts", H2))
        story.append(TableFromRows([presence], ["has_terms","has_ann","n_terms","n_ann"]))
        story.append(Spacer(1, 6))

        story.append(P("Null/empty coverage", H2))
        story.append(TableFromRows([totals], ["terms","null_label","null_iri","null_definition","no_synonyms"]))
        story.append(Spacer(1, 6))

        if top_labels:
            story.append(P("Top labels (by frequency)", H2))
            story.append(TableFromRows(top_labels, ["label","n"]))
            story.append(Spacer(1, 6))

        if top_props:
            story.append(P("Top annotation properties", H2))
            story.append(TableFromRows(top_props, ["prop_label","n"]))
            story.append(Spacer(1, 6))

        if xref_prefixes:
            story.append(P("Common xref prefixes", H2))
            story.append(TableFromRows(xref_prefixes, ["prefix","n"]))
            story.append(Spacer(1, 6))

        if samples:
            story.append(P("Sample terms", H2))
            story.append(TableFromRows(samples, ["ilx_id","label","definition_snip","n_synonyms"]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "NEUROLEX (INTERLEX) — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys, os
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
