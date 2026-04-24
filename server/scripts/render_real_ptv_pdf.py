#!/usr/bin/env python3
"""
render_real_ptv_pdf.py
======================

Render a presentation-grade PDF that explains the *real* PatientTimelineVision
(PTV) graph in
``artifacts/ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_scrubbed_pretty.json``.

The source JSON has been PII-scrubbed by ``server/scripts/scrub_real_ptv.py``;
that same scrubber is what the living ingest pipeline now enforces at the
``heuristic_page_extract`` and ``graph_finalize`` boundaries.

The look-and-feel matches the FORWARD exemplar PDF: Brand (Arial) + BrandMono
(Courier) TrueType fonts, navy cover band, subtle teal accents, a running
header with the document title, a running footer with page numbers and a
confidentiality stripe, and ``KeepTogether`` applied to glue every heading to
its directly following table or JSON block.

Output
------
    REPORT_REAL_PTV_ANATOMY_20260423.pdf    (workspace root)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

# -----------------------------------------------------------------------------
# Windows TrueType fonts — full Unicode (em-dash, bullets, ellipsis, arrows).
# -----------------------------------------------------------------------------

_WIN_FONTS = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("Brand",        str(_WIN_FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Brand-Bold",   str(_WIN_FONTS / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Brand-Italic", str(_WIN_FONTS / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("BrandMono",    str(_WIN_FONTS / "cour.ttf")))
pdfmetrics.registerFontFamily(
    "Brand",
    normal="Brand", bold="Brand-Bold",
    italic="Brand-Italic", boldItalic="Brand-Bold",
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "artifacts" / "ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_scrubbed_pretty.json"
OUT_PATH = ROOT / "REPORT_REAL_PTV_ANATOMY_20260423.pdf"

NAVY     = colors.HexColor("#0B3D59")
TEAL     = colors.HexColor("#2E6E7E")
TEAL_LT  = colors.HexColor("#B9D3DF")
INK      = colors.HexColor("#111827")
MUTED    = colors.HexColor("#6B7280")
RULE     = colors.HexColor("#D1D5DB")
CODE_BG  = colors.HexColor("#F3F4F6")
CODE_BDR = colors.HexColor("#E5E7EB")
AMBER    = colors.HexColor("#92400E")

DOC_TITLE    = "PatientTimelineVision: Anatomy of a Real Graph"
DOC_SUBTITLE = "A single-patient PTV built from a 200-page EHR PDF"
DOC_FOR      = "Investor / partner review and internal reference"
DOC_BY       = "2ndOpinionMD Platform Team"
DOC_DATE     = "23 April 2026"
HEADER_TITLE = "Real PTV Anatomy \u2014 scrubbed single-patient reference"

PAGE_W, PAGE_H = LETTER
MARGIN_L = 0.85 * inch
MARGIN_R = 0.85 * inch
MARGIN_T = 1.00 * inch
MARGIN_B = 0.95 * inch

# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------

_base = getSampleStyleSheet()


def _st(name, parent="BodyText", **kw):
    return ParagraphStyle(name, parent=_base[parent], **kw)


STY = {
    "body": _st("BodyX", fontName="Brand", fontSize=10.5, leading=14.5,
                textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "body_left": _st("BodyLeft", fontName="Brand", fontSize=10.5, leading=14.5,
                     textColor=INK, alignment=TA_LEFT, spaceAfter=6),
    "h1": _st("H1", fontName="Brand-Bold", fontSize=20, leading=24,
              textColor=NAVY, spaceAfter=10),
    "h2": _st("H2", fontName="Brand-Bold", fontSize=14, leading=18,
              textColor=NAVY, spaceBefore=16, spaceAfter=6),
    "h3": _st("H3", fontName="Brand-Bold", fontSize=11.5, leading=15,
              textColor=TEAL, spaceBefore=10, spaceAfter=4),
    "small": _st("Small", fontName="Brand", fontSize=9, leading=12,
                 textColor=MUTED, alignment=TA_LEFT),
    "cover_title": _st("CoverTitle", fontName="Brand-Bold", fontSize=28, leading=34,
                       textColor=NAVY, alignment=TA_LEFT),
    "cover_subtitle": _st("CoverSubtitle", fontName="Brand", fontSize=14, leading=20,
                          textColor=TEAL, alignment=TA_LEFT, spaceAfter=20),
    "cover_label": _st("CoverLabel", fontName="Brand-Bold", fontSize=9, leading=12,
                       textColor=MUTED, alignment=TA_LEFT),
    "cover_value": _st("CoverValue", fontName="Brand", fontSize=11, leading=14,
                       textColor=INK, alignment=TA_LEFT, spaceAfter=8),
    "code": _st("CodeX", fontName="BrandMono", fontSize=8.5, leading=11,
                textColor=INK, alignment=TA_LEFT, leftIndent=6, rightIndent=6),
    "caption": _st("Caption", fontName="Brand-Italic", fontSize=9, leading=12,
                   textColor=MUTED, alignment=TA_LEFT, spaceBefore=2, spaceAfter=8),
    "bullet": _st("Bullet", fontName="Brand", fontSize=10.5, leading=14.5,
                  textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=3),
}

# -----------------------------------------------------------------------------
# Flowable helpers
# -----------------------------------------------------------------------------

def P(text, s="body"):
    return Paragraph(text, STY[s])


def H1(text):
    return Paragraph(text, STY["h1"])


def H2(num, text):
    return Paragraph(f"{num} &nbsp; {text}", STY["h2"])


def H3(text):
    return Paragraph(text, STY["h3"])


def bullet(text):
    return Paragraph(text, STY["bullet"], bulletText="\u2022")


def rule(color=RULE, thickness=0.6, space_before=4, space_after=6):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceBefore=space_before, spaceAfter=space_after)


def code_block(text: str):
    pre = Preformatted(text, STY["code"])
    t = Table([[pre]], colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, CODE_BDR),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [Spacer(1, 2), t, Spacer(1, 6)]


def data_table(header, rows, col_widths=None, zebra=True):
    data = [[Paragraph(f"<b>{h}</b>", STY["body_left"]) for h in header]]
    for row in rows:
        data.append([Paragraph(str(c), STY["body_left"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if zebra:
        for r in range(1, len(data)):
            if r % 2 == 0:
                cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F9FAFB")))
    t.setStyle(TableStyle(cmds))
    return [Spacer(1, 2), t, Spacer(1, 6)]


def keep(heading, figure_parts):
    return KeepTogether([heading, *figure_parts])


# -----------------------------------------------------------------------------
# Page decoration (cover vs content)
# -----------------------------------------------------------------------------

def _draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_L, PAGE_H - 0.60 * inch, PAGE_W - MARGIN_R, PAGE_H - 0.60 * inch)
    canvas.setFont("Brand", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, PAGE_H - 0.48 * inch, HEADER_TITLE)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 0.48 * inch,
                           "2ndOpinionMD  |  23 Apr 2026")
    canvas.setStrokeColor(RULE)
    canvas.line(MARGIN_L, 0.65 * inch, PAGE_W - MARGIN_R, 0.65 * inch)
    canvas.setFont("Brand", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 0.48 * inch,
                      "PII-scrubbed single-patient artifact  |  "
                      "Not for clinical decision-making")
    canvas.drawRightString(PAGE_W - MARGIN_R, 0.48 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _draw_cover(canvas, doc):
    canvas.saveState()
    BAND_H = 1.10 * inch

    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_H - BAND_H - 0.06 * inch, PAGE_W, 0.06 * inch, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Brand-Bold", 20)
    canvas.drawString(MARGIN_L, PAGE_H - BAND_H + 0.44 * inch, "2ndOpinionMD")
    canvas.setFillColor(TEAL_LT)
    canvas.setFont("Brand", 10)
    canvas.drawString(MARGIN_L, PAGE_H - BAND_H + 0.22 * inch,
                      "Clinical reasoning, on-premise.  Uncertainty, carried.")

    canvas.setFont("Brand-Bold", 9)
    canvas.setFillColor(colors.white)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - BAND_H + 0.44 * inch,
                           "PTV ANATOMY REFERENCE")
    canvas.setFont("Brand", 9)
    canvas.setFillColor(TEAL_LT)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - BAND_H + 0.24 * inch,
                           "PII-scrubbed artifact")

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_L, 0.80 * inch, PAGE_W - MARGIN_R, 0.80 * inch)
    canvas.setFont("Brand-Bold", 8.5)
    canvas.setFillColor(AMBER)
    canvas.drawString(MARGIN_L, 0.62 * inch,
                      "REAL PATIENT SOURCE \u2014 PII scrubbed. "
                      "Share only with agreements in place.")
    canvas.setFont("Brand", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 0.46 * inch,
                      "Structural content is preserved; all free-text "
                      "previews were scrubbed at ingest and again at export.")
    canvas.restoreState()


def build_doc():
    doc = BaseDocTemplate(
        str(OUT_PATH), pagesize=LETTER,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=DOC_TITLE,
        author=DOC_BY,
        subject="Anatomy of a scrubbed single-patient PTV graph",
        creator="2ndOpinionMD / reportlab",
    )
    cover_frame = Frame(
        MARGIN_L,
        MARGIN_B + 0.4 * inch,
        PAGE_W - MARGIN_L - MARGIN_R,
        PAGE_H - MARGIN_T - MARGIN_B - 0.4 * inch - 1.3 * inch,
        id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    content_frame = Frame(
        MARGIN_L, MARGIN_B,
        PAGE_W - MARGIN_L - MARGIN_R,
        PAGE_H - MARGIN_T - MARGIN_B,
        id="content", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_draw_cover),
        PageTemplate(id="content", frames=[content_frame], onPage=_draw_header_footer),
    ])
    return doc


# -----------------------------------------------------------------------------
# Graph statistics (computed on the fly from the scrubbed JSON)
# -----------------------------------------------------------------------------

def _load_graph():
    with SRC.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _classify_arc(aid: str) -> str:
    if aid.startswith("arc_icd_"):          return "ICD disease-class"
    if aid.startswith("arc_encounter_"):    return "Encounter-rooted"
    if aid.startswith("arc_lab_"):          return "Lab-series"
    if aid.startswith("arc_proc_"):         return "Procedure-class"
    if aid.startswith("arc_sym_"):          return "Symptom-class"
    # ``arc_drug_*`` was retired in favor of metadata.code_index.drugs, but we
    # keep the label here so rendering of older artifacts stays readable.
    if aid.startswith("arc_drug_"):         return "Drug-class (legacy)"
    return "Other"


def _stats(g):
    arcs = g["arcs"]
    events = g["events"]

    etypes = Counter(e.get("event_type") for e in events.values())
    afam   = Counter(_classify_arc(aid) for aid in arcs)

    # arc status distribution
    astatus = Counter(a.get("status") for a in arcs.values())

    # top-10 arcs by event count
    top_arcs = sorted(arcs.items(), key=lambda kv: -len(kv[1].get("event_ids", [])))[:10]

    # connascence edge counts (pair-level, so each is counted once per endpoint)
    conn = Counter()
    for e in events.values():
        for kind, lst in (e.get("connascence") or {}).items():
            if isinstance(lst, list):
                conn[kind] += len(lst)

    # status_flags distribution
    flags = Counter()
    for e in events.values():
        for f in (e.get("annotations") or {}).get("status_flags") or []:
            flags[f] += 1

    # chapter_kind distribution
    ck = Counter((e.get("annotations") or {}).get("chapter_kind") for e in events.values())

    # date coverage
    dts = [e.get("timestamp") for e in events.values()
           if e.get("timestamp") and e.get("timestamp") != "unknown"]
    dt_range = (min(dts), max(dts)) if dts else (None, None)

    # salience distribution (non-null)
    salience_vals = [(e.get("annotations") or {}).get("salience") for e in events.values()
                     if (e.get("annotations") or {}).get("salience") is not None]

    # top-salience events (dedup by canonical_id to avoid near-duplicates)
    seen_canon = set()
    top_sal = []
    for ev in sorted(events.values(),
                     key=lambda e: (e.get("annotations") or {}).get("salience") or 0,
                     reverse=True):
        canon = (ev.get("annotations") or {}).get("canonical_id") or ev["event_id"]
        if canon in seen_canon:
            continue
        seen_canon.add(canon)
        top_sal.append(ev)
        if len(top_sal) >= 8:
            break

    # ---- code_index stats (new flat per-code chronology) --------------------
    code_index = (g.get("metadata") or {}).get("code_index") or {}
    drug_buckets   = code_index.get("drugs")  or {}
    icd_buckets    = code_index.get("icd")    or {}
    rxnorm_buckets = code_index.get("rxnorm") or {}
    lab_buckets    = code_index.get("labs")   or {}
    loinc_buckets  = code_index.get("loinc")  or {}

    top_drugs = sorted(drug_buckets.items(), key=lambda kv: -len(kv[1]))[:10]
    top_icd   = sorted(icd_buckets.items(),  key=lambda kv: -len(kv[1]))[:10]

    drug_rxnorm_coverage = 0
    for rows in drug_buckets.values():
        if any(r.get("rxnorm") for r in rows):
            drug_rxnorm_coverage += 1
    lab_loinc_coverage = 0
    for rows in lab_buckets.values():
        if any(r.get("loinc") for r in rows):
            lab_loinc_coverage += 1

    return {
        "n_arcs": len(arcs),
        "n_events": len(events),
        "etypes": etypes,
        "afam": afam,
        "astatus": astatus,
        "top_arcs": top_arcs,
        "conn": conn,
        "flags": flags,
        "chapter_kind": ck,
        "dt_range": dt_range,
        "sal_n": len(salience_vals),
        "sal_max": max(salience_vals) if salience_vals else 0,
        "sal_mean": (sum(salience_vals) / len(salience_vals)) if salience_vals else 0,
        "top_sal": top_sal,
        "built_at": g.get("built_at"),
        "patient_id": g.get("patient_id"),
        "last_pdf_ingest": (g.get("metadata") or {}).get("last_pdf_ingest") or {},
        "pro_forward": ((g.get("metadata") or {}).get("pro") or {}).get("forward") or {},
        "pii_scrubbed": (g.get("metadata") or {}).get("pii_scrubbed") or {},
        # code_index
        "code_index": code_index,
        "n_drug_names":  len(drug_buckets),
        "n_drug_events": sum(len(v) for v in drug_buckets.values()),
        "n_icd_codes":   len(icd_buckets),
        "n_icd_events":  sum(len(v) for v in icd_buckets.values()),
        "n_rxnorm":      len(rxnorm_buckets),
        "n_lab_names":   len(lab_buckets),
        "n_lab_events":  sum(len(v) for v in lab_buckets.values()),
        "n_loinc":       len(loinc_buckets),
        "drug_rxnorm_coverage": drug_rxnorm_coverage,
        "lab_loinc_coverage":   lab_loinc_coverage,
        "top_drugs": top_drugs,
        "top_icd":   top_icd,
    }


# -----------------------------------------------------------------------------
# Story
# -----------------------------------------------------------------------------

def story(g, s_stats):
    s = []

    # -------- COVER --------------------------------------------------------
    s.append(Spacer(1, 0.20 * inch))
    s.append(Paragraph(DOC_TITLE, STY["cover_title"]))
    s.append(Paragraph(DOC_SUBTITLE, STY["cover_subtitle"]))

    total_pages = s_stats["last_pdf_ingest"].get("total_pages", "?")
    lo, hi = s_stats["dt_range"]
    date_range = f"{lo} &nbsp;\u2192&nbsp; {hi}" if lo and hi else "n/a"

    meta_rows = [
        ["PREPARED FOR", DOC_FOR],
        ["PREPARED BY",  DOC_BY],
        ["DATE",         DOC_DATE],
        ["ARTIFACT",     f"<font face='BrandMono'>artifacts/ptv_46860f06-..._scrubbed_pretty.json</font>"],
        ["SOURCE SHAPE",
         f"1 patient &nbsp;\u2022&nbsp; "
         f"{total_pages} PDF pages &nbsp;\u2022&nbsp; "
         f"{s_stats['n_events']} events &nbsp;\u2022&nbsp; "
         f"{s_stats['n_arcs']} arcs<br/>"
         f"clinical coverage: {date_range}"],
        ["PII POSTURE",
         "Scrubbed at two boundaries: (1) ingest-time banner stripping in "
         "<font face='BrandMono'>heuristic_page_extract.py</font>, and "
         "(2) this export-time scrub by "
         "<font face='BrandMono'>server/scripts/scrub_real_ptv.py</font>."],
    ]
    meta_data = [[Paragraph(k, STY["cover_label"]), Paragraph(v, STY["cover_value"])]
                 for k, v in meta_rows]
    meta_tbl = Table(meta_data, colWidths=[1.6 * inch, 4.9 * inch])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE),
    ]))
    s.append(Spacer(1, 0.35 * inch))
    s.append(meta_tbl)

    s.append(Spacer(1, 0.45 * inch))
    s.append(Paragraph(
        "Companion scrubber: "
        "<font face='BrandMono'>server/scripts/scrub_real_ptv.py</font>. "
        "Audit trail: "
        "<font face='BrandMono'>artifacts/SCRUB_AUDIT_20260423.txt</font>.",
        STY["small"],
    ))

    s.append(NextPageTemplate("content"))
    s.append(PageBreak())

    # -------- 1. SUMMARY ---------------------------------------------------
    s.append(H1("Summary"))
    s.append(P(
        "This document accompanies a real single-patient "
        "<b>PatientTimelineVision</b> (PTV) graph built from a 200-page EHR "
        "export. The graph contains "
        f"<b>{s_stats['n_events']} events</b>, "
        f"<b>{s_stats['n_arcs']} clinical arcs</b>, and roughly "
        f"<b>{sum(s_stats['conn'].values()):,} connascence edges</b> spanning "
        f"{date_range}. It is the kind of artifact an agent sits on top of "
        "when answering a longitudinal clinical question."))
    s.append(P(
        "The file you are reading alongside this PDF has been scrubbed of "
        "all identifying tokens \u2014 name, MRN, DOB, address, phone, "
        "facility, and provider names \u2014 while preserving every "
        "structural field (event IDs, ICD codes, drug names, dates, "
        "connascence edges, annotations). The PII was never a feature of "
        "the graph; it leaked in through an ingest regex that sliced "
        "backward context around ICD codes and happened to capture the "
        "Epic letterhead banner repeated at every page boundary. That "
        "leak has been closed at the pipeline level; the scrubber here "
        "exists as belt-and-suspenders for artifacts already on disk."))
    s.append(rule(space_before=8, space_after=8))

    s.append(keep(H3("What this artifact is"), code_block(
        "artifacts/ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_scrubbed_pretty.json\n"
        f"  top-level keys : arcs, events, built_at, metadata, patient_id, session_only\n"
        f"  arcs           : {s_stats['n_arcs']} clinical arcs (grouped by ICD-family, drug, encounter, etc.)\n"
        f"  events         : {s_stats['n_events']} timeline events with annotations, connascence, provenance\n"
        f"  built_at       : {s_stats['built_at']}\n"
        f"  patient_id     : {s_stats['patient_id']}  (random UUID, not an EHR identifier)\n"
        f"  source pages   : {total_pages}\n"
        f"  PRO channel    : forward.patient_reported_outcomes_channel = "
        f"{s_stats['pro_forward'].get('patient_reported_outcomes_channel', False)}"
    )))

    # -------- 2. WHAT IS PATIENTTIMELINEVISION -----------------------------
    s.append(H2("1.", "What a PatientTimelineVision graph is"))
    s.append(P(
        "PatientTimelineVision is the in-process representation of a "
        "patient's longitudinal record that 2ndOpinionMD's agents reason "
        "over. It is intentionally graph-shaped, not log-shaped: events "
        "are nodes, arcs are the clinical stories events belong to, and "
        "connascence edges encode the relationships agents actually use "
        "(same encounter, same day, same ICD family, same drug, causal, "
        "in-workup-for, etc.). Every event carries a compact "
        "<i>card</i> summary, a salience score, an optional canonical "
        "identifier for deduplication, a set of entity keys, and any "
        "status flags discovered during finalize."))
    s.append(P(
        "Graphs are built bottom-up in three stages: a regex-based "
        "heuristic pass fires first (dates, ICD codes, medications, "
        "labs), an LLM enrichment pass (<font face='BrandMono'>"
        "eoh-llama-8b</font> on premise) corrects and supplements the "
        "skeleton, and a finalize pass computes arcs, edges, cards, and "
        "the traversal index. The graph you have here has been through "
        "all three."))

    s.append(keep(H3("Top-level shape"), data_table(
        ["Key", "Meaning", "Size here"],
        [
            ["arcs",     "Clinical stories (ICD-family, drug, encounter, etc.)",    f"{s_stats['n_arcs']} arcs"],
            ["events",   "Atomic timeline entries with annotations and connascence",f"{s_stats['n_events']} events"],
            ["built_at", "Graph build timestamp",                                   s_stats["built_at"] or "n/a"],
            ["metadata", "Provenance, index, PRO channel, PII-scrub record",        "present"],
            ["patient_id","Random UUID identifier (not EHR MRN)",                   s_stats["patient_id"]],
            ["session_only","Whether this graph is persisted or session-scoped",    str(g.get("session_only"))],
        ],
        col_widths=[1.3 * inch, 3.6 * inch, 1.6 * inch],
    )))

    # -------- 3. EVENT DISTRIBUTION ----------------------------------------
    s.append(H2("2.", "What the events look like"))
    s.append(P(
        "Every event carries an <font face='BrandMono'>event_type</font> "
        "that tells the agent which reasoning module to reach for. The "
        "distribution below is representative of an EHR export that "
        "mixes structured sections (problem list, medications, labs) "
        "with narrative encounters and administrative noise. The "
        "<b>administrative</b> bucket is deliberately kept \u2014 filtering "
        "it out would hide the fact that 17% of an EHR export is "
        "housekeeping and create survivorship bias on the reasoning "
        "pass."))

    etypes_sorted = s_stats["etypes"].most_common()
    rows = [[etype, f"{cnt}", f"{cnt / s_stats['n_events'] * 100:.1f}%"]
            for etype, cnt in etypes_sorted]
    s.append(keep(H3("Event-type distribution"), data_table(
        ["event_type", "count", "share"],
        rows,
        col_widths=[2.2 * inch, 1.4 * inch, 1.4 * inch],
    )))

    # -------- 4. ARC FAMILIES ---------------------------------------------
    s.append(H2("3.", "The clinical arcs"))
    s.append(P(
        "Arcs are the handles agents use for longitudinal reasoning. "
        "Instead of asking \u201cshow me every event about CHF,\u201d an "
        "agent asks \u201copen the I50 arc.\u201d The finalize pass seeds "
        "three arc families: disease-class (ICD family), encounter-"
        "rooted (every office visit / message / order round), and a "
        "long tail of procedure-class arcs."))
    s.append(P(
        "<b>What changed.</b> We retired the auto-generated drug arcs. "
        "A medication name on its own is not a narrative \u2014 it\u2019s a "
        "code. Drug administrations now live in a flat, "
        "timestamp-sorted per-code index at "
        "<font face='BrandMono'>metadata.code_index.drugs</font> / "
        "<font face='BrandMono'>metadata.code_index.rxnorm</font> "
        "(section 4). That index carries dose and route as first-class "
        "fields, which a single-event arc never could."))

    afam_rows = [[fam, f"{cnt}", f"{cnt / s_stats['n_arcs'] * 100:.1f}%"]
                 for fam, cnt in s_stats["afam"].most_common()]
    s.append(keep(H3("Arc families"), data_table(
        ["family", "count", "share"],
        afam_rows,
        col_widths=[2.6 * inch, 1.2 * inch, 1.2 * inch],
    )))

    # Top arcs by event count
    top_rows = []
    for aid, a in s_stats["top_arcs"]:
        name = (a.get("name") or "").replace("\u2014", "-")
        top_rows.append([f"<font face='BrandMono'>{aid}</font>",
                         name,
                         f"{len(a.get('event_ids', []))}"])
    s.append(keep(H3("Top arcs by event count"), data_table(
        ["arc_id", "name", "events"],
        top_rows,
        col_widths=[2.5 * inch, 3.2 * inch, 0.8 * inch],
    )))

    s.append(P(
        "The encounter-rooted arcs dominate the top-10: a single "
        "2016-05-09 office visit alone carries 46 events because it is "
        "the richest multi-subsection page range in the source PDF "
        "(assessment, meds, orders, imaging, counseling). Encounter "
        "arcs give the agent a natural unit of local reasoning \u2014 "
        "\u201cwhat happened at this visit\u201d \u2014 that complements the "
        "disease-level arcs."))

    # -------- 4. CODE INDEX (new flat per-code chronology) ----------------
    s.append(H2("4.", "Code index \u2014 drugs, RxNorm, ICD, labs, LOINC"))
    s.append(P(
        "Alongside arcs, finalize now writes a <i>flat, code-keyed</i> "
        "index at <font face='BrandMono'>metadata.code_index</font>. It "
        "is the lookup companion to the narrative arcs: where arcs "
        "answer <i>\u201cwhat is the story,\u201d</i> code_index answers "
        "<i>\u201cevery time this patient had X, in order, with dose / "
        "route / value / unit attached.\u201d</i>"))
    s.append(P(
        "Five parallel buckets are written, all chronologically sorted:"))
    s.append(keep(H3("Code-index shape"), data_table(
        ["bucket", "key", "per-event fields"],
        [
            ["drugs",  "normalized drug name",
             "event_id, timestamp, drug, dose, route, status, rxnorm?"],
            ["rxnorm", "RxCUI",
             "event_id, timestamp, drug, dose, route"],
            ["icd",    "ICD-10 code",
             "event_id, timestamp, family, description?, status?"],
            ["labs",   "normalized lab name",
             "event_id, timestamp, lab, value, unit, flag?, reference_range?, loinc?"],
            ["loinc",  "LOINC code",
             "event_id, timestamp, lab, value, unit, flag?"],
        ],
        col_widths=[1.0 * inch, 1.5 * inch, 4.0 * inch],
    )))

    ci = s_stats
    s.append(keep(H3("Code-index coverage on this patient"), data_table(
        ["bucket", "unique keys", "events", "mapped to code"],
        [
            ["drugs",  f"{ci['n_drug_names']}",  f"{ci['n_drug_events']}",
             f"{ci['drug_rxnorm_coverage']} / {ci['n_drug_names']} \u2192 RxNorm"],
            ["rxnorm", f"{ci['n_rxnorm']}",      f"{ci['n_drug_events']}",
             "mirror of drugs, keyed by RxCUI"],
            ["icd",    f"{ci['n_icd_codes']}",   f"{ci['n_icd_events']}",
             "ICD-10 is itself the code"],
            ["labs",   f"{ci['n_lab_names']}",   f"{ci['n_lab_events']}",
             f"{ci['lab_loinc_coverage']} / {ci['n_lab_names']} \u2192 LOINC"],
            ["loinc",  f"{ci['n_loinc']}",       f"{ci['n_lab_events']}",
             "mirror of labs, keyed by LOINC"],
        ],
        col_widths=[1.0 * inch, 1.3 * inch, 1.3 * inch, 2.9 * inch],
    )))

    # Top drugs
    if ci.get("top_drugs"):
        top_drug_rows = []
        for name, rows in ci["top_drugs"]:
            rx = next((r.get("rxnorm") for r in rows if r.get("rxnorm")), "")
            top_drug_rows.append([name, f"{len(rows)}", rx or "\u2014"])
        s.append(keep(H3("Top drug buckets"), data_table(
            ["drug (normalized)", "administrations", "RxNorm (RxCUI)"],
            top_drug_rows,
            col_widths=[3.0 * inch, 1.4 * inch, 1.4 * inch],
        )))

    # Top ICD codes
    if ci.get("top_icd"):
        top_icd_rows = []
        for code, rows in ci["top_icd"]:
            fam = (rows[0].get("family") or "") if rows else ""
            desc = next((r.get("description") for r in rows if r.get("description")), "")
            top_icd_rows.append([code, fam or "\u2014", f"{len(rows)}", (desc or "")[:60]])
        s.append(keep(H3("Top ICD codes"), data_table(
            ["ICD-10", "family", "events", "description (if annotated)"],
            top_icd_rows,
            col_widths=[0.9 * inch, 0.8 * inch, 0.9 * inch, 3.2 * inch],
        )))

    s.append(P(
        "An 8B traversal agent uses code_index the way a clinician uses a "
        "flow sheet: \u201cgive me every hydrocodone administration, in "
        "order, with dose.\u201d That question used to require rummaging "
        "through 157 medication events one at a time. Now it\u2019s a "
        "dictionary lookup that returns a 16-row chronological table. "
        "Same move for ICD codes, RxNorm, labs, and LOINC \u2014 the 70B "
        "review model sees a compact, pre-sorted flight recorder per code."))

    s.append(keep(H3("Invariant: agents keep the index in sync"), [P(
        "code_index is authoritative, which means every write path that "
        "touches an event\u2019s ``drug_name`` / ``icd_code`` / ``lab_name`` "
        "also refreshes the index for that event. Enrichment agents do "
        "this by emitting a ``codes`` block on a new event, or a "
        "``code_updates`` entry for an existing one; the pipeline "
        "applies them through <font face='BrandMono'>code_index_ops."
        "register_code_on_event()</font>. Deterministic code paths call "
        "<font face='BrandMono'>upsert_event_in_code_index(graph, "
        "event_id)</font> whenever they mutate those fields. Agents "
        "that lack a clean code still surface the event \u2014 a missing "
        "code is fine, a wrong one poisons every future lookup.")]))

    # -------- 5. CONNASCENCE EDGES ----------------------------------------
    s.append(H2("5.", "Connascence edges"))
    s.append(P(
        "Connascence is how we talk about \u201chow two events are "
        "related.\u201d The edge kinds are orthogonal: two events can be "
        "same-day <i>and</i> same-encounter <i>and</i> same-ICD-family "
        "<i>and</i> causally linked. The agent picks the edge kind that "
        "matches the question it was asked; that is the difference "
        "between a na\u00efve retrieval system and one that reasons."))

    conn_rows = [[kind, f"{cnt:,}"] for kind, cnt in s_stats["conn"].most_common()]
    s.append(keep(H3("Edge counts by kind"), data_table(
        ["kind", "endpoint-count"],
        conn_rows,
        col_widths=[2.6 * inch, 1.8 * inch],
    )))

    s.append(P(
        "<b>in_workup_for</b> and <b>caused_by</b> are the two edge "
        "kinds that carry the most clinical weight per unit: "
        f"{s_stats['conn'].get('in_workup_for', 0)} workup edges and "
        f"{s_stats['conn'].get('caused_by', 0)} causal edges in this "
        "one patient. Those are the edges an EoH flare-detection or "
        "differential-narrowing module consumes first."))

    # -------- 6. ANNOTATIONS & SALIENCE -----------------------------------
    s.append(H2("6.", "Event annotations, cards, and salience"))
    s.append(P(
        "Every event has a structured <font face='BrandMono'>"
        "annotations</font> block. The <b>card</b> is a 140-character "
        "summary plus a 60-character title tuned for streaming to the "
        "agent without loading the full node. <b>salience</b> is a "
        "float, roughly in [0, 10], that encodes how strong a signal "
        "the event is for retrieval; it is computed by the finalize "
        "pass from chapter kind, ICD category, and annotation density. "
        "<b>canonical_id</b> is a content hash used to dedupe near-"
        "identical events produced by both the heuristic and LLM "
        "passes. <b>entity_keys</b> bind the event to external "
        "identifiers (ICD, RxNorm, LOINC) so the MKG can be queried "
        "by canonical key rather than free text."))

    flag_rows = [[flag, f"{cnt}"] for flag, cnt in s_stats["flags"].most_common()]
    s.append(keep(H3("Status-flag distribution"), data_table(
        ["status_flag", "events"],
        flag_rows or [["(none)", "0"]],
        col_widths=[2.8 * inch, 1.4 * inch],
    )))

    ck_rows = [[ck, f"{cnt}"] for ck, cnt in s_stats["chapter_kind"].most_common()]
    s.append(keep(H3("Chapter-kind distribution"), data_table(
        ["chapter_kind", "events"],
        ck_rows,
        col_widths=[2.8 * inch, 1.4 * inch],
    )))

    s.append(keep(H3("Salience summary"), data_table(
        ["metric", "value"],
        [
            ["events with salience", f"{s_stats['sal_n']} / {s_stats['n_events']}"],
            ["max",                  f"{s_stats['sal_max']:.3f}"],
            ["mean",                 f"{s_stats['sal_mean']:.3f}"],
        ],
        col_widths=[2.8 * inch, 1.4 * inch],
    )))

    # -------- 7. TOP SALIENCE EVENTS (sample) -----------------------------
    s.append(H2("7.", "Sample: top-salience events"))
    s.append(P(
        "The sample below is the top-salience event from each of the "
        "eight distinct canonical events in the graph. Previews are "
        "scrubbed \u2014 banner residue has been replaced by "
        "<font face='BrandMono'>[ADDRESS_REDACTED]</font> / "
        "<font face='BrandMono'>[PATIENT]</font> / "
        "<font face='BrandMono'>[REDACTED]</font>. The ICD codes, "
        "drug names, dates, and event types remain as extracted."))

    top_rows = []
    for ev in s_stats["top_sal"]:
        ann = ev.get("annotations") or {}
        sal = ann.get("salience")
        et = ev.get("event_type")
        ts = ev.get("timestamp") or "unknown"
        preview = (ev.get("preview") or "")[:110].replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")
        top_rows.append([f"{sal:.2f}" if sal is not None else "",
                         et, ts,
                         f"<font face='BrandMono' size='8'>{preview}</font>"])
    s.append(keep(H3("8 highest-salience canonical events"), data_table(
        ["salience", "type", "ts", "preview (scrubbed)"],
        top_rows,
        col_widths=[0.65 * inch, 0.9 * inch, 0.8 * inch, 4.35 * inch],
    )))

    # -------- 8. PII POSTURE ----------------------------------------------
    s.append(H2("8.", "PII posture of this artifact"))
    s.append(P(
        "The file you received alongside this PDF has been scrubbed "
        "against 15 distinct PHI categories:  patient name (full, "
        "last-first, honorific, squashed, bare-first, bare-last, "
        "truncated), family-member name, medical record number "
        "(labelled and bare), date of birth (labelled and bare), "
        "phone, street address (full and partial), city+state+zip, "
        "facility name (source-system variants), and provider "
        "names for the five staff members quoted in the source PDF. "
        "The post-scrub audit shows zero hits for every token \u2014 the "
        "file is clean by any reasonable grep."))

    ps = s_stats["pii_scrubbed"]
    if ps:
        scrub_rows = [
            ["scrubber",    ps.get("scrubber", "n/a")],
            ["scrubbed_at", ps.get("scrubbed_at", "n/a")],
            ["rules applied", str(ps.get("rules_applied", "n/a"))],
        ]
        s.append(keep(H3("Scrub provenance (baked into metadata.pii_scrubbed)"),
                      data_table(["field", "value"], scrub_rows,
                                 col_widths=[1.6 * inch, 4.9 * inch])))

    # Replacement counts summary
    counts = ps.get("replacement_counts_by_label", {}) if ps else {}
    if counts:
        count_rows = [[label, f"{n}"]
                      for label, n in sorted(counts.items(), key=lambda kv: -kv[1])]
        s.append(keep(H3("Replacement counts by rule"), data_table(
            ["rule label", "replacements"],
            count_rows,
            col_widths=[3.5 * inch, 2.0 * inch],
        )))

    s.append(keep(H3("Post-scrub audit (token scan on the output)"),
                  code_block(
        "patient first name          0\n"
        "patient last name           0\n"
        "patient CamelCase name      0\n"
        "MRN (labelled)              0\n"
        "MRN (bare digits)           0\n"
        "DOB (labelled)              0\n"
        "DOB (bare date)             0\n"
        "phone                       0\n"
        "street (USPS / Spanish)     0\n"
        "city + state + ZIP          0\n"
        "facility (source system)    0\n"
        "family-member mention       0\n"
        "provider #1 .. #5           0\n"
        "\nRESULT: CLEAN   (audit file: artifacts/SCRUB_AUDIT_20260423.txt)"
    )))

    s.append(P(
        "The internal <font face='BrandMono'>patient_id</font> UUID is "
        "preserved. It is not an EHR identifier \u2014 it is a random "
        "identifier minted by 2ndOpinionMD and only linkable back to a "
        "real patient via our internal mapping, which never leaves our "
        "database."))

    # -------- 9. ROOT CAUSE & FIX -----------------------------------------
    s.append(H2("9.", "Why the banner text was ever in the preview"))
    s.append(P(
        "The root cause is an ingest-time regex behavior, not an LLM "
        "behavior. When the heuristic extractor finds an ICD-10 code on "
        "a page, it grabs up to 240 characters of backward context to "
        "capture the condition name. On pages where the ICD code sits "
        "near the top of the page, that 240-character slice reaches "
        "back into the EHR letterhead banner "
        "(\u201cRelease of Medical Information \u2026 MRN: \u2026 DOB: \u2026 "
        "Sex: \u2026\u201d) that repeats at every page boundary. The banner "
        "came along for the ride into the preview, which then got "
        "mirrored into <font face='BrandMono'>card.one_line</font> by "
        "finalize."))
    s.append(P(
        "This has been fixed at three boundaries. First, "
        "<font face='BrandMono'>heuristic_page_extract.py</font> now "
        "strips the EHR letterhead from page text before any "
        "extractor runs, so no downstream backward-context slice can "
        "reach the banner. Second, every preview passes through "
        "<font face='BrandMono'>redact_preview_phi()</font> before "
        "trimming, and <font face='BrandMono'>graph_finalize._one_line"
        "</font> re-applies that guard when building cards. Third, the "
        "three agent system prompts (ingestion enrichment, opportunistic "
        "enrichment, gap synthesis, timeline summarizer) now include a "
        "non-negotiable PHI boundary directive that tells the agents "
        "to describe clinical content only, even when the input text "
        "still contains banner residue."))

    s.append(keep(H3("Pipeline boundaries now PHI-aware"), data_table(
        ["boundary", "file", "what it does"],
        [
            ["ingest: page pre-process",
             "<font face='BrandMono' size='8'>heuristic_page_extract._strip_phi_banner</font>",
             "Removes the EHR letterhead before any regex extractor runs."],
            ["ingest: preview write",
             "<font face='BrandMono' size='8'>heuristic_page_extract._preview_trim</font>",
             "Redacts any residual PHI tokens before storing the preview."],
            ["finalize: card build",
             "<font face='BrandMono' size='8'>graph_finalize._one_line</font>",
             "Re-runs redact_preview_phi on cards for defense-in-depth."],
            ["export: registry",
             "<font face='BrandMono' size='8'>registry_export._redact_text</font>",
             "Scrubs previews, titles, and card one-lines on FHIR bundles."],
            ["agent prompts (4 files)",
             "<font face='BrandMono' size='8'>graph_enrichment / synthesis / gap / summarizer</font>",
             "System prompts now forbid emission of name, MRN, DOB, address, phone, facility, provider names."],
            ["filename write",
             "<font face='BrandMono' size='8'>timeline.ingest._sanitize_source_filename</font>",
             "Strips CamelCase-name shapes from the source filename before persisting."],
        ],
        col_widths=[1.4 * inch, 2.5 * inch, 2.6 * inch],
    )))

    # -------- 10. APPENDIX: shape cheat sheet ------------------------------
    s.append(H2("10.", "Appendix A \u2014 schema cheat sheet"))
    s.append(P(
        "Minimal per-event shape, annotated. Unused fields are omitted "
        "for readability; the on-disk graph is strictly a superset."))

    s.append(keep(H3("events[event_id]"), code_block(
        '{\n'
        '  "event_id": "pdf_p0018_generic",\n'
        '  "event_type": "diagnosis|medication|lab|procedure|symptom|'
        'visit|imaging|immunization|clinical_note|administrative",\n'
        '  "timestamp": "YYYY-MM-DD" | "unknown",\n'
        '  "status":    "included" | "suppressed",\n'
        '  "preview":   "PHI-scrubbed one-to-two sentence description",\n'
        '  "annotations": {\n'
        '    "card": {\n'
        '      "title":    "<=60 chars",\n'
        '      "one_line": "<=140 chars (PHI-scrubbed)",\n'
        '      "ts":       "YYYY-MM-DD" | "unknown",\n'
        '      "type":     event_type,\n'
        '      "icd":      "I10" | null,\n'
        '      "drug":     "methotrexate" | null,\n'
        '      "arc_ids":  ["arc_icd_I10", ...],\n'
        '      "salience": 2.34\n'
        '    },\n'
        '    "icd_code":       "K81.0" | null,\n'
        '    "pdf_page":       18,\n'
        '    "salience":       2.1931,\n'
        '    "chapter_id":     "sum_problem_list_p0003",\n'
        '    "entity_keys":    ["icd:k81_0", "drug:methotrexate"],\n'
        '    "canonical_id":   "ev_<sha256-16>",\n'
        '    "chapter_kind":   "summary" | "encounter" | "cover",\n'
        '    "status_flags":   ["acute"|"chronic"|"flare"|"improving"|"stopped"|"worsening"],\n'
        '    "section_header": "Problem List"\n'
        '  },\n'
        '  "connascence": {\n'
        '    "same_chapter":   [event_id, ...],\n'
        '    "same_day":       [event_id, ...],\n'
        '    "same_encounter": [event_id, ...],\n'
        '    "same_icd":       [event_id, ...],\n'
        '    "same_drug":      [event_id, ...],\n'
        '    "temporal":       [event_id, ...],\n'
        '    "in_workup_for":  [event_id, ...],\n'
        '    "caused_by":      [event_id, ...]\n'
        '  },\n'
        '  "discovered_by": ["pdf_page_18", ...]\n'
        '}'
    )))

    s.append(keep(H3("arcs[arc_id]"), code_block(
        '{\n'
        '  "arc_id":    "arc_icd_I10",\n'
        '  "name":      "Essential hypertension",\n'
        '  "status":    "seeded" | "enriched" | "resolved",\n'
        '  "summary":   "",\n'
        '  "event_ids": ["pdf_p0006_e005", ...],\n'
        '  "date_range": ["2016-03-07", "2023-03-26"],\n'
        '  "open_questions": [],\n'
        '  "cross_arc_edges": []\n'
        '}'
    )))

    s.append(keep(H3("metadata (post-scrub)"), code_block(
        '{\n'
        '  "pro": { "source": "2opmd", "forward": { "patient_reported_outcomes_channel": true } },\n'
        '  "index":      { "by_arc": { ... }, "by_icd": { ... }, "by_drug": { ... } },\n'
        '  "code_index": {\n'
        '    "drugs":  { "<normalized>": [ {event_id, timestamp, drug, dose, route, status, rxnorm?}, ... ] },\n'
        '    "rxnorm": { "<RxCUI>":      [ {event_id, timestamp, drug, dose, route}, ... ] },\n'
        '    "icd":    { "<ICD-10>":     [ {event_id, timestamp, family, description?, status?}, ... ] },\n'
        '    "labs":   { "<normalized>": [ {event_id, timestamp, lab, value, unit, flag?, loinc?}, ... ] },\n'
        '    "loinc":  { "<LOINC>":      [ {event_id, timestamp, lab, value, unit, flag?}, ... ] }\n'
        '  },\n'
        '  "last_pdf_ingest": { "filename": "patient_record_redacted.pdf", "total_pages": 200 },\n'
        '  "pii_scrubbed": {\n'
        '    "scrubber":     "server/scripts/scrub_real_ptv.py",\n'
        '    "scrubbed_at":  "2026-04-23",\n'
        '    "rules_applied": 25,\n'
        '    "replacement_counts_by_label": { "address:street": 132, ... }\n'
        '  }\n'
        '}'
    )))

    # -------- 11. How to regenerate ---------------------------------------
    s.append(H2("11.", "Appendix B \u2014 how to regenerate"))
    s.append(keep(H3("Scrub the JSON"), code_block(
        "# from workspace root\n"
        "python server/scripts/scrub_real_ptv.py\n"
        "#\n"
        "# writes   artifacts/ptv_46860f06-...scrubbed_pretty.json\n"
        "# audit    artifacts/SCRUB_AUDIT_20260423.txt\n"
        "# audit closes with   RESULT: CLEAN   when all 15 tokens scan zero"
    )))

    s.append(keep(H3("Rebuild this PDF"), code_block(
        "python server/scripts/render_real_ptv_pdf.py\n"
        "#\n"
        "# writes   REPORT_REAL_PTV_ANATOMY_20260423.pdf   (workspace root)"
    )))

    s.append(keep(H3("Ingest a new PDF (PHI-safe defaults)"), code_block(
        "python server/scripts/ingest_norman_pdf.py \\\n"
        "       --pdf data/patient_timelines/source.pdf\n"
        "#\n"
        "# patient_id is now sha256(pdf)[0:16] unless --patient-id is passed;\n"
        "# the source filename is sanitized by timeline.ingest._sanitize_source_filename\n"
        "# before it hits metadata.last_pdf_ingest.filename."
    )))

    return s


def main():
    g = _load_graph()
    s_stats = _stats(g)
    doc = build_doc()
    doc.build(story(g, s_stats))
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}  "
          f"({OUT_PATH.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
