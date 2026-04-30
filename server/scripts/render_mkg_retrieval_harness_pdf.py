#!/usr/bin/env python3
"""Render an ``mkg_retrieval_harness.py`` JSON receipt into one PDF report.

Supports:

- **Batch** artifacts: ``{ "batch": {...}, "runs": [ {...}, ... ] }``
- **Single-query** mode JSON (the inner ``run_query`` object).

Usage:

    python server/scripts/render_mkg_retrieval_harness_pdf.py \\
        receipts/MKG_RETRIEVAL_HARNESS_RUN_<stamp>.json

    python server/scripts/render_mkg_retrieval_harness_pdf.py \\
        --in receipts/run.json --out receipts/run_report.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


def _escape(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        leading=11,
        spaceAfter=3,
        fontSize=9,
    )
    mono = ParagraphStyle(
        "Mono",
        parent=base["Code"],
        leading=10,
        spaceAfter=3,
        fontSize=7.5,
        textColor=HexColor("#222222"),
    )
    return {
        "title": base["Title"],
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontSize=16, spaceAfter=8),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
            textColor=HexColor("#1f3a93"),
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=4,
            textColor=HexColor("#34495e"),
        ),
        "body": body,
        "mono": mono,
    }


def _md_to_paragraphs(text: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    if not text or not str(text).strip():
        out.append(Paragraph("<i>(empty)</i>", styles["body"]))
        return out
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            out.append(Spacer(1, 4))
            continue
        if line.startswith("### "):
            out.append(Paragraph(_escape(line[4:]), styles["h3"]))
        elif line.startswith("## "):
            out.append(Paragraph(_escape(line[3:]), styles["h2"]))
        elif line.startswith("# "):
            out.append(Paragraph(_escape(line[2:]), styles["h1"]))
        elif line.startswith("|") and "|" in line[1:]:
            out.append(Paragraph(_escape(line), styles["body"]))
        elif line.startswith("- ") or line.startswith("* "):
            out.append(Paragraph("&bull; " + _escape(line[2:]), styles["body"]))
        else:
            out.append(Paragraph(_escape(line), styles["body"]))
    return out


def _kv_table(rows: List[List[str]], key_width: float = 118, val_width: float = 390) -> Table:
    styles_bt = getSampleStyleSheet()
    safe_rows = [[Paragraph(_escape(c), styles_bt["BodyText"]) for c in r] for r in rows]
    t = Table(safe_rows, colWidths=[key_width, val_width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#ecf0f1")),
                ("BOX", (0, 0), (-1, -1), 0.35, HexColor("#bdc3c7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, HexColor("#dce4ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def _hits_table(
    hits: List[Dict[str, Any]],
    *,
    label: str,
    styles: Dict[str, ParagraphStyle],
    max_rows: int,
    text_max: int,
) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph(_escape(label), styles["h3"]))
    if not hits:
        out.append(Paragraph("<i>(none)</i>", styles["body"]))
        return out

    header = ["id", "source", "score", "title"]
    rows_h: List[List[str]] = [header]
    for h in hits[:max_rows]:
        snippet = (h.get("title") or "")[:text_max].replace("\n", " ")
        score = h.get("score")
        sc = f"{float(score):.4f}" if isinstance(score, (int, float)) else str(score or "")
        rows_h.append([str(h.get("id") or ""), str(h.get("source") or ""), sc, snippet])

    styles_bt = getSampleStyleSheet()
    safe = [[Paragraph(_escape(c), styles_bt["BodyText"]) for c in r] for r in rows_h]
    tbl = Table(safe, colWidths=[72, 90, 52, 300])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.35, HexColor("#7f8c8d")),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, HexColor("#bdc3c7")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f7f9fa")]),
            ]
        )
    )
    out.append(tbl)
    if len(hits) > max_rows:
        out.append(
            Paragraph(
                _escape(f"… plus {len(hits) - max_rows} more hits (truncated for PDF)."),
                styles["body"],
            )
        )
    return out


def _sources_modules_tables(plan: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    sel_src = plan.get("selected_sources") or []
    if isinstance(sel_src, list) and sel_src:
        rows = [["priority", "source", "why"]]
        for item in sel_src:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    str(item.get("priority") or ""),
                    str(item.get("source") or ""),
                    str(item.get("why") or "")[:380],
                ]
            )
        styles_bt = getSampleStyleSheet()
        safe = [[Paragraph(_escape(c), styles_bt["BodyText"]) for c in r] for r in rows]
        t = Table(safe, colWidths=[46, 120, 350])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.3, HexColor("#bdc3c7")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.15, HexColor("#dce4ec")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ]
            )
        )
        out.append(Paragraph("Router selected_sources", styles["h3"]))
        out.append(t)
        out.append(Spacer(1, 6))

    mods = plan.get("selected_modules") or []
    if isinstance(mods, list) and mods:
        rows_m = [["priority", "module_id", "why"]]
        for item in mods:
            if not isinstance(item, dict):
                continue
            rows_m.append(
                [
                    str(item.get("priority") or ""),
                    str(item.get("module_id") or ""),
                    str(item.get("why") or "")[:380],
                ]
            )
        styles_bt = getSampleStyleSheet()
        safe_m = [[Paragraph(_escape(c), styles_bt["BodyText"]) for c in r] for r in rows_m]
        tm = Table(safe_m, colWidths=[46, 46, 424])
        tm.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.3, HexColor("#bdc3c7")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.15, HexColor("#dce4ec")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ]
            )
        )
        out.append(Paragraph("Router selected_modules", styles["h3"]))
        out.append(tm)
        out.append(Spacer(1, 6))

    return out


def _id_preview(xs: Any, limit: int = 28) -> str:
    if not isinstance(xs, list):
        return ""
    head = [str(x) for x in xs[:limit]]
    more = len(xs) - limit if len(xs) > limit else 0
    s = ", ".join(head)
    if more > 0:
        s += f" (+ {more} more)"
    return s


def _render_overlap(overlap: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph("Lane overlap", styles["h2"]))
    jac = overlap.get("jaccard")
    rows = [
        ["jaccard", "" if jac is None else str(jac)],
        ["semantic_only ids", _id_preview(overlap.get("semantic_only"))],
        ["ts_only ids", _id_preview(overlap.get("ts_only"))],
        ["both ids", _id_preview(overlap.get("both"))],
    ]
    out.append(_kv_table(rows))
    return out


def _render_llm(llm: Any, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph("LLM synthesis", styles["h2"]))
    if not isinstance(llm, dict):
        out.append(Paragraph(_escape(str(llm)), styles["body"]))
        return out
    if llm.get("error"):
        out.append(Paragraph("<b>Error:</b> " + _escape(str(llm.get("error"))), styles["body"]))
        return out

    if llm.get("mode") == "two_pass":
        out.append(
            _kv_table(
                [
                    ["compress_model", str((llm.get("compress_pass") or {}).get("model") or "")],
                    ["compress_elapsed_sec", str((llm.get("compress_pass") or {}).get("elapsed_sec") or "")],
                    ["synth_model", str((llm.get("synth_pass") or {}).get("model") or "")],
                    ["synth_elapsed_sec", str((llm.get("synth_pass") or {}).get("elapsed_sec") or "")],
                ]
            )
        )
        out.append(Spacer(1, 6))
        cp = llm.get("compress_pass") or {}
        summ = str(cp.get("summary") or "")[:6000]
        if summ.strip():
            out.append(Paragraph("Compression summary", styles["h3"]))
            out.extend(_md_to_paragraphs(summ, styles))
        sp = llm.get("synth_pass") or {}
        md = str(sp.get("markdown") or "").strip()
        if md:
            out.append(Paragraph("Final synthesis (markdown)", styles["h3"]))
            out.extend(_md_to_paragraphs(md, styles))
        return out

    out.append(
        _kv_table(
            [
                ["model", str(llm.get("model") or "")],
                ["elapsed_sec", str(llm.get("elapsed_sec") or "")],
                ["had_extra_context", str(llm.get("had_extra_context"))],
            ]
        )
    )
    out.append(Spacer(1, 6))
    md = str(llm.get("markdown") or "").strip()
    if md:
        out.extend(_md_to_paragraphs(md, styles))
    else:
        out.append(Paragraph("<i>(no markdown)</i>", styles["body"]))
    return out


def _normalize_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if isinstance(data.get("runs"), list):
        return dict(data.get("batch") or {}), list(data["runs"])
    return {}, [data]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def build_pdf(
    harness_json: Path,
    out_pdf: Path,
    *,
    max_hit_rows: int,
    hit_title_max: int,
) -> None:
    raw = _load_json(harness_json)
    batch, runs = _normalize_payload(raw)
    if not runs:
        raise ValueError("No runs found: expected batch.runs[] or a single run_query object.")
    styles = _styles()
    story: List[Any] = []

    story.append(Paragraph("MKG retrieval harness — report", styles["title"]))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            _escape(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}"),
            styles["body"],
        )
    )
    story.append(Paragraph(_escape(f"Source JSON: {harness_json.name}"), styles["body"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Batch / run metadata", styles["h2"]))
    story.append(
        _kv_table(
            [
                ["n_questions", str(batch.get("n_questions") or len(runs))],
                ["elapsed_sec", str(batch.get("elapsed_sec") or "")],
                ["model", str(batch.get("model") or "")],
                ["synth_model", str(batch.get("synth_model") or "")],
                ["router_model", str(batch.get("router_model") or "")],
                ["use_router", str(batch.get("use_router"))],
                ["two_pass_synth", str(batch.get("two_pass_synth"))],
                ["embed_model", str(batch.get("embed_model") or "")],
            ]
        )
    )
    story.append(
        Paragraph(
            _escape(
                "Sections below include router_plan (EoH modules + pilot sources), retrieval hits, "
                "overlap, and LLM synthesis. Full pilot_slice_source_reference prose stays in the JSON file."
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 8))

    for i, row in enumerate(runs):
        if i > 0:
            story.append(PageBreak())
        idx = row.get("batch_index") or (i + 1)
        q = str(row.get("query") or "")
        story.append(Paragraph(_escape(f"Query {idx} / {len(runs)}"), styles["h1"]))
        story.append(Paragraph(_escape(q[:8000]), styles["body"]))
        story.append(Spacer(1, 6))

        story.append(Paragraph("Run timing & retrieval", styles["h2"]))
        story.append(
            _kv_table(
                [
                    ["top_k", str(row.get("top_k") or "")],
                    ["sources_filter", str(row.get("sources_filter") or "(none)")],
                    ["embed_device", str(row.get("embed_device") or "")],
                    ["embed_sec", str(row.get("embed_sec") or "")],
                    ["db_sec", str(row.get("db_sec") or "")],
                    ["ts_strategy", str(row.get("ts_strategy") or "")],
                    ["elapsed_sec", str(row.get("elapsed_sec") or "")],
                    ["batch_elapsed_sec", str(row.get("batch_elapsed_sec") or "")],
                ]
            )
        )
        et = row.get("embed_text")
        if et:
            story.append(Spacer(1, 4))
            story.append(Paragraph("embed_text (router-expanded semantic text)", styles["h3"]))
            story.append(Preformatted(str(et)[:8000], styles["mono"]))

        ts_used = row.get("ts_terms_used")
        if ts_used:
            story.append(Spacer(1, 4))
            story.append(Paragraph("ts_terms_used", styles["h3"]))
            story.append(Paragraph(_escape(_fmt_join(ts_used)), styles["body"]))

        plan = row.get("router_plan") if isinstance(row.get("router_plan"), dict) else {}
        if plan:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Source-router plan", styles["h2"]))
            story.append(
                _kv_table(
                    [
                        ["model", str(plan.get("model") or "")],
                        ["elapsed_sec", str(plan.get("elapsed_sec") or "")],
                        ["question_type", str(plan.get("question_type") or "")],
                        ["semantic_query", str(plan.get("semantic_query") or "")[:6000]],
                        ["ts_query", str(plan.get("ts_query") or "")[:2000]],
                        ["ts_terms", _fmt_join(plan.get("ts_terms"))],
                        ["notes", str(plan.get("notes") or "")[:2000]],
                    ]
                )
            )
            story.extend(_sources_modules_tables(plan, styles))

        eff = row.get("effective_sources")
        if eff is not None:
            story.append(Paragraph("effective_sources", styles["h3"]))
            story.append(Paragraph(_escape(_fmt_join(eff)), styles["body"]))

        sem = row.get("semantic_hits") if isinstance(row.get("semantic_hits"), list) else []
        ts_h = row.get("ts_hits") if isinstance(row.get("ts_hits"), list) else []
        story.append(Spacer(1, 6))
        story.extend(_hits_table(sem, label="Semantic hits", styles=styles, max_rows=max_hit_rows, text_max=hit_title_max))
        story.append(Spacer(1, 4))
        story.extend(_hits_table(ts_h, label="TS (FTS) hits", styles=styles, max_rows=max_hit_rows, text_max=hit_title_max))

        ov = row.get("overlap") if isinstance(row.get("overlap"), dict) else {}
        if ov:
            story.append(Spacer(1, 6))
            story.extend(_render_overlap(ov, styles))

        llm = row.get("llm")
        if llm is not None:
            story.append(Spacer(1, 6))
            story.extend(_render_llm(llm, styles))
        else:
            story.append(Spacer(1, 6))
            story.append(Paragraph("LLM synthesis", styles["h2"]))
            story.append(Paragraph("<i>(skipped — --no-llm or missing llm block)</i>", styles["body"]))

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=44,
        bottomMargin=44,
        title="MKG retrieval harness report",
        author="2OPMD MKG harness",
    )
    doc.build(story)


def _fmt_join(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(x) for x in val)
    return str(val)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json_path", nargs="?", type=Path, help="Path to MKG harness JSON (batch or single-query).")
    ap.add_argument("--in", dest="in_path", type=Path, help="Explicit input JSON path.")
    ap.add_argument("--out", type=Path, default=None, help="Output PDF path (default: <stem>_report.pdf beside JSON).")
    ap.add_argument("--max-hit-rows", type=int, default=12, help="Max rows per hits table per lane.")
    ap.add_argument("--hit-title-max", type=int, default=240, help="Max chars for hit title column.")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    path = args.in_path or args.json_path
    if path is None:
        print("error: pass JSON path as positional or --in", file=sys.stderr)
        return 2
    path = path.expanduser().resolve()
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    out = args.out
    if out is None:
        out = path.with_name(path.stem + "_report.pdf")
    else:
        out = out.expanduser().resolve()

    try:
        build_pdf(path, out, max_hit_rows=max(1, args.max_hit_rows), hit_title_max=max(80, args.hit_title_max))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())