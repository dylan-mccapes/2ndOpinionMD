#!/usr/bin/env python3
"""
PanelApp Integrity / Audit PDF

- Verdict rules:
  * FAIL if table missing
  * WARN if table present but 0 rows
  * WARN if critical blanks >5% (critical = gene_symbol + confidence_level)
  * PASS otherwise

- Optional AI verdict: set env AI=1 or pass --ai (requires OPENAI_API_KEY).
- Safe with or without the materialized view molecular.v_gene_panels_latest.
"""

import os
import sys
from datetime import date

from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT_DEFAULT = "db_integrity_reports/12_panelapp.pdf"


# ---------- Helpers ----------

def prescreen(conn):
    """Check table / MV presence + quick row count."""
    # has_table and has_mv are bool-like; rows may be 0 if empty
    row = q(conn, """
      SELECT
        (to_regclass('molecular.gene_panels') IS NOT NULL) AS has_table,
        COALESCE((SELECT COUNT(*) FROM molecular.gene_panels), 0) AS rows,
        (to_regclass('molecular.v_gene_panels_latest') IS NOT NULL) AS has_mv
    """)[0]
    return row


def refresh_mv_if_present(conn):
    """Refresh MV if it exists; ignore errors if any."""
    try:
        mv = q(conn, "SELECT to_regclass('molecular.v_gene_panels_latest') AS mv")[0]["mv"]
        if mv:
            q(conn, "REFRESH MATERIALIZED VIEW CONCURRENTLY molecular.v_gene_panels_latest;")
    except Exception:
        # best-effort only
        pass


def load(conn):
    """
    Load all data slices the report needs.
    Returns a tuple used directly by main().
    """
    pres = prescreen(conn)

    # Early return when table missing
    if not pres["has_table"]:
        return pres, {}, [], [], [], [], [], [], [], {}, [], {}, []

    refresh_mv_if_present(conn)

    core = q(conn, """
      SELECT
        COUNT(*)::bigint AS rows,
        COUNT(DISTINCT (panel_id, panel_version))::bigint AS unique_panels,
        COUNT(DISTINCT gene_symbol)::bigint AS unique_genes
      FROM molecular.gene_panels
    """)[0]

    # If empty, compute just what we can and bail early to keep report slim
    if int(core["rows"]) == 0:
        fts = q(conn, """
          SELECT
            EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema='molecular' AND table_name='gene_panels' AND column_name='ts'
            ) AS has_ts
        """)[0]
        idx = q(conn, """
          SELECT indexname
          FROM pg_indexes
          WHERE schemaname='molecular' AND tablename='gene_panels'
          ORDER BY indexname
        """)
        # hygiene still computed against 0 rows
        hygiene = {"blank_gene_symbol": 0, "blank_confidence": 0, "blank_moi": 0}
        return pres, core, [], [], [], [], [], [], [], fts, idx, hygiene, []

    by_panel = q(conn, """
      SELECT panel_id, panel_name, panel_version, COUNT(*)::bigint AS genes
      FROM molecular.gene_panels
      GROUP BY 1,2,3
      ORDER BY genes DESC NULLS LAST, panel_name
      LIMIT 20
    """)

    by_source = q(conn, """
      SELECT source_instance, COUNT(*)::bigint AS n
      FROM molecular.gene_panels
      GROUP BY 1 ORDER BY 2 DESC
    """)

    by_signedoff = q(conn, """
      SELECT signed_off, COUNT(*)::bigint AS n
      FROM molecular.gene_panels
      GROUP BY 1 ORDER BY 2 DESC
    """)

    # Map numeric/text confidence to human labels
    conf_dist = q(conn, """
      SELECT
        CASE
          WHEN confidence_level IN ('3','High','Green') THEN 'Green'
          WHEN confidence_level IN ('2','Moderate','Amber') THEN 'Amber'
          WHEN confidence_level IN ('1','Low','Red') THEN 'Red'
          WHEN confidence_level IN ('0') THEN 'Unknown/0'
          ELSE COALESCE(NULLIF(confidence_level,''),'(blank)')
        END AS level,
        COUNT(*)::bigint AS n
      FROM molecular.gene_panels
      GROUP BY 1
      ORDER BY 2 DESC
    """)

    moi_dist = q(conn, """
      SELECT COALESCE(NULLIF(mode_of_inheritance,''),'(blank)') AS moi, COUNT(*)::bigint AS n
      FROM molecular.gene_panels
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 20
    """)

    recent = q(conn, """
      SELECT panel_id, panel_name, panel_version, (imported_at::date) AS imported_date,
             COUNT(*)::bigint AS genes
      FROM molecular.gene_panels
      GROUP BY 1,2,3,4
      ORDER BY imported_date DESC NULLS LAST
      LIMIT 20
    """)

    examples = q(conn, """
      SELECT panel_name, panel_version, gene_symbol, confidence_level, mode_of_inheritance
      FROM molecular.gene_panels
      LIMIT 20
    """)

    fts = q(conn, """
      SELECT
        EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_schema='molecular' AND table_name='gene_panels' AND column_name='ts'
        ) AS has_ts
    """)[0]

    idx = q(conn, """
      SELECT indexname
      FROM pg_indexes
      WHERE schemaname='molecular' AND tablename='gene_panels'
      ORDER BY indexname
    """)

    hygiene = q(conn, """
      SELECT
        COUNT(*) FILTER (WHERE COALESCE(NULLIF(gene_symbol,''),NULL) IS NULL)     AS blank_gene_symbol,
        COUNT(*) FILTER (WHERE COALESCE(NULLIF(confidence_level::text,''),NULL) IS NULL) AS blank_confidence,
        COUNT(*) FILTER (WHERE COALESCE(NULLIF(mode_of_inheritance,''),NULL) IS NULL)     AS blank_moi
      FROM molecular.gene_panels
    """)[0]

    latest = []
    if pres["has_mv"]:
        latest = q(conn, """
          SELECT panel_id, panel_name, panel_version, COUNT(*)::bigint AS genes
          FROM molecular.v_gene_panels_latest
          GROUP BY 1,2,3
          ORDER BY genes DESC NULLS LAST, panel_name
          LIMIT 20
        """)

    return pres, core, by_panel, by_source, by_signedoff, conf_dist, moi_dist, recent, examples, fts, idx, hygiene, latest


