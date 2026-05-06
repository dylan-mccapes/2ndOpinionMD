#!/usr/bin/env python3
"""
Build a PDF-ready EoHD markdown packet from:
1) a final detective report markdown, and
2) a raw SSE receipt log containing underlying step runs.

Output structure:
- Cover page
- Table of contents
- Main report
- One section per detective phase (A1, E1, ...)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import request


@dataclass
class StepMeta:
    step_id: str
    kind: str = ""
    question_type: str = ""
    q: str = ""


def _extract_balanced_json(text: str, start_idx: int) -> Tuple[Optional[str], int]:
    """Extract first balanced JSON object starting at/after start_idx."""
    i = text.find("{", start_idx)
    if i == -1:
        return None, start_idx

    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(text)):
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[i : j + 1], j + 1

    return None, start_idx


def parse_receipt_events(raw: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Parse (event, data_json) tuples from raw receipt text.
    Works for normal multi-line logs and "single giant line" logs.
    """
    events: List[Tuple[str, Dict[str, Any]]] = []
    event_positions = list(re.finditer(r"event:\s*([A-Za-z0-9_]+)", raw))

    for idx, match in enumerate(event_positions):
        event_name = match.group(1).strip()
        seg_start = match.end()
        seg_end = (
            event_positions[idx + 1].start()
            if idx + 1 < len(event_positions)
            else len(raw)
        )
        segment = raw[seg_start:seg_end]

        data_pos = segment.find("data:")
        if data_pos == -1:
            continue

        json_blob, _ = _extract_balanced_json(segment, data_pos)
        if not json_blob:
            continue

        try:
            payload = json.loads(json_blob)
        except Exception:
            continue

        if isinstance(payload, dict):
            events.append((event_name, payload))

    return events


def strip_frontmatter(md_text: str) -> str:
    if md_text.startswith("---"):
        parts = md_text.split("\n---", 1)
        if len(parts) == 2:
            return parts[1].lstrip("\n")
    return md_text


