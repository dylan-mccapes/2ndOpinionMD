#!/usr/bin/env python3
"""Render a FORWARD 3-agent PTV harness JSON receipt into a single PDF report.

Layout per patient::

    1. Header (patient code, phenotype, headline, graph metadata)
    2. Original question
    3. Stage A — probe (model, tools, plan, answer, top events with weights)
    4. Stage B — gap (model, tools, plan, answer, gaps closed)
    5. Stage C — curated bundle (union working_set, top curated events)
    6. Stage D — PTV synthesis markdown
    7. Stage E — MKG overall synthesis (router plan, lane hits, final answer)
    8. Page break

The receipt path is taken from ``--receipt``; the PDF is written to ``--out``.
The harness invokes this script automatically after writing the receipt JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _escape(s: str) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        leading=12,
        spaceAfter=4,
        fontSize=9.5,
    )
    mono = ParagraphStyle(
        "Mono",
        parent=base["Code"],
        leading=11,
        spaceAfter=4,
        fontSize=8.5,
        textColor=HexColor("#222222"),
    )
    section = ParagraphStyle(
        "Section",
        parent=base["Heading2"],
        spaceBefore=8,
        spaceAfter=4,
        textColor=HexColor("#1f3a93"),
    )
    sub = ParagraphStyle(
        "Sub",
        parent=base["Heading3"],
        spaceBefore=4,
        spaceAfter=2,
        textColor=HexColor("#34495e"),
    )
    return {
        "title": base["Title"],
        "h1": base["Heading1"],
        "h2": section,
        "h3": sub,
        "body": body,
        "mono": mono,
        "italic": ParagraphStyle("Italic", parent=body, fontName="Helvetica-Oblique"),
    }


def _md_to_paragraphs(text: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    if not text:
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
        elif line.startswith("- ") or line.startswith("* "):
            out.append(Paragraph("&bull; " + _escape(line[2:]), styles["body"]))
        else:
            out.append(Paragraph(_escape(line), styles["body"]))
    return out


def _kv_table(rows: List[List[str]]) -> Table:
    safe_rows = [[Paragraph(_escape(c), getSampleStyleSheet()["BodyText"]) for c in r] for r in rows]
    t = Table(safe_rows, colWidths=[120, 360])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#ecf0f1")),
                ("BOX", (0, 0), (-1, -1), 0.4, HexColor("#bdc3c7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#bdc3c7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _events_table(events: List[Dict[str, Any]], max_rows: int = 12) -> Table:
    header = ["event_id", "type", "date", "weight", "title / one_line"]
    rows: List[List[str]] = [header]
    for ev in events[:max_rows]:
        title = ev.get("card_title") or ev.get("card_one_line") or ev.get("title") or ""
        rows.append(
            [
                str(ev.get("event_id") or ""),
                str(ev.get("event_type") or ev.get("type") or ""),
                str(ev.get("timestamp") or ev.get("date") or ""),
                str(ev.get("probe_weight") or ev.get("weight") or ""),
                title[:140],
            ]
        )
    styles = getSampleStyleSheet()
    safe = [[Paragraph(_escape(c), styles["BodyText"]) for c in r] for r in rows]
    t = Table(safe, colWidths=[110, 70, 65, 40, 200])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.4, HexColor("#7f8c8d")),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, HexColor("#bdc3c7")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f7f9fa")]),
            ]
        )
    )
    return t


def _render_stage_probe_or_gap(
    stage_label: str,
    stage: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph(_escape(stage_label), styles["h2"]))
    out.append(
        _kv_table(
            [
                ["Model", str(stage.get("model") or "")],
                ["Elapsed (s)", str(stage.get("elapsed_sec") or "")],
                ["Tools used", ", ".join(((stage.get("agent_log") or {}).get("tools_used") or [])) or "(none)"],
                ["Reason stopped", str((stage.get("agent_log") or {}).get("reason_stopped") or "")],
            ]
        )
    )
    out.append(Spacer(1, 6))

    plan = (stage.get("agent_log") or {}).get("plan") or {}
    if plan:
        out.append(Paragraph("Plan", styles["h3"]))
        out.append(
            _kv_table(
                [
                    ["route", str(plan.get("route") or "")],
                    ["rationale", str(plan.get("rationale") or "")],
                    ["expanded_query", str(plan.get("expanded_query") or "")],
                ]
            )
        )
        out.append(Spacer(1, 4))

    fa = (stage.get("agent_log") or {}).get("final_answer") or {}
    out.append(Paragraph("Answer", styles["h3"]))
    out.extend(_md_to_paragraphs(str(fa.get("answer") or "(no answer)"), styles))
    cited = fa.get("evidence_event_ids") or []
    if cited:
        out.append(Spacer(1, 2))
        out.append(
            Paragraph(
                "<b>Cited event_ids (" + str(len(cited)) + "):</b> " + _escape(", ".join(map(str, cited[:24]))),
                styles["body"],
            )
        )

    top_events = (stage.get("handoff") or {}).get("top_events") or []
    if top_events:
        out.append(Spacer(1, 4))
        out.append(Paragraph("Top weighted events from handoff", styles["h3"]))
        out.append(_events_table(top_events))
    return out


def _render_curated(bundle: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph("Stage C — Curated bundle", styles["h2"]))
    out.append(
        _kv_table(
            [
                ["Union working_set size", str(bundle.get("n_union") or 0)],
                ["Curated events", str(bundle.get("n_curated") or 0)],
                ["Probe tools", ", ".join(bundle.get("probe_tools") or []) or "(none)"],
                ["Gap tools", ", ".join(bundle.get("gap_tools") or []) or "(none)"],
            ]
        )
    )
    if bundle.get("curated_events"):
        out.append(Spacer(1, 4))
        out.append(Paragraph("Top curated events handed to synthesis model", styles["h3"]))
        out.append(_events_table(bundle["curated_events"], max_rows=15))
    return out


def _render_synthesis(synth: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph("Stage D — PTV synthesis", styles["h2"]))
    out.append(
        _kv_table(
            [
                ["Model", str(synth.get("model") or "")],
                ["Elapsed (s)", str(synth.get("elapsed_sec") or "")],
                ["num_ctx", str(synth.get("num_ctx") or "")],
                ["Input chars", str(synth.get("input_chars") or "")],
            ]
        )
    )
    out.append(Spacer(1, 6))
    if synth.get("error"):
        out.append(Paragraph("<b>Synthesis failed:</b> " + _escape(synth["error"]), styles["body"]))
        return out
    out.extend(_md_to_paragraphs(str(synth.get("markdown") or "(empty)"), styles))
    return out


def _hits_table(hits: List[Dict[str, Any]], max_rows: int = 6) -> Table:
    header = ["id", "source", "score", "snippet"]
    rows: List[List[str]] = [header]
    for h in (hits or [])[:max_rows]:
        snippet = (h.get("text") or h.get("snippet") or "").strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:220] + "…"
        score = h.get("score")
        if isinstance(score, (int, float)):
            score = f"{float(score):.4f}"
        rows.append(
            [
                str(h.get("id") or ""),
                str(h.get("source") or ""),
                str(score or ""),
                snippet,
            ]
        )
    styles = getSampleStyleSheet()
    safe = [[Paragraph(_escape(c), styles["BodyText"]) for c in r] for r in rows]
    t = Table(safe, colWidths=[55, 70, 50, 310])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#16a085")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.4, HexColor("#7f8c8d")),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, HexColor("#bdc3c7")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f4faf8")]),
            ]
        )
    )
    return t


def _render_mkg_overall(mkg: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    out.append(Paragraph("Stage E — MKG retrieval + overall synthesis", styles["h2"]))

    if not mkg or mkg.get("skipped"):
        reason = (mkg or {}).get("skipped") or "not run"
        out.append(Paragraph(f"<i>Stage E skipped: {_escape(str(reason))}</i>", styles["body"]))
        return out
    if mkg.get("error"):
        out.append(Paragraph("<b>Stage E error:</b> " + _escape(str(mkg["error"])), styles["body"]))
        out.append(
            _kv_table(
                [
                    ["Synth model", str(mkg.get("synth_model") or "")],
                    ["Elapsed (s)", str(mkg.get("elapsed_sec") or "")],
                ]
            )
        )
        return out

    overlap = mkg.get("overlap") or {}
    out.append(
        _kv_table(
            [
                ["Synth model", str(mkg.get("synth_model") or "")],
                ["Router model", str(mkg.get("router_model") or "(off)")],
                ["Embed model", str(mkg.get("embed_model") or "")],
                ["Top-K per lane", str(mkg.get("top_k") or "")],
                ["Use router", str(mkg.get("use_router") or False)],
                ["Restrict to router sources", str(mkg.get("router_restrict_sources") or False)],
                ["Effective sources", ", ".join(mkg.get("effective_sources") or []) or "(full pilot slice)"],
                ["Embed text", str(mkg.get("embed_text") or "")[:240]],
                ["TS strategy", str(mkg.get("ts_strategy") or "")],
                ["TS terms used", ", ".join(mkg.get("ts_terms_used") or []) or "(none)"],
                ["Overlap (both)", str(len(overlap.get("both") or []))],
                ["Jaccard", f"{float(overlap.get('jaccard') or 0):.3f}"],
                ["DB sec", str(mkg.get("db_sec") or "")],
                ["Embed sec", str(mkg.get("embed_sec") or "")],
                ["Stage elapsed (s)", str(mkg.get("elapsed_sec") or "")],
            ]
        )
    )

    plan = mkg.get("router_plan") or {}
    if plan:
        out.append(Spacer(1, 4))
        out.append(Paragraph("Router plan", styles["h3"]))
        out.append(
            _kv_table(
                [
                    ["Question type", str(plan.get("question_type") or "")],
                    ["Semantic query", str(plan.get("semantic_query") or "")[:240]],
                    [
                        "Selected sources",
                        ", ".join(
                            str(s.get("source") or "")
                            for s in (plan.get("selected_sources") or [])
                        )
                        or "(none)",
                    ],
                    [
                        "Selected modules",
                        ", ".join(
                            str(m.get("module") or "")
                            for m in (plan.get("selected_modules") or [])
                        )
                        or "(none)",
                    ],
                    ["Notes", str(plan.get("notes") or "")[:240]],
                ]
            )
        )

    sem = mkg.get("semantic_hits") or []
    ts = mkg.get("ts_hits") or []
    if sem:
        out.append(Spacer(1, 4))
        out.append(Paragraph(f"Semantic lane (top {min(len(sem), 6)} of {len(sem)})", styles["h3"]))
        out.append(_hits_table(sem))
    if ts:
        out.append(Spacer(1, 4))
        out.append(Paragraph(f"TS lane (top {min(len(ts), 6)} of {len(ts)})", styles["h3"]))
        out.append(_hits_table(ts))

    llm = mkg.get("llm") or {}
    out.append(Spacer(1, 6))
    out.append(Paragraph("Overall synthesis", styles["h3"]))
    if llm.get("error"):
        out.append(Paragraph("<b>Synthesis error:</b> " + _escape(str(llm["error"])), styles["body"]))
    else:
        out.extend(_md_to_paragraphs(str(llm.get("markdown") or "(empty)"), styles))
    return out


def _render_patient(run: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    patient = run.get("patient") or {}
    title = f"Patient {patient.get('code', '?')} — {patient.get('label') or patient.get('phenotype') or ''}"
    out.append(Paragraph(_escape(title), styles["h1"]))
    out.append(
        _kv_table(
            [
                ["Phenotype", str(patient.get("phenotype") or "")],
                ["Headline", str(patient.get("headline") or "")],
                ["Patient ID", str(patient.get("patient_id") or "")],
                ["PTV file", Path(str(patient.get("path") or "")).name],
                ["Graph hash", str(run.get("graph_hash") or "")],
                ["Events", str(run.get("n_events") or "")],
                ["Total elapsed (s)", str(run.get("elapsed_sec") or "")],
            ]
        )
    )

    out.append(Spacer(1, 6))
    out.append(Paragraph("Question", styles["h2"]))
    out.extend(_md_to_paragraphs(str(run.get("question") or ""), styles))

    if run.get("error"):
        out.append(Paragraph("<b>Pipeline error:</b> " + _escape(run["error"]), styles["body"]))
        return out

    stages = run.get("stages") or {}
    out.extend(_render_stage_probe_or_gap("Stage A — Probe (8B)", stages.get("probe") or {}, styles))
    out.extend(_render_stage_probe_or_gap("Stage B — Gap assessment (8B)", stages.get("gap") or {}, styles))
    out.extend(_render_curated(stages.get("curated_bundle") or {}, styles))
    out.extend(_render_synthesis(stages.get("synthesis") or {}, styles))
    if "mkg_overall_synth" in stages:
        out.extend(_render_mkg_overall(stages.get("mkg_overall_synth") or {}, styles))
    return out


def render(receipt_path: Path, out_path: Path) -> Path:
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    styles = _styles()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=44,
        bottomMargin=44,
        title="FORWARD 3-Agent PTV Report",
    )

    story: List[Any] = []
    story.append(Paragraph("FORWARD PTV 3-Agent Harness Report", styles["title"]))
    models = payload.get("models") or {}
    config = payload.get("config") or {}
    mkg_cfg = (config.get("mkg") or {}) if isinstance(config.get("mkg"), dict) else {}
    story.append(
        _kv_table(
            [
                ["Receipt", receipt_path.name],
                ["Built at (UTC)", str(payload.get("built_at") or "")],
                ["Cohort dir", str(payload.get("cohort_dir") or "")],
                ["Probe model", str(models.get("probe") or "")],
                ["Gap model", str(models.get("gap") or "")],
                ["PTV synthesis model (Stage D)", str(models.get("synth") or "")],
                ["MKG overall synth model (Stage E)", str(models.get("mkg_overall_synth") or "(off)")],
                ["MKG router model", str(models.get("mkg_router") or "(off)")],
                ["MKG embed model", str(models.get("mkg_embed") or "(off)")],
                ["Stage E enabled", str(config.get("stage_e_enabled"))],
                ["MKG top-K", str(mkg_cfg.get("top_k") or "")],
                ["MKG router restrict sources", str(mkg_cfg.get("router_restrict_sources") or False)],
                ["Patients", str(payload.get("n_patients") or 0)],
                ["Total elapsed (s)", str(payload.get("elapsed_sec") or "")],
                ["Probe max turns", str(config.get("probe_max_turns") or "")],
                ["Gap max turns", str(config.get("gap_max_turns") or "")],
                ["Synth num_ctx", str(config.get("synth_num_ctx") or "")],
            ]
        )
    )
    story.append(Spacer(1, 8))

    runs = payload.get("runs") or []
    for i, run in enumerate(runs):
        story.extend(_render_patient(run, styles))
        if i < len(runs) - 1:
            story.append(PageBreak())

    doc.build(story)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--receipt", type=Path, required=True, help="Path to the JSON receipt produced by the harness.")
    ap.add_argument("--out", type=Path, required=True, help="Output PDF path.")
    args = ap.parse_args()

    if not args.receipt.exists():
        raise SystemExit(f"receipt not found: {args.receipt}")
    pdf = render(args.receipt.resolve(), args.out.resolve())
    print(str(pdf))


if __name__ == "__main__":
    main()
