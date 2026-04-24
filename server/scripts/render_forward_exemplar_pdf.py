#!/usr/bin/env python3
"""
render_forward_exemplar_pdf.py
==============================

Render a presentation-grade PDF version of the FORWARD exemplar cohort report
for Kaleb Michaud's RA-conference and Congressional materials.

The PDF is a standalone deliverable: cover page, typeset tables, real code
blocks, running header/footer with page numbers, and an appendix with the
screenshot-ready JSON snippets.  The only forced page break is the transition
from the cover template to the body template.  Elsewhere, subsection titles are
kept with their table or JSON block using ReportLab's KeepTogether so a heading
is not orphaned at the bottom of a page.  Very tall blocks may still move as a
unit to the next page if they do not fit.
It intentionally does not duplicate the slide-ready HANDOUT markdown file,
which stays as a light on-hand companion.

Usage
-----
    python server/scripts/render_forward_exemplar_pdf.py

Output
------
    REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.pdf    (workspace root)
"""

from __future__ import annotations

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
# Windows TrueType fonts for full Unicode coverage (em-dashes, bullets, etc.)
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
OUT_PATH = ROOT / "REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.pdf"

NAVY     = colors.HexColor("#0B3D59")
TEAL     = colors.HexColor("#2E6E7E")
TEAL_LT  = colors.HexColor("#B9D3DF")
INK      = colors.HexColor("#111827")
MUTED    = colors.HexColor("#6B7280")
RULE     = colors.HexColor("#D1D5DB")
CODE_BG  = colors.HexColor("#F3F4F6")
CODE_BDR = colors.HexColor("#E5E7EB")
AMBER    = colors.HexColor("#92400E")

DOC_TITLE    = "FORWARD Exemplar Cohort"
DOC_SUBTITLE = "Five Patients \u00d7 Five Years of Patient-Reported Outcomes"
DOC_FOR      = "Dr. Kaleb Michaud, PhD   |   FORWARD / UNMC Rheumatology"
DOC_BY       = "2ndOpinionMD Platform Team"
DOC_DATE     = "22 April 2026"
HEADER_TITLE = "FORWARD Exemplar Cohort for Dr. Michaud"

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
    "body": _st(
        "BodyX", fontName="Brand", fontSize=10.5, leading=14.5,
        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6,
    ),
    "body_left": _st(
        "BodyLeft", fontName="Brand", fontSize=10.5, leading=14.5,
        textColor=INK, alignment=TA_LEFT, spaceAfter=6,
    ),
    "h1": _st(
        "H1", fontName="Brand-Bold", fontSize=20, leading=24,
        textColor=NAVY, spaceAfter=10,
    ),
    "h2": _st(
        "H2", fontName="Brand-Bold", fontSize=14, leading=18,
        textColor=NAVY, spaceBefore=16, spaceAfter=6,
    ),
    "h3": _st(
        "H3", fontName="Brand-Bold", fontSize=11.5, leading=15,
        textColor=TEAL, spaceBefore=10, spaceAfter=4,
    ),
    "small": _st(
        "Small", fontName="Brand", fontSize=9, leading=12,
        textColor=MUTED, alignment=TA_LEFT,
    ),
    "cover_title": _st(
        "CoverTitle", fontName="Brand-Bold", fontSize=30, leading=36,
        textColor=NAVY, alignment=TA_LEFT,
    ),
    "cover_subtitle": _st(
        "CoverSubtitle", fontName="Brand", fontSize=15, leading=20,
        textColor=TEAL, alignment=TA_LEFT, spaceAfter=20,
    ),
    "cover_label": _st(
        "CoverLabel", fontName="Brand-Bold", fontSize=9, leading=12,
        textColor=MUTED, alignment=TA_LEFT,
    ),
    "cover_value": _st(
        "CoverValue", fontName="Brand", fontSize=11, leading=14,
        textColor=INK, alignment=TA_LEFT, spaceAfter=8,
    ),
    "code": _st(
        "CodeX", fontName="BrandMono", fontSize=8.5, leading=11,
        textColor=INK, alignment=TA_LEFT, leftIndent=6, rightIndent=6,
    ),
    "caption": _st(
        "Caption", fontName="Brand-Italic", fontSize=9, leading=12,
        textColor=MUTED, alignment=TA_LEFT, spaceBefore=2, spaceAfter=8,
    ),
    "bullet": _st(
        "Bullet", fontName="Brand", fontSize=10.5, leading=14.5,
        textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=3,
    ),
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