def _first_meaningful_line(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith(">"):
            continue
        return line
    return ""


def build_phase_synopsis(meta: StepMeta, body: str) -> str:
    kind_map = {
        "terrain_risk": "Maps the overall clinical terrain and dominant problems.",
        "data_gap": "Identifies key missing data that limit inference confidence.",
        "meta_calibration": "Assesses reliability, uncertainty, and interpretation limits.",
        "diagnostic_landscape": "Evaluates diagnostic hypotheses and relative support.",
        "mystery_focus": "Prioritizes investigative steps to resolve uncertainty.",
        "patient_facing_explanation": "Translates findings and uncertainty into patient-friendly language.",
    }
    base = kind_map.get(meta.kind, "")
    first = _first_meaningful_line(body)
    if first:
        first = re.sub(r"\s+", " ", first).strip()
        if len(first) > 170:
            first = first[:167].rstrip() + "..."
    if base and first:
        return f"{base} {first}"
    if base:
        return base
    if first:
        return first
    return "Phase report extracted from llm_done payload."


def build_data_availability_context(step_meta: Dict[str, StepMeta]) -> Optional[str]:
    """Explain intentional mixed framing across detective phases."""
    full_timeline_steps: List[str] = []
    sparse_steps: List[str] = []
    for sid, meta in step_meta.items():
        q = (meta.q or "").lower()
        if "entire timeline" in q or "major clinical arcs" in q:
            full_timeline_steps.append(sid)
        if (
            "extremely limited timeline" in q
            or "lack of clinical" in q
            or "absence of clinical information" in q
            or "single document header" in q
        ):
            sparse_steps.append(sid)

    if full_timeline_steps and sparse_steps:
        full_str = ", ".join(sorted(full_timeline_steps))
        sparse_str = ", ".join(sorted(sparse_steps))
        return (
            "## \\textcolor{calmblue}{Data Availability Context}\n\n"
            "This packet intentionally combines two analytical lenses from one run:\n\n"
            f"- **Broad timeline synthesis phases:** {full_str}\n"
            f"- **Data-scarcity stress-test phases:** {sparse_str}\n\n"
            "This contrast is expected. Some prompts request full longitudinal interpretation, "
            "while others explicitly test uncertainty handling under sparse-input assumptions. "
            "Read these as complementary views, not accidental contradictions."
        )
    return None


def build_toc(step_order: List[str], step_meta: Dict[str, StepMeta], step_reports: Dict[str, str]) -> str:
    lines = [
        "## \\textcolor{calmblue}{Stage Guide (Synopsis)}",
        "",
        "- **Main Report**",
        "  - Primary detective synthesis and integrated trajectory view.",
    ]
    for sid in step_order:
        meta = step_meta.get(sid, StepMeta(step_id=sid))
        body = step_reports.get(sid, "")
        synopsis = build_phase_synopsis(meta, body)
        lines.append(f"- **Phase {sid}**")
        lines.append(f"  - {synopsis}")
    return "\n".join(lines)


def render_packet(
    patient_id: str,
    main_report_md: str,
    main_report_title: str,
    step_order: List[str],
    step_meta: Dict[str, StepMeta],
    step_reports: Dict[str, str],
    detective_report: Optional[str],
    tone: str = "default",
    include_consistency_note: bool = True,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: List[str] = []
    if tone == "comfort":
        subtitle = "Main Report + Underlying Phase Reports (Comfort Profile)"
        cover_note = (
            "This packet is prepared to support calm, traceable review. "
            "It includes the main detective report followed by each underlying phase report in run order."
        )
        cover_bullets = [
            "- What this packet includes: Cover, TOC, main report, and per-phase reports",
            "- Sources used: receipt event stream + final report markdown",
        ]
    else:
        subtitle = "Main Report + Underlying Phase Reports"
        cover_note = (
            "This packet is generated for PDF export. It includes the primary "
            "detective report followed by each underlying phase report in run order."
        )
        cover_bullets = [
            "- Section order: Cover -> TOC -> Main report -> Phase covers/reports",
            "- Source chain: receipt event stream + final report markdown",
        ]

    lines.extend(
        [
            "---",
            f'title: "EoHD Packet — {patient_id}"',
            f'subtitle: "{subtitle}"',
            'author: "2ndOpinionMD EoHD PDF Agent"',
            f'date: "{now}"',
            "toc: false",
            "---",
            "",
            "# \\textcolor{calmblue}{Ethos-of-Health Detective Packet}",
            "",
            f"## {patient_id}",
            "",
            cover_note,
            "",
            *cover_bullets,
            "",
            "\\sectionrule",
            "",
            (
                build_data_availability_context(step_meta)
                if include_consistency_note and build_data_availability_context(step_meta)
                else ""
            ),
            "",
            "\\sectionrule" if include_consistency_note and build_data_availability_context(step_meta) else "",
            "",
            "\\newpage",
            "",
            build_toc(step_order, step_meta, step_reports),
            "",
            "\\sectionrule",
            "",
            "\\newpage",
            "",
            "## \\textcolor{calmblue}{Main Report}",
            "",
            f"_Source: {main_report_title}_",
            "",
            strip_frontmatter(main_report_md).rstrip(),
            "",
            "\\sectionrule",
            "",
        ]
    )

    if detective_report:
        lines.extend(
            [
                "",
                "## \\textcolor{calmblue}{Main Report (Detective Event Payload)}",
                "",
                detective_report.rstrip(),
                "",
                "\\sectionrule",
                "",
            ]
        )

    for sid in step_order:
        meta = step_meta.get(sid, StepMeta(step_id=sid))
        body = step_reports.get(sid, "").strip()
        if not body:
            continue
        lines.extend(
            [
                "",
                "\\newpage",
                "",
                f"## \\textcolor{{calmblue}}{{Phase {sid}}}",
                "",
                (
                    f"- **Phase context:** {meta.kind or 'unknown'}"
                    if tone == "comfort"
                    else f"- **Kind:** {meta.kind or 'unknown'}"
                ),
                (
                    f"- **Question type:** {meta.question_type or 'unknown'}"
                    if tone == "comfort"
                    else f"- **Question Type:** {meta.question_type or 'unknown'}"
                ),
                "",
                "## Prompt",
                "",
                meta.q.strip() or "_No prompt captured._",
                "",
                "## Report",
                "",
                body,
                "",
                "\\sectionrule",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def build_pdf(
    in_md: Path,
    out_pdf: Path,
    pdf_geometry: str,
    pdf_fontsize: str,
    pdf_header: Optional[Path],
) -> None:
    cmd = [
        "pandoc",
        str(in_md),
        "--toc",
        "--toc-depth=2",
        "-V",
        f"geometry:{pdf_geometry}",
        "-V",
        f"fontsize={pdf_fontsize}",
    ]
    if pdf_header:
        cmd.extend(["-H", str(pdf_header)])
    cmd.extend(["-o", str(out_pdf)])
    subprocess.run(cmd, check=True)


def synthesize_with_gpt41(
    packet_md: str,
    tone: str,
    model: str,
    step_order: List[str],
    max_chars: int = 220000,
) -> str:
    """
    Optional coherence pass using GPT-4.1, performed section-by-section.
    This avoids whole-document truncation and lets the model improve page flow.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot run GPT-4.1 synthesis.")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError(f"OpenAI client unavailable: {exc}") from exc

    client = OpenAI(api_key=api_key, timeout=120.0)
    tone_hint = (
        "Use calm, supportive language and gentle transitions."
        if tone == "comfort"
        else "Use concise professional language and clear transitions."
    )

    section_anchor = re.compile(
        r"^## \\textcolor\{calmblue\}\{(Main Report|Phase [^}]+)\}\s*$",
        flags=re.MULTILINE,
    )
    anchors = list(section_anchor.finditer(packet_md))
    if not anchors:
        anchors = []

    sections: List[Tuple[str, str]] = []
    if anchors:
        preface = packet_md[: anchors[0].start()]
        if preface.strip():
            sections.append(("preface", preface))
        for i, m in enumerate(anchors):
            sec_name = m.group(1).strip()
            start = m.start()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(packet_md)
            sections.append((sec_name, packet_md[start:end]))
    else:
        sections.append(("document", packet_md))

    revised_sections: List[str] = []
    for sec_name, sec_md in sections:
        sec_in = sec_md.rstrip() + "\n"
        if not sec_in.strip():
            revised_sections.append(sec_in)
            continue
        if len(sec_in) > max_chars:
            print(
                f"WARNING: synthesis skipped for section '{sec_name}' "
                f"({len(sec_in)} chars > {max_chars})."
            )
            revised_sections.append(sec_in)
            continue

        system_prompt = (
            "You are an agent working for 2ndOpinionMD as Ethos of Health PDF Agent.\n"
            "You are doing an editorial section pass for a medical analytic packet.\n"
            "Revise this single section for clarity, coherence, and pagination flow.\n"
            "Hard constraints:\n"
            "1) Keep the section heading exactly as-is.\n"
            "2) Keep all facts/claims; do not invent or remove clinical claims.\n"
            "3) Preserve markdown lists, markdown tables, and LaTeX commands.\n"
            "4) Keep markdown valid for Pandoc PDF.\n"
            "5) You may add short transitions and light elaboration for readability.\n"
            "6) You may insert \\newpage only where it improves flow.\n"
            "7) NEVER use placeholders like 'section unchanged', 'see original', or 'omitted'.\n"
            "8) Do not delete table rows/columns; keep tables coherent.\n"
        )
        user_prompt = (
            f"Section: {sec_name}\n"
            f"{tone_hint}\n\n"
            "Return only the fully revised section markdown.\n\n"
            "=== BEGIN SECTION ===\n"
            f"{sec_in}\n"
            "=== END SECTION ===\n"
        )

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            revised = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            print(f"WARNING: synthesis failed for section '{sec_name}': {exc}")
            revised_sections.append(sec_in)
            continue

        if not revised:
            print(f"WARNING: synthesis returned empty section '{sec_name}', keeping original.")
            revised_sections.append(sec_in)
            continue

        candidate = revised + ("\n" if not revised.endswith("\n") else "")
        valid, reason = _section_synthesis_is_valid(sec_in, candidate)
        if not valid:
            print(
                f"WARNING: synthesis rejected for section '{sec_name}' ({reason}); "
                "keeping original."
            )
            revised_sections.append(sec_in)
            continue
        revised_sections.append(candidate)

    joined = "".join(revised_sections)
    valid, reason = _synthesis_is_valid(
        original_packet=packet_md,
        synthesized_packet=joined,
        step_order=step_order,
    )
    if not valid:
        raise RuntimeError(f"Sectioned synthesis invalid: {reason}")
    return joined


def _synthesis_is_valid(
    original_packet: str,
    synthesized_packet: str,
    step_order: List[str],
) -> Tuple[bool, str]:
    """Guardrail: reject synthesized output if it drops content/sections."""
    low = synthesized_packet.lower()
    banned_markers = [
        "section unchanged",
        "see original",
        "omitted",
        "unchanged for editorial",
    ]
    for marker in banned_markers:
        if marker in low:
            return False, f"contains banned placeholder marker: {marker}"

    # Ensure all phase headings still exist.
    for sid in step_order:
        heading = f"## \\textcolor{{calmblue}}{{Phase {sid}}}"
        if heading not in synthesized_packet:
            return False, f"missing phase heading: {sid}"

    # Coherence pass should not massively shrink content.
    # If <85% of original size, it's likely compressing by omission.
    if len(synthesized_packet) < int(len(original_packet) * 0.85):
        return False, "synthesized output shrank too much vs original"

    return True, "ok"


def _section_synthesis_is_valid(original_section: str, revised_section: str) -> Tuple[bool, str]:
    low = revised_section.lower()
    banned_markers = ["section unchanged", "see original", "omitted", "unchanged for editorial"]
    for marker in banned_markers:
        if marker in low:
            return False, f"contains banned placeholder marker: {marker}"

    first_heading = re.search(r"^## .+$", original_section, flags=re.MULTILINE)
    if first_heading and first_heading.group(0) not in revised_section:
        return False, "missing section heading"

    if len(revised_section) < int(len(original_section) * 0.75):
        return False, "section shrank too much"

    original_table_lines = len(
        [ln for ln in original_section.splitlines() if ln.strip().startswith("|")]
    )
    revised_table_lines = len(
        [ln for ln in revised_section.splitlines() if ln.strip().startswith("|")]
    )
    if original_table_lines >= 4 and revised_table_lines < int(original_table_lines * 0.6):
        return False, "table content reduced too aggressively"

    return True, "ok"


def _safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip()) or "unknown"


def _load_analytics_export_payload(
    export_json_path: Optional[Path],
    export_url: Optional[str],
    timeout_s: int,
) -> Optional[Dict[str, Any]]:
    if export_json_path and export_json_path.exists():
        return json.loads(export_json_path.read_text(encoding="utf-8", errors="replace"))

    if export_url:
        req = request.Request(export_url, method="POST")
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    return None


def _build_analytics_appendix_and_emit_images(
    payload: Dict[str, Any],
    charts_dir: Path,
    packet_parent_dir: Path,
) -> str:
    charts = payload.get("charts") if isinstance(payload.get("charts"), dict) else {}
    ordered_keys = [
        "stability_band",
        "event_edge_intensity",
        "precedence_map",
        "terrain_trajectory",
        "flare_noise_panel",
    ]
    patient_id = str(payload.get("patient_id", "UNKNOWN_PATIENT"))
    safe_patient = _safe_slug(patient_id)
    charts_dir.mkdir(parents=True, exist_ok=True)

    emitted: List[Tuple[str, Path]] = []
    for key in ordered_keys:
        b64 = charts.get(key)
        if not isinstance(b64, str) or not b64.strip():
            continue
        out_png = charts_dir / f"{safe_patient}_{key}.png"
        try:
            out_png.write_bytes(base64.b64decode(b64))
            emitted.append((key, out_png))
        except Exception:
            continue

    if not emitted:
        return ""

    labels = {
        "stability_band": "Stability Band",
        "event_edge_intensity": "Event and Edge Intensity",
        "precedence_map": "Precedence Map",
        "terrain_trajectory": "Terrain Trajectory",
        "flare_noise_panel": "Flare vs Noise Panel",
    }

    lines = [
        "",
        "\\newpage",
        "",
        "## \\textcolor{calmblue}{Timeline Analytics Appendix}",
        "",
        (
            "These charts are generated by the timeline analytics engine and appended "
            "for clinician-facing pattern review."
        ),
        "",
    ]
    for key, p in emitted:
        rel = str(p.resolve())
        lines.extend(
            [
                f"### \\textcolor{{calmblue}}{{{labels.get(key, key)}}}",
                "",
                f"![{labels.get(key, key)}]({rel})",
                "",
                "\\sectionrule",
                "",
            ]
        )
    return "\n".join(lines)


def load_env_if_available() -> None:
    """Load .env from repo root when python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def main() -> None:
    load_env_if_available()
    parser = argparse.ArgumentParser(
        description="Build PDF-ready EoHD packet from report + receipt."
    )
    parser.add_argument("--report-md", required=True, type=Path)
    parser.add_argument("--receipt-md", required=True, type=Path)
    parser.add_argument(
        "--out-md",
        type=Path,
        default=Path("receipts/EOHD_PACKET_PDF_READY.md"),
    )
    parser.add_argument(
        "--emit-step-files-dir",
        type=Path,
        default=Path("receipts/eohd_step_reports"),
    )
    parser.add_argument(
        "--tone",
        choices=["default", "comfort"],
        default="default",
        help="Writing/packaging tone profile for generated markdown.",
    )
    parser.add_argument(
        "--out-pdf",
        type=Path,
        default=None,
        help="Optional PDF output path. If set, pandoc is invoked.",
    )
    parser.add_argument(
        "--pdf-geometry",
        default="margin=0.85in",
        help="Pandoc PDF geometry variable (e.g., margin=0.85in).",
    )
    parser.add_argument(
        "--pdf-fontsize",
        default="11pt",
        help="Pandoc PDF fontsize variable (e.g., 11pt).",
    )
    parser.add_argument(
        "--pdf-header",
        type=Path,
        default=Path("receipts/eohd_pdf_comfort_header.tex"),
        help="Optional LaTeX header include file for pandoc PDF generation.",
    )
    parser.add_argument(
        "--synthesize-gpt41",
        action="store_true",
        help="Run optional GPT-4.1 coherence pass before writing output markdown.",
    )
    parser.add_argument(
        "--synthesis-model",
        default="gpt-4.1",
        help="Model for synthesis pass (default: gpt-4.1).",
    )
    parser.add_argument(
        "--synthesis-max-chars",
        type=int,
        default=220000,
        help="Maximum document size for single synthesis pass.",
    )
    parser.add_argument(
        "--no-consistency-note",
        action="store_true",
        help="Disable automatic data-availability context note.",
    )
    parser.add_argument(
        "--analytics-export-json",
        type=Path,
        default=None,
        help="Optional timeline analytics export JSON payload to append as chart images.",
    )
    parser.add_argument(
        "--analytics-export-url",
        default=None,
        help="Optional timeline analytics export URL (POST) returning JSON with charts.",
    )
    parser.add_argument(
        "--analytics-http-timeout-s",
        type=int,
        default=60,
        help="Timeout seconds for analytics export URL fetch.",
    )
    parser.add_argument(
        "--analytics-charts-dir",
        type=Path,
        default=Path("receipts/eohd_analytics_charts"),
        help="Directory where decoded analytics chart PNG files are written.",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    if not args.analytics_charts_dir.is_absolute():
        args.analytics_charts_dir = (repo_root / args.analytics_charts_dir).resolve()

    report_text = args.report_md.read_text(encoding="utf-8", errors="replace")
    receipt_text = args.receipt_md.read_text(encoding="utf-8", errors="replace")
    events = parse_receipt_events(receipt_text)

    step_meta: Dict[str, StepMeta] = {}
    # Primary section ordering must follow first appearance in llm_done payloads.
    step_order: List[str] = []
    step_reports: Dict[str, str] = {}
    patient_id = "UNKNOWN_PATIENT"
    detective_report: Optional[str] = None

    for event, data in events:
        if isinstance(data.get("patient_id"), str):
            patient_id = data["patient_id"]

        if event == "detective_plan":
            for s in data.get("steps", []) or []:
                sid = str(s.get("step_id", "")).strip()
                if not sid:
                    continue
                if sid not in step_order:
                    step_order.append(sid)
                step_meta[sid] = StepMeta(
                    step_id=sid,
                    kind=str(s.get("kind", "")),
                    question_type=str(s.get("question_type", "")),
                    q=str(s.get("q", "")),
                )
        elif event == "detective_step_start":
            sid = str(data.get("step_id", "")).strip()
            if sid:
                if sid not in step_order:
                    step_order.append(sid)
                existing = step_meta.get(sid, StepMeta(step_id=sid))
                existing.kind = str(data.get("kind", existing.kind))
                existing.question_type = str(
                    data.get("question_type", existing.question_type)
                )
                existing.q = str(data.get("q", existing.q))
                step_meta[sid] = existing
        elif event == "llm_done":
            sid = str(data.get("step_id", "")).strip()
            txt = data.get("text")
            if sid and isinstance(txt, str) and txt.strip():
                step_reports[sid] = txt.strip()
                if sid not in step_order:
                    step_order.append(sid)
        elif event == "detective_report":
            rep = data.get("report")
            if isinstance(rep, str) and rep.strip():
                detective_report = rep.strip()

    # If no llm_done sections were captured, fail fast with an explicit signal.
    if not step_reports:
        raise SystemExit(
            "No llm_done phase reports found. Verify receipt file is non-empty and contains SSE events."
        )

    # Emit individual phase markdown files.
    args.emit_step_files_dir.mkdir(parents=True, exist_ok=True)
    for sid in step_order:
        body = step_reports.get(sid, "").strip()
        if not body:
            continue
        meta = step_meta.get(sid, StepMeta(step_id=sid))
        per_step = [
            "---",
            f'title: "EoHD Phase {sid} — {patient_id}"',
            f'date: "{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}"',
            "---",
            "",
            f"# Phase {sid}",
            "",
            f"- Kind: {meta.kind or 'unknown'}",
            f"- Question Type: {meta.question_type or 'unknown'}",
            "",
            "## Prompt",
            "",
            meta.q.strip() or "_No prompt captured._",
            "",
            "## Report",
            "",
            body,
            "",
        ]
        (args.emit_step_files_dir / f"PHASE_{sid}_PDF_READY.md").write_text(
            "\n".join(per_step), encoding="utf-8"
        )

    packet = render_packet(
        patient_id=patient_id,
        main_report_md=report_text,
        main_report_title=args.report_md.name,
        step_order=step_order,
        step_meta=step_meta,
        step_reports=step_reports,
        detective_report=detective_report,
        tone=args.tone,
        include_consistency_note=not args.no_consistency_note,
    )

    # Always emit deterministic baseline packet first.
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(packet, encoding="utf-8")
    print(f"Wrote baseline packet: {args.out_md}")

    if args.out_pdf:
        args.out_pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf_header = args.pdf_header if args.pdf_header and args.pdf_header.exists() else None
        build_pdf(
            in_md=args.out_md,
            out_pdf=args.out_pdf,
            pdf_geometry=args.pdf_geometry,
            pdf_fontsize=args.pdf_fontsize,
            pdf_header=pdf_header,
        )
        print(f"Wrote baseline PDF: {args.out_pdf}")

    if args.synthesize_gpt41:
        original_packet = packet
        synthesized = synthesize_with_gpt41(
            packet_md=packet,
            tone=args.tone,
            model=args.synthesis_model,
            step_order=step_order,
            max_chars=args.synthesis_max_chars,
        )
        valid, reason = _synthesis_is_valid(
            original_packet=original_packet,
            synthesized_packet=synthesized,
            step_order=step_order,
        )
        if valid:
            packet = synthesized
        else:
            print(f"WARNING: GPT-4.1 synthesis rejected ({reason}); using original packet.")

    analytics_payload = _load_analytics_export_payload(
        export_json_path=args.analytics_export_json,
        export_url=args.analytics_export_url,
        timeout_s=args.analytics_http_timeout_s,
    )
    if analytics_payload:
        appendix = _build_analytics_appendix_and_emit_images(
            payload=analytics_payload,
            charts_dir=args.analytics_charts_dir,
            packet_parent_dir=args.out_md.parent,
        )
        if appendix.strip():
            packet = packet.rstrip() + "\n" + appendix.rstrip() + "\n"
            print("Appended timeline analytics charts to packet.")
        else:
            print("WARNING: analytics payload present but no chart images were emitted.")

    args.out_md.write_text(packet, encoding="utf-8")
    print(f"Wrote final packet: {args.out_md}")
    print(f"Phase files: {args.emit_step_files_dir}")
    print(f"Steps captured: {len([s for s in step_order if step_reports.get(s)])}")

    if args.out_pdf:
        pdf_header = args.pdf_header if args.pdf_header and args.pdf_header.exists() else None
        build_pdf(
            in_md=args.out_md,
            out_pdf=args.out_pdf,
            pdf_geometry=args.pdf_geometry,
            pdf_fontsize=args.pdf_fontsize,
            pdf_header=pdf_header,
        )
        print(f"Wrote final PDF: {args.out_pdf}")


if __name__ == "__main__":
    main()

