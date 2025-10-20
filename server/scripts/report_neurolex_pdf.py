#!/usr/bin/env python3
import os, json
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

OUT = "db_integrity_reports/17_neurolex.pdf"
SQL = "database/sql/17_neurolex_audit.sql"

def load():
    conn = connect()
    try:
        js = q(conn, f"\copy ({open(SQL).read()}) TO STDOUT")  # not used; kept for parity
    except Exception:
        pass
    finally:
        conn.close()

    # simpler: run the file and fetch one JSON row
    conn = connect()
    try:
        row = q(conn, f"\\i {SQL}")[0]  # psql meta won't work via driver; fallback below
    except Exception:
        row = q(conn, open(SQL).read())[0]
    finally:
        conn.close()

    # row is a dict with a single key 'json' when using our SELECT jsonb_build_object ...
    audit = row.get('json', row)
    if isinstance(audit, str):
        audit = json.loads(audit)
    return audit

def verdict_from(audit):
    pres   = audit.get("presence", {})
    totals = audit.get("totals", {})
    core   = audit.get("core", {})

    if not pres.get("has_terms"):
        return "fail", "No ontology.neurolex table present."
    if int(pres.get("n_terms",0)) == 0:
        return "warn", "NeuroLex table exists but contains 0 rows."

    # Grade on the filtered core slice. PASS if core has defs and synonyms populated.
    core_terms = int(core.get("terms", 0) or 0)
    core_null_defs = int(core.get("null_definition", 0) or 0)
    core_no_syns = int(core.get("no_synonyms", 0) or 0)

    if core_terms > 0 and core_null_defs == 0 and core_no_syns == 0:
        return "pass", "Core disease-like subset has definitions and synonyms populated."
    return "warn", "Overall set includes many template/CDE entries with empty definitions/synonyms."

def main(out=OUT, use_ai=False):
    audit = load()
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
                "Grade PASS if core.terms>0 and core.null_definition=0 and core.no_synonyms=0. "
                "WARN if table empty or many NULLs; FAIL only if table missing. "
                "Return JSON only: {\"verdict\":\"pass|warn|fail\",\"rationale\":\"<=3 short sentences\",\"actions\":[\"...\",\"...\"]}"
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

        story.append(P("Core slice (used for grading)", H2))
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