def code_block(text):
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


def keep_heading_with_figure(heading, figure_parts):
    """Glue a heading to the following table or code block (no hard page break)."""
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
                           "2ndOpinionMD  |  22 Apr 2026")
    canvas.setStrokeColor(RULE)
    canvas.line(MARGIN_L, 0.65 * inch, PAGE_W - MARGIN_R, 0.65 * inch)
    canvas.setFont("Brand", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 0.48 * inch,
                      "Synthetic exemplar cohort  |  Not for clinical decision-making  |  SSRN 6554940")
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
                           "FORWARD PILOT 2026")
    canvas.setFont("Brand", 9)
    canvas.setFillColor(TEAL_LT)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - BAND_H + 0.24 * inch,
                           "Confidential \u2014 for Dr. K. Michaud")

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_L, 0.80 * inch, PAGE_W - MARGIN_R, 0.80 * inch)
    canvas.setFont("Brand-Bold", 8.5)
    canvas.setFillColor(AMBER)
    canvas.drawString(MARGIN_L, 0.62 * inch,
                      "SYNTHETIC COHORT \u2014 Programmatically generated for demonstration and pilot-shape review.")
    canvas.setFont("Brand", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 0.46 * inch,
                      "No real patient records were used. Not for clinical decision-making.")
    canvas.restoreState()

