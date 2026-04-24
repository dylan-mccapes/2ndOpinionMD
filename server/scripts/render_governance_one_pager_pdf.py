#!/usr/bin/env python3
"""Render the Governance One-Pager PDF for partner review (FORWARD / RISE etc.)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#1f3a5f")
ACCENT = colors.HexColor("#2e86de")
MUTED = colors.HexColor("#6b7280")


def _styles():
    base = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1",
        parent=base["Heading1"],
        fontSize=16,
        leading=19,
        spaceAfter=2,
        textColor=BRAND,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=3,
        textColor=BRAND,
    )
    body = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontSize=9.5,
        leading=12.5,
        alignment=TA_LEFT,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=8.2,
        leading=10.5,
        textColor=MUTED,
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        leftIndent=10,
        bulletIndent=0,
        spaceBefore=0,
        spaceAfter=1,
    )
    return {"h1": h1, "h2": h2, "body": body, "small": small, "bullet": bullet}


def _layered_table(rows, widths, body_style):
    data = [
        [
            Paragraph("<b>#</b>", body_style),
            Paragraph("<b>Layer</b>", body_style),
            Paragraph("<b>Guarantee</b>", body_style),
        ]
    ]
    for idx, layer, guarantee in rows:
        data.append(
            [
                Paragraph(str(idx), body_style),
                Paragraph(f"<b>{layer}</b>", body_style),
                Paragraph(guarantee, body_style),
            ]
        )
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]
        )
    )
    return t


def build_pdf(out_pdf: Path) -> None:
    st = _styles()

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title="2ndOpinionMD Governance One-Pager",
        author="2ndOpinionMD",
        subject="Governance one-pager for partner review (FORWARD / RISE).",
    )

    story = []
    story.append(Paragraph("2ndOpinionMD &mdash; Governance One-Pager", st["h1"]))
    story.append(
        Paragraph(
            "FORWARD / RISE longitudinal PRO study collaboration &nbsp;&middot;&nbsp; April 2026 "
            "&nbsp;&middot;&nbsp; For partner society leadership, IRB, and data-governance reviewers",
            st["small"],
        )
    )
    story.append(Spacer(1, 6))

    story.append(Paragraph("1) Architecture at a Glance", st["h2"]))
    story.append(
        Paragraph(
            "2ndOpinionMD is an <b>on-premise, air-gapped clinical reasoning platform</b> "
            "pairing a Medical Knowledge Engine (<b>million+</b> RAG-indexed documents across "
            "15+ ontologies, guidelines, and EHR-note corpora including MIMIC shards), "
            "the Ethos of Health (EoH) reasoning framework "
            "(30+ governance-first modules), and <b>PatientTimelineVision (PTV)</b> &mdash; "
            "the per-patient longitudinal graph.",
            st["body"],
        )
    )
    for b in [
        "<b>Hardware (pilot):</b> Apple M2 Ultra + Intel i7 workstation with RTX-4090 (<i>PortalNode prototype</i> profile). Full multi-GPU PortalNodes require separate funding.",
        "<b>Models:</b> local <i>eoh-llama</i> tiers (3.2 routing, 8B workhorse, 70B synthesis); cloud LLM disabled by default for regulated workloads.",
        "<b>Substrate:</b> PostgreSQL 16 + pgvector; FastAPI backend; React SPA; nginx reverse proxy.",
        "<b>Provenance:</b> every graph mutation, model routing decision, and detective run is receipt-tracked.",
        "<b>Partner surface:</b> scoped B2B API (<code>/v1/mkg/*</code>) with key auth + rate limits. Patient identifiers never traverse this surface.",
    ]:
        story.append(Paragraph(f"&bull; {b}", st["bullet"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2) HIPAA Posture (Operational Today)", st["h2"]))
    story.append(
        Paragraph(
            "Privacy is a <b>layered architectural concern</b>, not a bolt-on. All eight layers below "
            "are implemented in the platform today; partner cohorts are processed through the same pipeline.",
            st["body"],
        )
    )
    story.append(Spacer(1, 3))

    layers = [
        (
            1,
            "Ingestion-time PII scrub (pre-DB)",
            "<code>ehr.patient_timeline</code> and <code>ehr.artifacts</code> rows are "
            "<b>scrubbed of direct identifiers before insert</b>. Raw source files are not retained.",
        ),
        (
            2,
            "OGrE agent-driven scrub",
            "Opportunistic Graph Enrichment agents re-scan events; <b>any PII the 8B agent sees is "
            "redacted with provenance</b> and the code index is re-synchronized.",
        ),
        (
            3,
            "Query anonymization",
            "Every clinical query is converted to a categorical summary "
            "(e.g. <i>symptom_query: cardiopulmonary_assessment adult</i>) <b>before it reaches any log</b>.",
        ),
        (
            4,
            "Encrypted logging at rest",
            "Fernet-encrypted, rotated, key-isolated. Logs are unreadable without the key; a "
            "decrypt utility is reserved for authorized audit.",
        ),
        (
            5,
            "Security middleware",
            "Sensitive-path blocking, CORS allow-list, request logging with anonymized payloads only.",
        ),
        (
            6,
            "Consent + audit trails",
            "<code>anonymization_consent</code> at session init; chat-graph evictions are "
            "<b>soft-deleted</b> with timestamp and reason for full audit reconstruction.",
        ),
        (
            7,
            "Local-first inference",
            "All LLM inference runs locally on the pilot on-prem stack (M2 Ultra + i7/RTX-4090) and scales to the PortalNode prototype profile as funding allows. "
            "<b>No patient data leaves the network</b> in the on-premise configuration.",
        ),
        (
            8,
            "Provenance tracking",
            "PTV mutations, detective runs, chat references, and B2B usage are receipt-tracked. "
            "Every output is traceable via a <code>DerivationChain</code>.",
        ),
    ]

    story.append(
        KeepTogether(
            _layered_table(
                layers,
                widths=[0.3 * inch, 1.7 * inch, 5.4 * inch],
                body_style=st["body"],
            )
        )
    )
    story.append(Spacer(1, 4))

    for b in [
        "<b>Air-gapped operation</b> is the default for partner pilots and longitudinal studies; cloud LLMs disabled at deployment.",
        "<b>De-identification standard:</b> Safe Harbor (18 HIPAA identifiers), with optional Expert Determination review.",
        "<b>Sub-processors:</b> none for the air-gapped configuration. The on-premise deployment is self-contained after initial model/corpus load.",
        "<b>BAA:</b> executed with any covered entity prior to identifiable-PHI handling. Partner society governs release of de-identified cohort data.",
    ]:
        story.append(Paragraph(f"&bull; {b}", st["bullet"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("3) Non-Commercial Research Terms", st["h2"]))
    for b in [
        "<b>Non-commercial use only.</b> Study artifacts are used solely for research and publication without a separately negotiated commercial agreement.",
        "<b>No model training on partner data</b> without explicit, study-specific written consent. Partner corpora are used for inference, retrieval, and reasoning only.",
        "<b>Data residency.</b> Partner-supplied data remains on the pilot on-prem stack / PortalNode prototype (or partner-designated infrastructure); no off-premise copies.",
        "<b>Scoped access.</b> Partner investigators receive scoped B2B keys (<code>mkg:read</code>, <code>mkg:evidence</code>) limited to the study cohort; provisioning is logged and revocable.",
        "<b>Deletion on request.</b> Study-scoped artifacts are purged on a defined timeline (30 days default) with a cryptographic deletion receipt.",
        "<b>IP boundary.</b> 2ndOpinionMD retains platform/model/MKG/EoH ownership; partners retain source-data ownership; derived research outputs are co-owned per study agreement.",
    ]:
        story.append(Paragraph(f"&bull; {b}", st["bullet"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("4) Publication-First Commitment", st["h2"]))
    for b in [
        "<b>Support partner publication priorities.</b> Primary study findings are published by the partner society (or jointly as agreed); 2ndOpinionMD will not pre-publish overlapping primary findings.",
        "<b>Methods transparency.</b> Platform methods, PTV schema, toolkit interfaces, and governance controls are documented for reviewer-facing methods sections; relevant Modelfiles and harness specs available on request under confidentiality.",
        "<b>Open reproducibility on non-patient artifacts.</b> Synthetic PTV graphs, harness questions, and scoring rubrics are shareable so reviewers can replicate the evaluation <b>without partner PHI</b>.",
        "<b>Honest-uncertainty reporting.</b> Clinical outputs carry Uncertainty Carriers (posterior means + 90% credible intervals + evidence event IDs + method tag). Publications report bands alongside point estimates.",
        "<b>Reasonable embargo.</b> A standard publication embargo (typically 6&ndash;12 months from study conclusion, per partner policy) is honored before any marketing or white-paper reuse.",
    ]:
        story.append(Paragraph(f"&bull; {b}", st["bullet"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("5) Points of Contact", st["h2"]))
    for b in [
        "<b>Technical / Engineering:</b> Dylan McCapes (2ndOpinionMD Engineering).",
        "<b>Clinical / Scientific:</b> Dr. Andras Hanyal, PharmMD.",
        "<b>Governance / Compliance:</b> via the same engineering contact; BAA and DUA drafts provided on request.",
    ]:
        story.append(Paragraph(f"&bull; {b}", st["bullet"]))
    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "<i>This one-pager is a governance summary intended for partner review. It is not a legal instrument. "
            "Binding terms are set in the executed research-collaboration agreement, DUA, and BAA applicable to each study.</i>",
            st["small"],
        )
    )
    story.append(Spacer(1, 2))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            st["small"],
        )
    )

    doc.build(story)
    print(f"Wrote {out_pdf}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default="reports/GOVERNANCE_ONE_PAGER_20260423.pdf",
    )
    args = ap.parse_args()
    out_pdf = Path(args.out).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(out_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

