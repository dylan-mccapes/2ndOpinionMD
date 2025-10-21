#!/usr/bin/env python3
import os, json
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

OUT = "db_integrity_reports/17_neurolex.pdf"
SQL = "database/sql/17_neurolex_audit.sql"

def _run_audit_sql():
    sql_text = open(SQL, "r", encoding="utf-8").read()
    conn = connect()
    try:
        rows = q(conn, sql_text)
    finally:
        conn.close()
    if not rows:
        return {}
    row = rows[0]
    # row is usually {'json': '<json text>'} or {'?column?': '<json text>'}
    if isinstance(row, dict):
        val = next(iter(row.values()))
    else:
        val = row
    return json.loads(val) if isinstance(val, str) else val

def verdict_from(audit):
    pres   = audit.get("presence", {})
    totals = audit.get("totals", {})
    core   = audit.get("core", {})

    if not pres.get("has_terms"):
        return "fail", "No ontology.neurolex table present."
    if int(pres.get("n_terms", 0) or 0) == 0:
        return "warn", "NeuroLex table exists but contains 0 rows."

    # PASS rubric (pragmatic for InterLex):
    # - overall has labels & IRIs (no nulls)
    # - core slice exists (non-zero terms)
    # Definitions may be blank for many InterLex terms; that's expected.
    ok_labels = int(totals.get("null_label", 0) or 0) == 0
    ok_iris   = int(totals.get("null_iri",   0) or 0) == 0
    core_n    = int(core.get("terms",        0) or 0)

    if ok_labels and ok_iris and core_n > 0:
        return "pass", "Terms present with stable IDs; core slice available. Blank definitions are expected for many InterLex terms."

    return "warn", "Table present but some identifiers or core coverage are insufficient."

def main(out=OUT, use_ai=False):
    audit = _run_audit_sql()
    verdict, why = verdict_from(audit)

    ai_obj = None
    if use_ai:
        facts = {
            "presence": audit.get("presence"),
            "overall": audit.get("totals"),
            "core": audit.get("core"),
        }
        ai_obj = ai_analyze(
            system=(
                "You audit NeuroLex (InterLex subset). "
                "PASS if totals.null_label=0 AND totals.null_iri=0 AND core.terms>0. "
                "WARN if table empty or identifiers missing; FAIL if table missing. "
                "Return ONLY JSON like "
                "{\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\",\"actions\":[\"...\",\"...\"]}."
            ),
            user=facts
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Presence
        pres = audit.get("presence", {})
        story.append(P("Presence & counts", H2))
        story.append(TableFromRows(
            [(pres.get("has_terms"), pres.get("has_ann"), pres.get("n_terms"), pres.get("n_ann"))],
            ["has_terms","has_ann","n_terms","n_ann"]
        ))
        story.append(Spacer(1, 6))

        # Overall vs Core
        tot = audit.get("totals", {})
        core = audit.get("core", {})
        story.append(P("Null/empty coverage — OVERALL", H2))
        story.append(TableFromRows([(
            tot.get("terms"), tot.get("null_label"), tot.get("null_iri"),
            tot.get("null_definition"), tot.get("no_synonyms")
        )], ["terms","null_label","null_iri","null_definition","no_synonyms"]))
        story.append(Spacer(1, 6))

        story.append(P("Core slice (used for readiness check)", H2))
        story.append(TableFromRows([(
            core.get("terms"), core.get("null_definition"), core.get("no_synonyms")
        )], ["terms","null_definition","no_synonyms"]))
        story.append(Spacer(1, 6))

        # A few quick tables
        if audit.get("top_labels"):
            story.append(P("Top labels (by frequency)", H2))
            story.append(TableFromRows(
                [(x["label"], x["n"]) for x in audit["top_labels"]], ["label","n"]
            ))
            story.append(Spacer(1, 6))

        if audit.get("top_annotation_props"):
            story.append(P("Top annotation properties", H2))
            story.append(TableFromRows(
                [(x["prop_label"], x["n"]) for x in audit["top_annotation_props"]], ["prop_label","n"]
            ))
            story.append(Spacer(1, 6))

        if audit.get("xref_prefixes"):
            story.append(P("Common xref prefixes", H2))
            story.append(TableFromRows(
                [(x["prefix"], x["n"]) for x in audit["xref_prefixes"]], ["prefix","n"]
            ))
            story.append(Spacer(1, 6))

        if audit.get("samples"):
            story.append(P("Sample terms", H2))
            story.append(TableFromRows(
                [(x["ilx_id"], x["label"], x["definition_snip"], x["n_synonyms"]) for x in audit["samples"]],
                ["ilx_id","label","definition_snip","n_synonyms"]
            ))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "NEUROLEX (INTERLEX) — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