def build_doc():
    doc = BaseDocTemplate(
        str(OUT_PATH), pagesize=LETTER,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title="FORWARD Exemplar Cohort for Dr. Michaud",
        author="2ndOpinionMD Platform Team",
        subject="FORWARD RA 2026 pilot exemplar (5 patients x 5 years PROs)",
        creator="2ndOpinionMD / reportlab",
    )
    cover_frame = Frame(
        MARGIN_L,
        MARGIN_B + 0.4 * inch,
        PAGE_W - MARGIN_L - MARGIN_R,
        PAGE_H - MARGIN_T - MARGIN_B - 0.4 * inch - 1.3 * inch,  # reserve top band space
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
# Story
# -----------------------------------------------------------------------------

def story():
    s = []

    # -------- COVER --------------------------------------------------------
    s.append(Spacer(1, 0.20 * inch))
    s.append(Paragraph(DOC_TITLE, STY["cover_title"]))
    s.append(Paragraph(DOC_SUBTITLE, STY["cover_subtitle"]))

    meta_rows = [
        ["PREPARED FOR", DOC_FOR],
        ["PREPARED BY", DOC_BY],
        ["DATE", DOC_DATE],
        ["PILOT SCOPE",
         "5 patients &nbsp;\u2022&nbsp; 5 years &nbsp;\u2022&nbsp; "
         "Patient-Reported Outcomes only<br/>"
         "(HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI)"],
        ["COMPANION PAPER",
         "<i>Uncertainty-Carrier Governance for Clinical Decision Support</i><br/>"
         "SSRN 6554940"],
        ["DELIVERABLES",
         "5 PatientTimelineVision graphs (JSON) + manifest<br/>"
         "Generator: <font face='BrandMono'>server/scripts/gen_forward_exemplar.py</font>"],
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

    s.append(Spacer(1, 0.50 * inch))
    s.append(Paragraph(
        "Artifacts in <font face='BrandMono'>artifacts/forward_exemplar_5pt/</font>. "
        "Companion slide-ready one-pager: "
        "<font face='BrandMono'>HANDOUT_FORWARD_EXEMPLAR_KALEB_SLIDE_BULLETS_20260422.md</font>.",
        STY["small"],
    ))

    s.append(NextPageTemplate("content"))
    s.append(PageBreak())

    # -------- SUMMARY ------------------------------------------------------
    s.append(H1("Summary"))
    s.append(P(
        "This document accompanies a cohort of five synthetic "
        "<b>PatientTimelineVision</b> (PTV) graphs that demonstrate the shape of a "
        "FORWARD-ingested patient record in the 2ndOpinionMD system. Each graph covers "
        "five years of longitudinal Patient-Reported Outcomes (PROs) only \u2014 the "
        "exact data class FORWARD collects \u2014 and carries first-class "
        "<b>Uncertainty-Carrier</b> (UC) nodes that make confidence, basis, and "
        "missingness explicit on every derived metric."))
    s.append(P(
        "Two of the five patients carry the governance story for Dr. Michaud's "
        "RA-conference and Congressional talks: Patient&nbsp;4, whose UC elevates flare "
        "probability two semi-annual cycles before overt clinical change; and "
        "Patient&nbsp;5, whose UC widens honestly when the patient misses questionnaires. "
        "The other three patients provide cohort heterogeneity."))
    s.append(rule(space_before=8, space_after=8))

    s.append(keep_heading_with_figure(H3("What you have received"), code_block(
        "artifacts/forward_exemplar_5pt/\n"
        "  MANIFEST.json\n"
        "  ptv_synth_P1_early_responder.json              54 events / 14 arcs\n"
        "  ptv_synth_P2_escalation_single_flare.json      56 events / 15 arcs\n"
        "  ptv_synth_P3_cycler_multi_flare.json           64 events / 19 arcs\n"
        "  ptv_synth_P4_subclinical_flare_uc_wins.json    58 events / 15 arcs   <- lead case\n"
        "  ptv_synth_P5_honest_uncertainty_missing.json   48 events / 15 arcs   <- lead case"
    )))

    s.append(H3("Every graph is reproducible and clearly labeled"))
    s.append(bullet("<font face='BrandMono'>metadata.synthetic: true</font> at the graph root"))
    s.append(bullet(
        "<font face='BrandMono'>metadata.disclaimer</font>: "
        "\u201cSYNTHETIC demonstration cohort \u2026 No real patient records were used \u2026 "
        "Not for clinical decision-making.\u201d"))
    s.append(bullet("<font face='BrandMono'>metadata.schema_version: \"ptv.2.1-forward-exemplar\"</font>"))
    s.append(bullet(
        "<font face='BrandMono'>metadata.pro.forward.patient_reported_outcomes_channel: true</font> "
        "\u2014 the PRO channel is wired, and mirrored journal event IDs are listed"))
    s.append(bullet(
        "<font face='BrandMono'>metadata.generator.seed</font> \u2014 fixed per patient, "
        "so artifacts regenerate bit-for-bit"))

    # -------- 1. PURPOSE ---------------------------------------------------
    s.append(H2("1.", "Purpose of this exemplar"))

    s.append(H3("It is"))
    s.append(P(
        "A precise, reproducible demonstration of the shape of a FORWARD-ingested "
        "patient graph in our system:", "body_left"))
    s.append(bullet(
        "Five-year longitudinal trajectories built from PRO questionnaires only "
        "(HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI), mirroring the "
        "FORWARD semi-annual structure."))
    s.append(bullet(
        "<b>Uncertainty-Carrier</b> emissions computed deterministically from the PRO "
        "composite, with calibrated 90% bands and a cited "
        "<font face='BrandMono'>basis</font> list."))
    s.append(bullet(
        "<b>Clinical arcs</b> populated (not just seeded): "
        "<font face='BrandMono'>summary</font>, "
        "<font face='BrandMono'>open_questions</font>, and "
        "<font face='BrandMono'>cross_arc_edges</font> all carry content."))
    s.append(bullet(
        "Provenance on every node and edge "
        "(<font face='BrandMono'>extracted_by</font>, "
        "<font face='BrandMono'>canonical_id</font>, "
        "<font face='BrandMono'>discovered_by</font>, "
        "<font face='BrandMono'>generator.seed</font>)."))

    s.append(H3("It is not"))
    s.append(P(
        "A real-patient dataset. No FORWARD records, no EHR records, no chart review "
        "\u2014 every trajectory is clinically plausible but entirely programmatic. The "
        "artifacts are intended for presentation and pilot-shape review, and every "
        "file makes that status explicit in metadata and in the filename.",
        "body_left"))

    # -------- 2. FIVE PATIENTS --------------------------------------------
    s.append(keep_heading_with_figure(H2("2.", "The five patients, at a glance"), data_table(
        ["#", "Phenotype", "Headline"],
        [
            ["P1", "Early MTX responder",
             "Five-year improving trajectory; narrow UCs throughout."],
            ["P2", "MTX \u2192 TNFi escalation with one flare",
             "Single flare at year 2 triggers adalimumab add-on; trajectory returns to baseline."],
            ["P3", "Cycler with three flares",
             "TNFi \u2192 TNFi \u2192 JAKi; wide UCs reflect disease volatility."],
            ["<b>P4</b>", "<b>Subclinical flare predicted by UC (lead case)</b>",
             "<b>UC elevated flare probability at rounds 3\u20134; overt flare at round 5.</b>"],
            ["<b>P5</b>", "<b>Honest uncertainty with missing data (lead case)</b>",
             "<b>Rounds 4 and 6 questionnaires missing; UC widths widen and basis cites insufficient data.</b>"],
        ],
        col_widths=[0.5 * inch, 2.2 * inch, 3.8 * inch],
    )))
    s.append(Paragraph(
        "Two lead cases (P4, P5) anchor the governance narrative; the three "
        "supporting patients (P1\u2013P3) illustrate heterogeneity of trajectory "
        "across the cohort.",
        STY["caption"]))

    # -------- 3. PATIENT 4 ------------------------------------------------
    s.append(H2("3.", "Patient 4 \u2014 subclinical-flare governance exemplar"))

    s.append(H3("3.1  Trajectory"))
    s.append(P(
        "Ten semi-annual PRO rounds over five years. Stable HAQ-II and VAS scores "
        "at rounds 0\u20132. At rounds 3 and 4, scores drift <i>within</i> the patient's "
        "own trajectory but stay <i>below</i> the HAQ-II and VAS-pain MCID thresholds "
        "(0.22 index units and 20 points). At round 5, both thresholds are crossed "
        "and therapy escalation is recorded."))

    s.append(keep_heading_with_figure(H3("3.2  UC emissions (extracted from the graph)"), data_table(
        ["Round", "UC p.e.", "90% band", "Conf.", "Pre-flare?", "Key basis"],
        [
            ["0", "0.05", "[0.02, 0.15]", "low", "\u2014",
             "baseline; insufficient trajectory data"],
            ["<b>3</b>", "<b>0.22</b>", "<b>[0.20, 0.24]</b>",
             "<b>high</b>", "<b>yes</b>",
             "HAQ-II delta 0.50 MCID units; VAS pain delta 0.47 MCID units"],
            ["<b>4</b>", "<b>0.37</b>", "<b>[0.34, 0.40]</b>",
             "<b>high</b>", "<b>yes</b>",
             "HAQ-II delta 0.91 MCID units; VAS pain delta 0.92 MCID units"],
            ["5", "0.87", "[0.78, 0.95]", "high", "overt flare",
             "HAQ-II delta 2.50 MCID units; VAS pain delta 2.17 MCID units"],
            ["9", "0.32", "[0.24, 0.40]", "high", "\u2014",
             "post-escalation recovery trajectory"],
        ],
        col_widths=[0.70 * inch, 0.85 * inch, 1.00 * inch,
                    0.90 * inch, 1.05 * inch, 2.00 * inch],
    )))

    s.append(H3("3.3  The governance line"))
    s.append(P(
        "The UC emitted at rounds 3 and 4 \u2014 two full semi-annual cycles before the "
        "overt flare at round 5 \u2014 is the governance artifact. It is:", "body_left"))
    s.append(bullet(
        "<b>Deterministic.</b> No LLM was consulted to produce it; it is a "
        "MCID-normalized composite over the PRO trajectory, with the UC width "
        "widening as variance grows."))
    s.append(bullet(
        "<b>Cited.</b> Every UC node carries "
        "<font face='BrandMono'>evidence_event_ids</font> pointing to the PRO events "
        "that drove the band, plus "
        "<font face='BrandMono'>governance_ref: \"SSRN 6554940\"</font>."))
    s.append(bullet(
        "<b>Honest.</b> Round 0 ships with "
        "<font face='BrandMono'>confidence: \"low\"</font> "
        "and the basis line \u201cbaseline round; insufficient trajectory data\u201d \u2014 "
        "the system does not overstate early certainty."))
    s.append(bullet(
        "<b>Graph-native.</b> "
        "<font face='BrandMono'>arc_flare_r05.cross_arc_edges</font> links the "
        "overt-flare arc to the study-epoch arcs at rounds 3 and 4 with "
        "<font face='BrandMono'>kind: \"pre_flare_anticipation\"</font> and "
        "<font face='BrandMono'>evidence_event_id</font> pointing to the anticipation "
        "UCs. The pre-flare signal is a first-class graph edge, not a footnote."))
    s.append(bullet(
        "<b>Open-question bearing.</b> "
        "<font face='BrandMono'>arc_flare_r05.open_questions</font> "
        "contains: <i>\u201cEarlier UC-anticipated rounds 3\u20134 suggest a pre-flare "
        "signal; would earlier escalation have prevented this event?\u201d</i> \u2014 the "
        "system authors its own agenda for follow-up review."))

    # -------- 4. PATIENT 5 ------------------------------------------------
    s.append(H2("4.", "Patient 5 \u2014 honest-uncertainty exemplar"))

    s.append(H3("4.1  Situation"))
    s.append(P(
        "Patient does not complete questionnaires at rounds 4 and 6. The graph "
        "records two <font face='BrandMono'>administrative</font> events labeled "
        "<i>\u201cQuestionnaire round N: not completed\u201d</i> rather than "
        "interpolating or guessing."))

    s.append(keep_heading_with_figure(H3("4.2  UC behavior"), data_table(
        ["Round", "UC p.e.", "90% band", "Conf.", "Basis"],
        [
            ["0", "0.05", "[0.02, 0.15]", "low",
             "baseline; insufficient trajectory data"],
            ["<b>7</b>", "<b>0.67</b>", "<b>[0.54, 0.81]</b>", "<b>moderate</b>",
             "HAQ-II delta 2.09 MCID units; VAS pain delta 1.45 MCID units; "
             "<b>UC width widened due to missing recent questionnaire(s)</b>"],
            ["9", "0.65", "[0.56, 0.75]", "high",
             "missingness cleared; band narrows"],
        ],
        col_widths=[0.70 * inch, 0.85 * inch, 1.00 * inch,
                    1.00 * inch, 2.95 * inch],
    )))

    s.append(H3("4.3  The governance line"))
    s.append(P(
        "The UC width at round 7 is wider than the width at round 9 even though the "
        "point estimates are nearly identical \u2014 because the information available "
        "is different, and the framework refuses to obscure that difference. The "
        "basis line says so explicitly."))

    # -------- 5. SCHEMA CHEAT SHEET ---------------------------------------
    s.append(keep_heading_with_figure(H2("5.", "Schema cheat sheet (for any slide that shows JSON)"), data_table(
        ["Field", "Meaning"],
        [
            ["<font face='BrandMono'>arcs[*].status</font>",
             "<font face='BrandMono'>seeded \u2192 enriched \u2192 reviewed \u2192 locked</font> \u2014 lifecycle state"],
            ["<font face='BrandMono'>arcs[*].summary</font>",
             "human-readable arc synthesis, cited"],
            ["<font face='BrandMono'>arcs[*].open_questions</font>",
             "agenda items the system flags for review"],
            ["<font face='BrandMono'>arcs[*].cross_arc_edges</font>",
             "typed inter-arc relations "
             "(<font face='BrandMono'>treated_by</font>, "
             "<font face='BrandMono'>initiated_in_response_to</font>, "
             "<font face='BrandMono'>pre_flare_anticipation</font>)"],
            ["<font face='BrandMono'>events[*].card</font>",
             "100\u2013200 token per-event digest"],
            ["<font face='BrandMono'>events[*].salience</font>",
             "numeric priority score"],
            ["<font face='BrandMono'>events[*].canonical_id</font>",
             "cross-source dedup handle"],
            ["<font face='BrandMono'>events[*].entity_keys</font>",
             "normalized codes "
             "(<font face='BrandMono'>icd:*</font>, "
             "<font face='BrandMono'>rxnorm:*</font>, "
             "<font face='BrandMono'>instrument:haq2</font>, "
             "<font face='BrandMono'>round:3</font>)"],
            ["<font face='BrandMono'>events[*].annotations.kind</font>",
             "for <font face='BrandMono'>derived_metric</font> nodes, identifies the "
             "carrier class (<font face='BrandMono'>uncertainty_carrier</font>)"],
            ["<font face='BrandMono'>events[*].annotations.basis</font>",
             "UC's cited evidence list"],
            ["<font face='BrandMono'>events[*].annotations.governance_ref</font>",
             "pointer to SSRN 6554940"],
        ],
        col_widths=[2.5 * inch, 4.0 * inch],
    )))
    s.append(P(
        "Screenshotting a slice \u2014 e.g. a single UC node plus the flare arc it "
        "attaches to \u2014 is sufficient for a slide. The compact "
        "<font face='BrandMono'>card</font> and the cited "
        "<font face='BrandMono'>basis</font> read together as a self-contained "
        "governance artifact."))

    # -------- 6. REAL DATA TRANSITION -------------------------------------
    s.append(H2("6.", "What changes when real FORWARD data replaces synthetic"))
    s.append(P(
        "Essentially nothing structural. The same ingestion pipeline emits "
        "identically shaped graphs; real trajectories replace programmatic ones; "
        "<font face='BrandMono'>metadata.synthetic</font> flips to "
        "<font face='BrandMono'>false</font>; RxNorm CUIs come from our local RxNav "
        "snapshot rather than the generator's compact map. All UC computation, arc "
        "enrichment, and cross-arc edge inference are the same deterministic code "
        "paths."))

    s.append(H3("6.1  Pilot-data shape we would like"))
    s.append(bullet("<b>n = 5</b> patients with RA (ICD-10 M05.* or M06.*), anonymized cohort"))
    s.append(bullet("<b>5 years</b> of follow-up, ~10 semi-annual questionnaires per patient"))
    s.append(bullet(
        "<b>Primary variables:</b> HAQ-II raw, VAS Pain (0\u2013100), VAS Patient "
        "Global (0\u2013100), PAS-II, RDCI components"))
    s.append(bullet(
        "<b>Treatment:</b> start/stop dates for DMARDs, biologics, JAKi, steroids; "
        "dose where recorded"))
    s.append(bullet(
        "<b>Format:</b> CSV or Parquet; long format (one row per patient \u00d7 round "
        "\u00d7 instrument); ISO-8601 dates; explicit units in column names"))
    s.append(bullet(
        "<b>Out of scope (confirmed):</b> labs, imaging, biosamples, -omics, DAS28"))

    s.append(H3("6.2  Turnaround once data is in hand"))
    s.append(P(
        "Pilot ingest \u2192 5 production (non-synthetic) FORWARD PTV graphs: "
        "<b>\u2264&nbsp;48 hours</b> from receipt. UC emission, arc enrichment, and "
        "manifest regeneration are included."))

    # -------- 7. HOW TO USE -----------------------------------------------
    s.append(H2("7.", "Recommended use of these artifacts"))
    s.append(bullet(
        "<b>Lead with P4</b> on the governance slide. One JSON snippet of the "
        "<font face='BrandMono'>P4_uc_r03</font> node plus the "
        "<font face='BrandMono'>arc_flare_r05</font> arc summary, side by side, is "
        "the one-slide version of the whole UC argument."))
    s.append(bullet(
        "<b>Use P5 on the \u201cwhat happens when we don't know\u201d slide.</b> Show "
        "the widened band at round 7 with its basis list; show the narrowed band at "
        "round 9 once data returns."))
    s.append(bullet(
        "<b>Show the cohort as a table</b> (P1\u2013P5, phenotype, # flares, mean UC "
        "width) on the \u201cheterogeneity, honestly reported\u201d slide \u2014 the "
        "manifest file carries these values."))
    s.append(bullet(
        "<b>Cite SSRN 6554940</b> on every slide that shows a UC node; the graphs do "
        "this automatically via <font face='BrandMono'>governance_ref</font>."))
    s.append(bullet(
        "<b>If asked \u201cis this real data?\u201d</b>, the answer is in "
        "<font face='BrandMono'>metadata.synthetic</font> and in every filename. "
        "No ambiguity."))

    # -------- 8. REPRODUCIBILITY ------------------------------------------
    s.append(H2("8.", "Reproducibility and attribution"))
    s.append(bullet(
        "Every artifact is reproducible bit-for-bit from "
        "<font face='BrandMono'>server/scripts/gen_forward_exemplar.py</font> "
        "at git HEAD on 22 April 2026."))
    s.append(bullet(
        "Seeds are fixed per patient and recorded in "
        "<font face='BrandMono'>metadata.generator.seed</font>."))
    s.append(bullet(
        "RxNorm CUIs are listed by ingredient in the generator source and should be "
        "validated against the local RxNav snapshot prior to any production use."))
    s.append(bullet(
        "For any public rendering, a footer of the form "
        "<i>\u201cSynthetic exemplar cohort; 2ndOpinionMD + FORWARD pilot preview; "
        "generator seed {seed}; SSRN 6554940\u201d</i> is sufficient attribution."))

    # -------- APPENDIX A: JSON SNIPPETS -----------------------------------
    s.append(H1("Appendix A \u2014 Screenshot-ready JSON snippets"))
    s.append(P(
        "Each snippet below is extracted verbatim from the shipped artifacts. Any "
        "of them is suitable for a single-slide full-bleed screenshot."))

    s.append(keep_heading_with_figure(H3("A.1  UC node at anticipation round 3 (Patient 4)"), code_block(
        '{\n'
        '  "event_type": "derived_metric",\n'
        '  "timestamp": "2022-08-01",\n'
        '  "annotations": {\n'
        '    "kind": "uncertainty_carrier",\n'
        '    "metric": "flare_probability_90",\n'
        '    "point_estimate": 0.22,\n'
        '    "band_90": [0.20, 0.24],\n'
        '    "confidence": "high",\n'
        '    "anticipation": true,\n'
        '    "basis": [\n'
        '      "HAQ-II delta since baseline = 0.50 MCID units",\n'
        '      "VAS pain delta since baseline = 0.47 MCID units",\n'
        '      "rounds with missing data in last 3 rounds: 0"\n'
        '    ],\n'
        '    "governance_ref": "SSRN 6554940 (Uncertainty Carriers)",\n'
        '    "evidence_event_ids": [\n'
        '      "P4_r03_haq2", "P4_r03_vas_pain",\n'
        '      "P4_r03_vas_global", "P4_r03_pas2"\n'
        '    ]\n'
        '  }\n'
        '}')))

    s.append(keep_heading_with_figure(H3("A.2  Flare arc citing the anticipation round (Patient 4)"), code_block(
        '{\n'
        '  "arc_id": "arc_flare_r05",\n'
        '  "name": "Flare window (round 6)",\n'
        '  "status": "enriched",\n'
        '  "summary": "PRO-composite flare detected at round 6. HAQ-II and\n'
        '              VAS-pain crossed MCID thresholds against patient\n'
        '              baseline; treatment escalation recorded within the\n'
        '              same epoch.",\n'
        '  "open_questions": [\n'
        '    "Earlier UC-anticipated rounds 3-4 suggest a pre-flare signal;\n'
        '     would earlier escalation have prevented this event?"\n'
        '  ],\n'
        '  "cross_arc_edges": [\n'
        '    {"peer_arc_id": "arc_therapy_adalimumab",\n'
        '     "kind": "treated_by", "strength": 1.0},\n'
        '    {"peer_arc_id": "arc_study_epoch_m24",\n'
        '     "kind": "pre_flare_anticipation", "strength": 0.8,\n'
        '     "evidence_event_id": "P4_uc_r03"},\n'
        '    {"peer_arc_id": "arc_study_epoch_m30",\n'
        '     "kind": "pre_flare_anticipation", "strength": 0.8,\n'
        '     "evidence_event_id": "P4_uc_r04"}\n'
        '  ]\n'
        '}')))

    s.append(keep_heading_with_figure(H3("A.3  Honest-uncertainty UC at round 7 (Patient 5)"), code_block(
        '{\n'
        '  "event_type": "derived_metric",\n'
        '  "annotations": {\n'
        '    "kind": "uncertainty_carrier",\n'
        '    "point_estimate": 0.67,\n'
        '    "band_90": [0.54, 0.81],\n'
        '    "confidence": "moderate",\n'
        '    "basis": [\n'
        '      "HAQ-II delta since baseline = 2.09 MCID units",\n'
        '      "VAS pain delta since baseline = 1.45 MCID units",\n'
        '      "rounds with missing data in last 3 rounds: 1",\n'
        '      "UC width widened due to missing recent questionnaire(s)"\n'
        '    ],\n'
        '    "governance_ref": "SSRN 6554940 (Uncertainty Carriers)"\n'
        '  }\n'
        '}')))

    # -------- APPENDIX B: PROVENANCE --------------------------------------
    s.append(H1("Appendix B \u2014 Provenance and regeneration"))
    s.append(keep_heading_with_figure(H3("Regenerate all artifacts"), code_block(
        "python server/scripts/gen_forward_exemplar.py")))

    s.append(keep_heading_with_figure(H3("Files produced"), code_block(
        "artifacts/forward_exemplar_5pt/\n"
        "  MANIFEST.json                                   3.6 KB\n"
        "  ptv_synth_P1_early_responder.json              95.4 KB\n"
        "  ptv_synth_P2_escalation_single_flare.json     100.6 KB\n"
        "  ptv_synth_P3_cycler_multi_flare.json          118.9 KB\n"
        "  ptv_synth_P4_subclinical_flare_uc_wins.json   105.3 KB\n"
        "  ptv_synth_P5_honest_uncertainty_missing.json   87.3 KB")))

    s.append(H3("Companion documents"))
    s.append(bullet(
        "<b>This document</b> (PDF) \u2014 "
        "<font face='BrandMono'>REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.pdf</font>"))
    s.append(bullet(
        "<b>Slide-ready one-pager</b> (Markdown) \u2014 "
        "<font face='BrandMono'>HANDOUT_FORWARD_EXEMPLAR_KALEB_SLIDE_BULLETS_20260422.md</font> "
        "(kept on-hand; edit freely during talk prep)"))

    s.append(H3("Contact for this deliverable"))
    s.append(P(
        "Technical questions on the graph structure, UC computation, or real-data "
        "ingest path route through the 2ndOpinionMD platform team. For anything "
        "concerning pilot scope, DUA, or publication plan, please contact Andr\u00e1s "
        "directly."))

    return s

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    doc = build_doc()
    doc.build(story())
    kb = OUT_PATH.stat().st_size / 1024
    print(f"wrote {OUT_PATH.name}  ({kb:.1f} KB)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
