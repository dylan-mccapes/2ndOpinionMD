#!/usr/bin/env python3
"""Render PDF report for PTV toolkit + harness + chatbot."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.0f}%" if d else "0%"


def _table(headers, rows, widths):
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    data = [[Paragraph(f"<b>{h}</b>", body) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), body) for c in row])
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build_pdf(summary_path: Path, out_pdf: Path) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    h = summary["header"]
    a = summary["aggregate"]

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    body.leading = 13
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=10)

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="REPORT_PTV_TOOLKIT_HARNESS_CHATBOT_20260423",
        author="2ndOpinionMD",
        subject="PTV Toolkit Report",
    )

    story = []
    story.append(Paragraph("REPORT — PTV Toolkit, Harness Results, and Chatbot", h1))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).isoformat()}<br/>"
            f"Model: {h.get('model')}<br/>"
            f"Graph hash: {h.get('graph_hash')}<br/>"
            f"Questions: {h.get('n_questions')} &nbsp;&nbsp; Elapsed: {h.get('elapsed_sec')}s",
            small,
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("1) Toolkit Overview", h2))
    story.append(
        Paragraph(
            "The toolkit provides deterministic retrieval tools for graph-grounded clinical QA: "
            "code_index_lookup, temporal_scan, semantic_search, bfs_expand, get_event, "
            "list_event_types, and graph_stats. It runs in a strict plan-first JSON loop "
            "and emits handoff artifacts for downstream 70B review.",
            body,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("2) Harness Metrics", h2))
    metric_rows = [
        ["Plan emitted", f"{a['has_plan']}/{a['n']} ({_pct(a['has_plan'], a['n'])})"],
        ["Plan-route match", f"{a['plan_route_match']}/{a['n']} ({_pct(a['plan_route_match'], a['n'])})"],
        ["Primary-tool match", f"{a['primary_tool_match']}/{a['n']} ({_pct(a['primary_tool_match'], a['n'])})"],
        ["Any-tool match", f"{a['any_tool_match']}/{a['n']} ({_pct(a['any_tool_match'], a['n'])})"],
        ["Valid evidence IDs", f"{a['final_has_evidence']}/{a['n']} ({_pct(a['final_has_evidence'], a['n'])})"],
        ["Keyword match", f"{a['keyword_match']}/{a['n']} ({_pct(a['keyword_match'], a['n'])})"],
        ["Expanded query used", f"{a['has_expanded_query']}/{a['n']}"],
    ]
    story.append(_table(["Metric", "Result"], metric_rows, [2.9 * inch, 2.7 * inch]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3) Result Assessment", h2))
    findings = [
        "Primary tool routing reached 100%, indicating stable retrieval decision-making in the 8B probe.",
        "Evidence grounding reached 90%; one probe ended at max_turns before final_answer.",
        "Two plan-route mismatches were orientation label differences rather than wrong tool usage.",
        "Current quality supports pilot use for retrieval and curation, with 70B retained as synthesis validator.",
    ]
    for x in findings:
        story.append(Paragraph(f"- {x}", body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4) Chatbot Delivery and Test Status", h2))
    story.append(
        Paragraph(
            "Interactive chatbot scripts were added for both WSL and PowerShell. "
            "The chatbot reuses the harness retrieval loop (run_agent), supports transcript/handoff capture, "
            "and prints tool traces plus evidence IDs.",
            body,
        )
    )
    chat_rows = [
        ["WSL/Linux entry", "server/scripts/ptv_chatbot_wsl.py"],
        ["PowerShell launcher", "server/scripts/ptv_chatbot.ps1"],
        ["WSL host routing", "--wsl-host and --auto-wsl-host"],
        ["Startup connectivity probe", "GET /api/tags with targeted hints"],
        ["Windows default URL", "http://127.0.0.1:11434"],
    ]
    story.append(_table(["Component", "Status"], chat_rows, [2.1 * inch, 3.5 * inch]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5) Recommended Next Steps", h2))
    for x in [
        "Increase enforced final_answer behavior after decisive one-tool queries.",
        "Add strict evidence-id sanitation before final synthesis.",
        "Expand orientation route aliases in harness scoring.",
        "Add Bayesian probes once bayesian_update_uc enters toolkit.",
    ]:
        story.append(Paragraph(f"- {x}", body))

    story.append(Spacer(1, 8))
    story.append(Paragraph("References", h2))
    refs = [
        "receipts/RECEIPT_PTV_TOOLKIT_HARNESS_EOH_LLAMA_LUCIFER_20260423.md",
        "artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer/summary.json",
        "server/scripts/ptv_toolkit_harness.py",
        "server/scripts/ptv_chatbot_wsl.py",
        "server/scripts/ptv_chatbot.ps1",
    ]
    for r in refs:
        story.append(Paragraph(f"- {r}", small))

    doc.build(story)
    print(f"Wrote {out_pdf}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--summary",
        default="artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer/summary.json",
    )
    ap.add_argument(
        "--out",
        default="reports/REPORT_PTV_TOOLKIT_HARNESS_CHATBOT_20260423.pdf",
    )
    args = ap.parse_args()

    summary = Path(args.summary).resolve()
    out_pdf = Path(args.out).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(summary, out_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
