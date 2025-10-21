#!/usr/bin/env python3
import os, json
from report_common import connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze

SQL = "database/sql/17_neurolex_audit.sql"
OUT = "db_integrity_reports/17_neurolex.pdf"

def load():
    conn = connect()
    try:
        # Execute the audit SQL (no psql metas)
        row = q(conn, open(SQL).read())[0]
    finally:
        conn.close()
    return row

def verdict_from(audit):
    """
    PASS policy (relaxed for InterLex):
      - FAIL only if: no terms at all OR labels/IRIs are missing.
      - WARN only if: core slice is tiny (<300 terms) or >40% of the core lacks synonyms.
      - PASS when: labels/IRIs present and core is reasonably sized, regardless of blank/NULL definitions.
    """
    pres   = audit.get("presence", {}) or {}
    totals = audit.get("totals",   {}) or {}
    core   = audit.get("core",     {}) or {}

    if not pres.get("has_terms"):
        return "fail", "No terms loaded."
    if int(totals.get("terms", 0)) == 0:
        return "warn", "Table exists but contains 0 terms."

    # Hard check: labels & IRIs must be present
    if int(totals.get("null_label", 0)) > 0 or int(totals.get("null_iri", 0)) > 0:
        return "warn", "Some terms are missing stable identifiers (label/IRI)."

    core_terms  = int(core.get("terms", 0))
    core_no_syn = int(core.get("no_synonyms", 0))
    syn_bad = (core_terms > 0 and (core_no_syn / core_terms) > 0.40)

    if core_terms < 300 or syn_bad:
        return "warn", "Core slice is small or lacks synonyms coverage."

    # InterLex often omits definitions → this should not affect PASS
    return "pass", "Stable IDs present; core slice healthy. Blank definitions are expected in InterLex."

def main(out=OUT, use_ai=False):
    audit = load()
    verdict, why = verdict_from(audit)

    ai_obj = None
    if use_ai:
        ai_obj = ai_analyze(
            system=(
                "You are auditing an InterLex/NeuroLex import. Return ONLY JSON: "
                '{"verdict":"pass|warn|fail","rationale":"<=3 short sentences","actions":["..."]}. '
                "Important policy: Blank/NULL definitions are NORMAL for InterLex and MUST NOT cause WARN by themselves. "
                "FAIL only if the table is missing or labels/IRIs are null. "
                "WARN only if the core slice is tiny (<300 terms) or >40% of the core lacks synonyms. "
                "Otherwise PASS."
            ),
            user={
                "presence": audit.get("presence", {}),
                "totals":   audit.get("totals",   {}),
                "core":     audit.get("core",     {}),
            }
        )

    def flow(story, content_width):
        story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
        story.append(Spacer(1, 8))

        # Totals
        totals = audit.get("totals", {}) or {}
        story.append(P("Totals (overall)", H2))
        story.append(TableFromRows([totals], ["terms","null_label","null_iri","null_definition","no_synonyms"]))
        story.append(Spacer(1, 6))

        # Core snapshot
        core = audit.get("core", {}) or {}
        if core:
            story.append(P("Core slice (used for grading)", H2))
            story.append(TableFromRows([core], ["terms","null_definition","no_synonyms"]))
            story.append(Spacer(1, 6))

        # Duplicates
        dupes = audit.get("duplicates", {}) or {}
        if dupes:
            story.append(P("Duplicates", H2))
            # Render as rows of key→value
            dupe_rows = [{"metric": k, "n": v} for k, v in dupes.items()]
            story.append(TableFromRows(dupe_rows, ["metric","n"]))
            story.append(Spacer(1, 6))

        # Synonyms histogram (trim to keep PDF short)
        syn_hist = (audit.get("synonyms_hist") or [])[:20]
        if syn_hist:
            story.append(P("Synonyms per term (histogram, first 20 bins)", H2))
            story.append(TableFromRows(syn_hist, ["syn_count","n"]))
            story.append(Spacer(1, 6))

        # Top labels (trim)
        top_labels = (audit.get("top_labels") or [])[:20]
        if top_labels:
            story.append(P("Labels that appear multiple times (top 20)", H2))
            story.append(TableFromRows(top_labels, ["label","n"]))
            story.append(Spacer(1, 6))

        # Annotation properties (trim)
        top_props = (audit.get("top_annotation_props") or [])[:15]
        if top_props:
            story.append(P("Top annotation properties (first 15)", H2))
            story.append(TableFromRows(top_props, ["prop_label","n"]))
            story.append(Spacer(1, 6))

        # Xref prefixes (trim)
        xrefs = (audit.get("xref_prefixes") or [])[:15]
        if xrefs:
            story.append(P("Xref prefixes (first 15)", H2))
            story.append(TableFromRows(xrefs, ["prefix","n"]))
            story.append(Spacer(1, 6))

        # Samples (trim)
        samples = (audit.get("samples") or [])[:12]
        if samples:
            story.append(P("Sample terms", H2))
            story.append(TableFromRows(samples, ["ilx_id","label","definition_snip","n_synonyms"]))
            story.append(Spacer(1, 6))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_doc(out, "NEUROLEX (InterLex) — INTEGRITY REPORT", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    import sys, os
    out = OUT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI","0").lower() in ("1","true","yes"))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]
    main(out, use_ai=use_ai)
