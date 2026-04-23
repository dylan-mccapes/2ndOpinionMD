# EOHD PDF Style Guide (Comfort Profile)

**Date:** 2026-02-27  
**Intent:** A clinically clear but emotionally gentler presentation style for EoHD packet PDFs.

---

## 1) Visual Tone

- Use calm blue section headers (`calmblue`) and soft divider lines (`linerule`).
- Keep high readability without stark contrast spikes.
- Prefer consistent spacing over dense blocks.

## 2) Layout

- Margin: `0.85in`
- Font size: `11pt`
- Paragraph spacing: `0.4em`
- Section dividers: thin horizontal rules between major blocks

## 3) Heading Structure

- One clear title per page-level section.
- Use short, human headers:
  - `Main Report`
  - `Phase A1` (etc.)
  - `Prompt`
  - `Report`
- Avoid aggressive all-caps labeling unless compliance-required.

## 4) Bullet Style (Softer)

- Keep bullets concise and supportive rather than declarative.
- Render list bullets as light gray dashes (`--`) in PDF.
- Prefer language like:
  - "What this section includes"
  - "Sources used"
  - "Context"
- Avoid overly rigid command tone.

## 5) Wording Defaults

- Use transparent, calm framing:
  - "This packet is prepared to support review."
  - "Reports are listed in run order for traceability."
- Keep rigor, but reduce hard-edged phrasing.

## 6) PDF Generation Defaults

Use the script in comfort mode (recommended), or use Pandoc with:

- `receipts/eohd_pdf_comfort_header.tex`
- geometry `margin=0.85in`
- fontsize `11pt`
- `calmblue` section headings + `\sectionrule` separators
- TOC entries include a 1-2 sentence phase synopsis

Example:

`python3 eohd_pdf_agent.py --report-md reports/REPORT_NORMAN_ERIC_ROBERTS_EOHD_20260227.md --receipt-md receipts/RECEIPT_EOHD_NORMAN_ERIC_ROBERTS_20260226.md --out-md receipts/EOHD_PACKET_NORMAN_ERIC_ROBERTS_COMFORT.md --out-pdf receipts/EOHD_PACKET_NORMAN_ERIC_ROBERTS_COMFORT.pdf --tone comfort`

