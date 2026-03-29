"""Generate a PDF from an EoHD detective run (final report + step reports + graph figures)."""
from __future__ import annotations

import base64
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

_CSS = """
@page { size: letter; margin: 1in 0.75in; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 20pt; color: #0d3b66; border-bottom: 2px solid #0d3b66; padding-bottom: 4pt; margin-top: 24pt; }
h2 { font-size: 15pt; color: #1d5a8a; margin-top: 18pt; }
h3 { font-size: 13pt; color: #2a7ab5; margin-top: 14pt; }
h4 { font-size: 11pt; color: #333; margin-top: 10pt; }
.header { text-align: center; margin-bottom: 20pt; }
.header h1 { font-size: 22pt; border: none; margin-bottom: 4pt; }
.header .subtitle { font-size: 12pt; color: #555; }
.header .date { font-size: 10pt; color: #888; }
.disclaimer { background: #fff3cd; border: 1px solid #ffc107; padding: 8pt 12pt; margin: 12pt 0; font-size: 9pt; color: #856404; }
.step-header { background: #e8f4fd; padding: 6pt 10pt; margin-top: 16pt; border-left: 3px solid #1d5a8a; }
.step-header h2 { margin: 0; color: #0d3b66; }
.step-header .step-q { font-style: italic; color: #555; font-size: 10pt; margin-top: 2pt; }
.evidence-claim { background: #f8f9fa; border-left: 2px solid #28a745; padding: 4pt 8pt; margin: 4pt 0; font-size: 10pt; }
.evidence-claim .strength { font-weight: bold; }
.citation-list { font-size: 9pt; color: #666; margin-top: 8pt; }
.figure-block { margin: 14pt 0; page-break-inside: avoid; }
.figure-block img { max-width: 100%; }
.figure-caption { font-size: 9pt; color: #444; margin-top: 4pt; font-style: italic; }
.figure-interp { background: #f0f7ff; border-left: 3px solid #457b9d; padding: 6pt 10pt; margin: 6pt 0; font-size: 10pt; }
.footer { font-size: 8pt; color: #999; text-align: center; margin-top: 24pt; border-top: 1px solid #ddd; padding-top: 4pt; }
ul, ol { margin-left: 16pt; }
li { margin-bottom: 4pt; }
"""

_STEP_KIND_LABELS = {
    "terrain_risk": "Terrain & Risk Assessment",
    "flare_vs_noise": "Flare vs. Noise Classification",
    "diagnostic_landscape": "Diagnostic Landscape Analysis",
    "trajectory": "Trajectory & Evolution Mapping",
    "treatment_risk_tradeoff": "Treatment Risk-Tradeoff Analysis",
    "meta_calibration": "Meta-Calibration & Data Gaps",
}


