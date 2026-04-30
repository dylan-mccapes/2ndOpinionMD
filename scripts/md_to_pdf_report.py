#!/usr/bin/env python3
"""Render a markdown text file into a simple PDF report."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


IN_MD = Path(r"c:\2OPMD\2ndOpinionMD-MVP\receipts\FORWARD_MKG_QA_COLLECTION_20250425.md")
OUT_PDF = Path(r"c:\2OPMD\2ndOpinionMD-MVP\receipts\FORWARD_MKG_QA_COLLECTION_20250425.pdf")


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main() -> None:
    text = IN_MD.read_text(encoding="utf-8", errors="replace")
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    h3 = styles["Heading3"]
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        leading=13,
        spaceAfter=6,
    )

    story = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            story.append(Paragraph(_escape(line[2:]), h1))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_escape(line[3:]), h2))
            continue
        if line.startswith("### "):
            story.append(Paragraph(_escape(line[4:]), h3))
            continue

        # Keep markdown bullets/numbering as text for readability.
        story.append(Paragraph(_escape(line), body))

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=48,
        bottomMargin=48,
        title="FORWARD MKG Q&A Collection",
    )
    doc.build(story)
    print(str(OUT_PDF))


if __name__ == "__main__":
    main()