def verdict_from(pres, core, hygiene):
    """Return ('pass'|'warn'|'fail', reason)."""
    if not pres.get("has_table"):
        return "fail", "PanelApp table not found."

    rows = int((core or {}).get("rows", 0) or 0)

    if rows == 0:
        return "warn", "Table exists but contains 0 rows."

    # Critical blanks: gene_symbol + confidence_level
    blank_gene = int((hygiene or {}).get("blank_gene_symbol", 0) or 0)
    blank_conf = int((hygiene or {}).get("blank_confidence", 0) or 0)
    crit_blank_rate = (blank_gene + blank_conf) / max(rows, 1)

    if crit_blank_rate > 0.05:
        return "warn", f"Critical blanks >5% (gene_symbol + confidence_level = {crit_blank_rate:.1%})."

    return "pass", "PanelApp gene panels present and healthy."


# ---------- Main ----------

def main():
    out = OUT_DEFAULT
    use_ai = ("--ai" in sys.argv) or (os.getenv("AI", "0").lower() in ("1", "true", "yes"))
    if "--out" in sys.argv:
        try:
            out = sys.argv[sys.argv.index("--out") + 1]
        except Exception:
            pass

    conn = connect()
    try:
        (pres, core, by_panel, by_source, by_signedoff, conf_dist, moi_dist,
         recent, examples, fts, idx, hygiene, latest) = load(conn)

        verdict, why = verdict_from(pres, core, hygiene)

        # AI verdict (optional) — mirrors the same rules as above
        ai_obj = None
        if use_ai:
            rows = int((core or {}).get("rows", 0) or 0)
            blank_gene = int((hygiene or {}).get("blank_gene_symbol", 0) or 0)
            blank_conf = int((hygiene or {}).get("blank_confidence", 0) or 0)
            crit_blank_rate = (blank_gene + blank_conf) / max(rows, 1) if rows else 0.0

            # derive small, high-signal summaries for the AI
            conf_total = sum(x["n"] for x in conf_dist) if conf_dist else 0
            conf_pct = {x["level"]: (x["n"] / conf_total if conf_total else 0.0) for x in conf_dist}
            moi_unknown = next((x["n"] for x in moi_dist if x["moi"] in ("Unknown", "(blank)")), 0)
            moi_unknown_rate = moi_unknown / max(rows, 1) if rows else 0.0

            # top panel (by genes) if available
            top_panel = None
            src_for_top = (latest or by_panel)
            if src_for_top:
                t = src_for_top[0]
                top_panel = {
                    "panel_name": t.get("panel_name"),
                    "panel_version": t.get("panel_version"),
                    "genes": int(t.get("genes") or 0)
                }

            ai_obj = ai_analyze(
                system=(
                    "You are auditing imported PanelApp data. "
                    "Output ONLY JSON like "
                    "{\"verdict\":\"pass|warn|fail\","
                    "\"rationale\":\"<=3 short sentences\","
                    "\"insights\":[\"bullet1\",\"bullet2\",...],"
                    "\"actions\":[\"short next step\",...]}."
                    "Rules: fail if table missing; warn if rows==0; otherwise pass unless "
                    "critical_blank_rate>0.05 (critical fields are gene_symbol and confidence_level). "
                    "When passing, still include 3–6 specific insights using the stats supplied."
                ),
                user={
                    "has_table": bool(pres.get("has_table")),
                    "rows": rows,
                    "unique_panels": int((core or {}).get("unique_panels", 0) or 0),
                    "unique_genes": int((core or {}).get("unique_genes", 0) or 0),
                    "critical_blank_rate": crit_blank_rate,
                    "confidence_pct": conf_pct,
                    "moi_unknown_rate": moi_unknown_rate,
                    "signed_off_counts": by_signedoff,
                    "source_counts": by_source,
                    "top_panel": top_panel,
                    "recent_count": len(recent or []),
                }
            )


        # If table missing or empty, build a short PDF and exit early
        if not pres["has_table"] or int((core or {}).get("rows", 0) or 0) == 0:
            def flow_empty(story, content_width):
                story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
                story.append(Spacer(1, 8))
                if pres["has_table"]:
                    story.append(P("Table is present but empty. No distributions or samples to display.", H2))
                else:
                    story.append(P("Schema ‘molecular.gene_panels’ is missing.", H2))

            os.makedirs(os.path.dirname(out), exist_ok=True)
            title = f"PanelApp — INTEGRITY REPORT ({date.today().isoformat()})"
            build_doc(out, title, None, flow_empty, ai_obj=ai_obj)
            print(f"Wrote {out}")
            return

        # Normal full report flow
        def flow(story, content_width):
            story.append(P(f"Verdict: {verdict.upper()} — {why}", BODY))
            story.append(Spacer(1, 8))

            story.append(P("Core counts", H2))
            story.append(TableFromRows([core], ["rows", "unique_panels", "unique_genes"]))
            story.append(Spacer(1, 8))

            story.append(P("Source instances", H2))
            story.append(TableFromRows(by_source, ["source_instance", "n"]))
            story.append(Spacer(1, 8))

            story.append(P("Signed-off distribution", H2))
            story.append(TableFromRows(by_signedoff, ["signed_off", "n"]))
            story.append(Spacer(1, 8))

            story.append(P("Confidence level distribution", H2))
            story.append(TableFromRows(conf_dist, ["level", "n"]))
            story.append(Spacer(1, 8))

            story.append(P("Mode of inheritance (top)", H2))
            story.append(TableFromRows(moi_dist, ["moi", "n"]))
            story.append(Spacer(1, 8))

            if latest:
                story.append(P("Top panels by gene count (latest per panel)", H2))
                story.append(TableFromRows(latest, ["panel_id", "panel_name", "panel_version", "genes"]))
            else:
                story.append(P("Top panels by gene count", H2))
                story.append(TableFromRows(by_panel, ["panel_id", "panel_name", "panel_version", "genes"]))
            story.append(Spacer(1, 8))

            story.append(P("Recently imported panels", H2))
            story.append(TableFromRows(recent, ["panel_id", "panel_name", "panel_version", "imported_date", "genes"]))
            story.append(Spacer(1, 8))

            story.append(P("Sample records", H2))
            story.append(TableFromRows(examples, ["panel_name", "panel_version", "gene_symbol", "confidence_level", "mode_of_inheritance"]))
            story.append(Spacer(1, 8))

            story.append(P("Schema & Indexes", H2))
            story.append(TableFromRows([fts], ["has_ts"]))
            story.append(TableFromRows(idx, ["indexname"]))

        os.makedirs(os.path.dirname(out), exist_ok=True)
        title = f"PanelApp — INTEGRITY REPORT ({date.today().isoformat()})"
        build_doc(out, title, None, flow, ai_obj=ai_obj)
        print(f"Wrote {out}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