def _md(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


def _render_evidence_map(emap: Optional[Dict[str, Any]]) -> str:
    if not emap:
        return ""
    claims = emap.get("claims", [])
    if not claims:
        return ""
    html = '<h4>Evidence Map</h4>\n'
    for c in claims:
        strength = c.get("support_strength", "unknown")
        html += (
            f'<div class="evidence-claim">'
            f'<span class="strength">[{strength}]</span> '
            f'{c.get("text", "")}'
            f'</div>\n'
        )
    return html


def _render_citations(cites: Optional[List[Dict[str, Any]]]) -> str:
    if not cites:
        return ""
    html = '<div class="citation-list"><strong>Sources:</strong> '
    titles = []
    for c in cites[:15]:
        t = c.get("title", c.get("source", ""))
        if t and t not in titles:
            titles.append(t)
    html += "; ".join(titles)
    html += "</div>\n"
    return html


def _render_figures(
    figures: List[Dict[str, Any]],
    interpretations: Optional[List[str]] = None,
) -> str:
    """Render graph analysis figures as HTML for the PDF."""
    if not figures:
        return ""

    html = '<h1>Graph Analysis</h1>\n'
    interps = interpretations or []

    for i, fig in enumerate(figures):
        png = fig.get("png_bytes", b"")
        if not png:
            continue

        title = fig.get("title", f"Figure {i + 1}")
        caption = fig.get("caption", "")
        b64 = base64.b64encode(png).decode("ascii")

        html += f'<div class="figure-block">\n'
        html += f'<h3>Figure {i + 1}: {title}</h3>\n'
        html += f'<img src="data:image/png;base64,{b64}" />\n'
        if caption:
            html += f'<div class="figure-caption">{caption}</div>\n'
        if i < len(interps) and interps[i]:
            html += f'<div class="figure-interp">'
            html += f'<strong>Interpretation:</strong> {_md(interps[i])}'
            html += f'</div>\n'
        html += '</div>\n'

    return html


def build_detective_pdf(
    patient_id: str,
    question: str,
    focus: str,
    final_report: Optional[str],
    steps: List[Dict[str, Any]],
    graph_events: int = 0,
    graph_edges: int = 0,
    elapsed_ms: int = 0,
    figures: Optional[List[Dict[str, Any]]] = None,
    figure_interpretations: Optional[List[str]] = None,
) -> bytes:
    """Build a PDF from the detective run results. Returns PDF bytes.

    Args:
        figures: list of dicts from graph_figures.generate_all_figures()
        figure_interpretations: LLM-generated interpretation per figure
    """

    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    html_parts = [
        f"<html><head><style>{_CSS}</style></head><body>",
        '<div class="header">',
        "<h1>EoH Detective Report</h1>",
        f'<div class="subtitle">Patient: {patient_id}</div>',
        f'<div class="date">Generated {now}</div>',
        "</div>",
        '<div class="disclaimer">',
        "<strong>Notice:</strong> This is an analytic knowledge map generated by the "
        "2ndOpinionMD Ethos-of-Health engine. It is NOT medical advice and is NOT a "
        "substitute for in-person clinical care or professional medical judgment.",
        "</div>",
        f"<p><strong>Question:</strong> {question}</p>",
    ]

    if focus and focus != "eoh_detective_run":
        html_parts.append(f"<p><strong>Focus:</strong> {focus}</p>")
    if graph_events:
        html_parts.append(
            f"<p><strong>Graph:</strong> {graph_events:,} events, "
            f"{graph_edges:,} edges</p>"
        )
    if elapsed_ms:
        html_parts.append(
            f"<p><strong>Run time:</strong> {elapsed_ms / 1000:.0f}s</p>"
        )

    # Final synthesis report
    if final_report:
        html_parts.append("<h1>Synthesis Report</h1>")
        html_parts.append(_md(final_report))

    # Step reports
    html_parts.append("<h1>Step Reports</h1>")
    for step in steps:
        sid = step.get("step_id", "?")
        kind = step.get("kind", "")
        kind_label = _STEP_KIND_LABELS.get(kind, kind.replace("_", " ").title())
        q = step.get("q", "")

        html_parts.append(f'<div class="step-header">')
        html_parts.append(f"<h2>Step {sid}: {kind_label}</h2>")
        html_parts.append(f'<div class="step-q">{q}</div>')
        html_parts.append("</div>")

        answer = step.get("answer_text", "")
        if answer:
            html_parts.append(_md(answer))

        html_parts.append(_render_evidence_map(step.get("evidence_map")))
        html_parts.append(_render_citations(step.get("citations")))

    # Graph analysis figures
    if figures:
        html_parts.append(_render_figures(figures, figure_interpretations))

    # Footer
    html_parts.append(
        '<div class="footer">'
        f"Generated by 2ndOpinionMD EoH Detective &mdash; {now}"
        "</div>"
    )
    html_parts.append("</body></html>")

    full_html = "\n".join(html_parts)

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(full_html), dest=pdf_buffer)
    if pisa_status.err:
        logger.error("PDF generation failed with %d errors", pisa_status.err)
    pdf_buffer.seek(0)
    return pdf_buffer.read()


def save_detective_pdf(
    pdf_bytes: bytes,
    patient_id: str,
    run_id: str,
    output_dir: str = "artifacts/detective_reports",
) -> str:
    """Save PDF to disk and return the path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"detective_report_{patient_id}_{ts}_{run_id[:8]}.pdf"
    path = out / filename
    path.write_bytes(pdf_bytes)
    logger.info("Detective report PDF saved: %s (%d bytes)", path, len(pdf_bytes))
    return str(path)
