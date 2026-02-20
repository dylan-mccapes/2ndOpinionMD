#!/usr/bin/env python3
"""
Generate a mock patient timeline PDF for demo graph seeding.

Output: data/patient-timelines/mock_timeline_demo.pdf

Use with:
  python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/mock_timeline_demo.pdf \
    --patient-id demo_patient

Content: Synthetic 38F seropositive RA patient with visits, labs, flares,
medications, and journal entries. Uses explicit ISO dates for parser extraction.
"""

from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

# ---------------------------------------------------------------------------
# Mock timeline content — explicit dates for parser, clinical keywords for
# event type identification (lab, flare, medication, symptom, visit, journal)
# ---------------------------------------------------------------------------

TIMELINE_CONTENT = """
PATIENT TIMELINE — DEMO SEED
Patient ID: demo_patient
DOB: 1986-03-15 | Sex: F
Condition: Seropositive Rheumatoid Arthritis

================================================================================
2024-12-01T09:00:00 — Visit
================================================================================
Initial rheumatology visit. Seropositive RA diagnosed.
History: Swollen MCPs and PIPs bilaterally, morning stiffness > 1 hour.
RF positive, anti-CCP positive. DAS28: 5.6.
Assessment: Moderate disease activity.
Plan: Start methotrexate, order baseline labs.

================================================================================
2024-12-01T10:30:00 — Medication
================================================================================
Started methotrexate 15 mg weekly PO. Folic acid 1 mg daily.
No adalimumab at this time.

================================================================================
2025-01-15T14:00:00 — Lab
================================================================================
Baseline labs. CBC, CMP, LFTs. CRP 18 mg/L, ESR 42 mm/hr.
ALT slightly elevated at 45 U/L. Hold MTX until repeat in 2 weeks.

================================================================================
2025-02-15T09:00:00 — Lab
================================================================================
Repeat labs. CRP 12 mg/L, ESR 34 mm/hr. Improved but still elevated.
ALT normalized. Continue methotrexate 15 mg weekly.

================================================================================
2025-03-01T09:00:00 — Medication
================================================================================
Add adalimumab 40 mg subcutaneous every 2 weeks.
Inadequate response to MTX monotherapy after 3 months.

================================================================================
2025-04-10T08:00:00 — Flare
================================================================================
Moderate disease flare. Patient reports increased joint pain and swelling
in hands and wrists. Morning stiffness 2 hours. Worsening fatigue.
Started prednisone burst 20 mg daily x 5 days, taper.

================================================================================
2025-04-10T11:00:00 — Lab
================================================================================
CRP 28 mg/L, ESR 52 mm/hr. Inflammatory markers elevated with flare.
Continue adalimumab, monitor.

================================================================================
2025-06-05T08:00:00 — Flare
================================================================================
Moderate flare — knees and wrists. Pain 6/10. Morning stiffness 90 min.
Prednisone burst 15 mg daily x 5 days. Consider MTX dose escalation.

================================================================================
2025-06-20T09:00:00 — Lab
================================================================================
CRP 6 mg/L, ESR 22 mm/hr. Inflammatory markers back toward baseline.
Disease activity improving.

================================================================================
2025-07-01T08:00:00 — Visit
================================================================================
Clinic visit. Low disease activity on MTX + adalimumab.
DAS28: 3.0. Patient reports overall improvement. Continue current regimen.
Next follow-up in 3 months.

================================================================================
2025-07-15T22:00:00 — Journal / Self-report
================================================================================
Patient reports mild stiffness on busy weeks, otherwise doing well.
Journal entry: "When I work 10+ hour days, hands ache more in evening.
Otherwise feeling much better than before treatment."
""".strip()


def build_pdf(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Patient Timeline — Demo Seed", styles["Title"]))
    story.append(Spacer(1, 12))

    # Pre block (preserves whitespace for parser)
    mono = ParagraphStyle(
        "Monospace",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=11,
        leftIndent=0,
        rightIndent=0,
    )
    for block in TIMELINE_CONTENT.split("\n\n"):
        story.append(Paragraph(block.replace("\n", "<br/>"), mono))
        story.append(Spacer(1, 6))

    doc.build(story)
    print(f"Generated: {out_path}")


def main() -> None:
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    out_path = repo_root / "data" / "patient-timelines" / "mock_timeline_demo.pdf"
    build_pdf(out_path)


if __name__ == "__main__":
    main()
