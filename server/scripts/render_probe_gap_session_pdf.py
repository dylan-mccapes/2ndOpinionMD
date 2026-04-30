#!/usr/bin/env python3
"""Render a ``forward_probe_gap_report_chatbot`` session JSONL into one PDF report.

Each JSON line is expected to look like ``chatbot_session.v1`` rows produced by the harness:
``question``, ``router_*``, ``mkg_*``, ``graph_tool``, ``graph_args``, ``gap_report``, ``final_report``, ``retro``, …

Usage::

    python server/scripts/render_probe_gap_session_pdf.py \\
        receipts/FORWARD_PROBE_GAP_SESSION_HARNESS_<stamp>_session.jsonl

    python server/scripts/render_probe_gap_session_pdf.py --session-jsonl path/to/session.jsonl --out report.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
            # Markdown pipe rows — plain text row for tables.
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


def _fmt_list(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(x) for x in val)
    return str(val)


def _load_turns(path: Path) -> List[Dict[str, Any]]:
    turns: List[Dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            turns.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return turns


def _render_retro(retro: Any, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    out: List[Any] = []
    if retro is None:
        return out
    if isinstance(retro, dict) and not retro:
        return out
    out.append(Paragraph("Retro bundle", styles["h2"]))
    if not isinstance(retro, dict):
        out.append(Paragraph(_escape(json.dumps(retro, default=str)[:8000]), styles["body"]))
        return out
    gate = retro.get("gate") if isinstance(retro.get("gate"), dict) else {}
    rows = [
        ["references_prior", str(gate.get("references_prior", ""))],
        ["retro_query", str(gate.get("retro_query") or "")],
        ["retro_summary (preview)", (retro.get("retro_summary") or "")[:1200]],
        ["evidence_turn_ids", _fmt_list(retro.get("evidence_turn_ids"))],
    ]
    out.append(_kv_table(rows))
    out.append(Spacer(1, 6))
    summ = str(retro.get("retro_summary") or "").strip()
    if len(summ) > 1200:
        out.append(Paragraph("Retro summary (full)", styles["h3"]))
        out.extend(_md_to_paragraphs(summ, styles))
    return out


def build_pdf(session_jsonl: Path, out_pdf: Path) -> None:
    turns = _load_turns(session_jsonl)
    styles = _styles()
    story: List[Any] = []

    session_id = turns[0].get("session_id") if turns else session_jsonl.stem
    graph_hash = turns[0].get("graph_hash") if turns else ""

    story.append(Paragraph("FORWARD Probe → GAP → Report — Session", styles["title"]))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            _escape(f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}"),
            styles["body"],
        )
    )
    story.append(_kv_table([["session_id", str(session_id)], ["graph_hash", str(graph_hash)], ["turns", str(len(turns))], ["source_file", session_jsonl.name]]))
    story.append(Spacer(1, 14))

    for i, row in enumerate(turns):
        if i > 0:
            story.append(PageBreak())

        tid = str(row.get("turn_id") or f"turn_{i + 1}")
        story.append(Paragraph(_escape(f"Turn {row.get('turn_index', i + 1)} — {tid}"), styles["h1"]))
        story.append(
            Paragraph(_escape(f"Timestamp: {row.get('ts') or ''}"), styles["body"]),
        )
        story.append(Spacer(1, 8))

        story.append(Paragraph("User question", styles["h2"]))
        story.extend(_md_to_paragraphs(str(row.get("question") or ""), styles))

        story.append(Paragraph("Router plan", styles["h2"]))
        story.append(
            _kv_table(
                [
                    ["semantic_query", str(row.get("router_plan_semantic_query") or "")[:4000]],
                    ["ts_terms", _fmt_list(row.get("router_ts_terms"))[:2000]],
                    ["sources", _fmt_list(row.get("router_sources"))],
                    ["modules", _fmt_list(row.get("router_modules"))],
                    ["question_type", str(row.get("router_question_type") or "")],
                ]
            )
        )

        story.append(Paragraph("MKG / probe metrics", styles["h2"]))
        story.append(
            _kv_table(
                [
                    ["mkg_jaccard", str(row.get("mkg_jaccard"))],
                    ["semantic_hits", str(row.get("mkg_semantic_hit_count") or "")],
                    ["ts_hits", str(row.get("mkg_ts_hit_count") or "")],
                    ["ts_or_fallback_used", str(row.get("ts_or_fallback_used"))],
                ]
            )
        )

        story.append(Paragraph("Graph tool", styles["h2"]))
        story.append(_kv_table([["graph_tool", str(row.get("graph_tool") or "")]]))
        args_obj = row.get("graph_args")
        ga = json.dumps(args_obj, indent=2, ensure_ascii=False, default=str) if args_obj is not None else "{}"
        story.append(Spacer(1, 4))
        story.append(Paragraph("graph_args (JSON)", styles["h3"]))
        story.append(Preformatted(ga[:12000], styles["mono"]))

        story.append(Paragraph("GAP report", styles["h2"]))
        story.extend(_md_to_paragraphs(str(row.get("gap_report") or ""), styles))

        story.append(Paragraph("Final report", styles["h2"]))
        story.extend(_md_to_paragraphs(str(row.get("final_report") or ""), styles))

        story.extend(_render_retro(row.get("retro"), styles))

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=44,
        bottomMargin=44,
        title=f"Session {session_id}",
        author="2OPMD FORWARD probe-gap-report harness",
    )
    doc.build(story)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "session_jsonl",
        nargs="?",
        type=Path,
        help="Path to *_session.jsonl (same rows as chatbot session log).",
    )
    ap.add_argument("--session-jsonl", type=Path, dest="session_jsonl_opt", help="Explicit path (alternative to positional).")
    ap.add_argument("--out", type=Path, default=None, help="Output PDF path (default: <stem>_report.pdf beside JSONL).")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    path = args.session_jsonl_opt or args.session_jsonl
    if path is None:
        print("error: pass session JSONL path as positional or --session-jsonl", file=sys.stderr)
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
        build_pdf(path, out)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
