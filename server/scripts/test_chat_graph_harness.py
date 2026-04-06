#!/usr/bin/env python3
"""
test_chat_graph_harness.py — Chat Graph Decay & Eviction Test Harness

Simulates 20 patient/doctor/agent chat messages over 30 days against a
real or synthetic PTV graph. Manipulates timestamps to observe decay,
anchoring retention, and eviction behavior.

Does NOT require Postgres — runs entirely in-memory using the chat_graph
module directly.

Also generates a 10-page synthetic patient timeline PDF (~200 entries)
for integration testing.

Usage:
    python scripts/test_chat_graph_harness.py
    python scripts/test_chat_graph_harness.py --generate-pdf synthetic_timeline.pdf
    python scripts/test_chat_graph_harness.py --ptv ../artifacts/timeline_ollama_20260330_1312/ptv_heuristic_enriched.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent
if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from server.eoh.chat_graph import (
    ChatMessage,
    ChatDecayConfig,
    DEFAULT_DECAY_CONFIG,
    create_message,
    compute_decay_score,
    update_all_decay_scores,
    select_eviction_candidates,
    evict_message,
    anchor_message_to_event,
    touch_message,
    build_chat_context_for_eohd,
    build_enrichment_candidates,
)


# ── Synthetic timeline PDF generation ────────────────────────────────────────

SYNTHETIC_PATIENT = {
    "name": "Maria Elena Vasquez",
    "mrn": "SYN-2026-001",
    "dob": "03/15/1972",
    "sex": "female",
}

DIAGNOSES = [
    ("Systemic Lupus Erythematosus", "M32.10", "01/10/2020"),
    ("Lupus Nephritis, Class III", "M32.14", "04/22/2020"),
    ("Antiphospholipid Syndrome", "D68.61", "01/10/2020"),
    ("Hypertension", "I10", "06/15/2018"),
    ("Iron Deficiency Anemia", "D50.9", "09/03/2020"),
    ("Anxiety Disorder", "F41.1", "03/20/2021"),
    ("Vitamin D Deficiency", "E55.9", "11/12/2020"),
    ("Raynaud Phenomenon", "I73.00", "01/10/2020"),
    ("Alopecia", "L65.9", "05/14/2021"),
    ("Osteoporosis", "M81.0", "02/28/2023"),
]

MEDICATIONS = [
    ("hydroxychloroquine", "200 mg", "oral", "twice daily"),
    ("mycophenolate mofetil", "1000 mg", "oral", "twice daily"),
    ("prednisone", "10 mg", "oral", "daily"),
    ("lisinopril", "20 mg", "oral", "daily"),
    ("aspirin", "81 mg", "oral", "daily"),
    ("ferrous sulfate", "325 mg", "oral", "daily"),
    ("vitamin D3", "2000 IU", "oral", "daily"),
    ("calcium carbonate", "600 mg", "oral", "daily"),
    ("sertraline", "50 mg", "oral", "daily"),
    ("amlodipine", "5 mg", "oral", "daily"),
    ("omeprazole", "20 mg", "oral", "daily"),
    ("folic acid", "1 mg", "oral", "daily"),
]

LABS = [
    ("ANA", "positive", "1:640"),
    ("Anti-dsDNA", "positive", "85 IU/mL"),
    ("C3", "low", "62 mg/dL"),
    ("C4", "low", "8 mg/dL"),
    ("ESR", "elevated", "48 mm/hr"),
    ("CRP", "elevated", "2.4 mg/dL"),
    ("Creatinine", "normal", "0.9 mg/dL"),
    ("eGFR", "normal", "78 mL/min"),
    ("Hemoglobin", "low", "10.2 g/dL"),
    ("Platelet count", "normal", "185 thou/cu mm"),
    ("WBC", "low", "3.2 thou/cu mm"),
    ("Urinalysis protein", "trace", "30 mg/dL"),
    ("Anti-Smith", "positive", ""),
    ("Anti-RNP", "positive", ""),
    ("Vitamin D 25-OH", "low", "18 ng/mL"),
    ("Ferritin", "low", "12 ng/mL"),
    ("TSH", "normal", "2.1 mIU/L"),
    ("ALT", "normal", "22 U/L"),
    ("AST", "normal", "19 U/L"),
    ("Urine protein/creatinine ratio", "elevated", "0.8"),
]

VISIT_TYPES = [
    "Office Visit in Rheumatology",
    "Office Visit in Nephrology",
    "Telephone in Rheumatology",
    "Office Visit in Internal Medicine",
    "Office Visit in Dermatology",
    "Allied Health/Nurse Visit in Laboratory",
    "Office Visit in Psychiatry",
]

NOTES = [
    "Patient reports increased fatigue and joint pain over past 2 weeks. Malar rash noted on examination.",
    "Lupus nephritis stable on current regimen. Proteinuria improved from prior visit.",
    "Discussed stress management. Patient reports work-related anxiety affecting sleep.",
    "Raynaud symptoms worsening with cold weather. Added amlodipine to regimen.",
    "Hair thinning continues. Reassured patient this is common with SLE. No scarring alopecia.",
    "Patient concerned about prednisone side effects. Discussed taper plan pending labs.",
    "DEXA scan shows osteopenia. Started calcium and vitamin D supplementation.",
    "Flare: arthralgias, fatigue, low-grade fever. Increased prednisone to 20 mg.",
    "Follow-up after flare. Symptoms improved. Begin prednisone taper: 15 mg x 2 weeks.",
    "Annual comprehensive review. SLEDAI-2K score: 6. Moderate disease activity.",
    "Patient reports emotional distress related to chronic illness. Referral to psychiatry.",
    "Lab review: complement levels improving. Anti-dsDNA titer decreasing. Continue current regimen.",
    "Immunization review: flu vaccine administered. COVID booster discussed.",
    "Patient hospitalized for lupus flare with pleuritis. Discharged on methylprednisolone pulse.",
    "Post-hospitalization follow-up. Clinically improved. Resume mycophenolate.",
]


def _generate_synthetic_timeline_text() -> List[str]:
    """Generate 10 pages of Kaiser-formatted synthetic timeline text."""
    pages = []
    random.seed(42)  # reproducible

    base_date = datetime(2020, 1, 10)
    header = (
        f"Release of Medical Information\n"
        f"25 N Via Monte\nWalnut Creek, CA 94598\n925-210-8834\n"
        f"{SYNTHETIC_PATIENT['name']}\n"
        f"MRN: {SYNTHETIC_PATIENT['mrn']} DOB: {SYNTHETIC_PATIENT['dob']}\n"
        f"Sex: {SYNTHETIC_PATIENT['sex']}\n"
    )

    # Page 1: Demographics + Problem List
    p1 = header + "\nProblem List as of 12/05/2025\n\n"
    for dx_name, icd, noted in DIAGNOSES:
        p1 += f"{dx_name.upper()}{noted}\nDiagnosis: {dx_name}\nNoted on: {noted}\nICD-10-CM: {icd}\n\n"
    pages.append(p1)

    # Page 2: Current Medications
    p2 = header + "\nCurrent Medications\n\n"
    for drug, dose, route, freq in MEDICATIONS:
        status = random.choice(["Active", "Active", "Active", "Discontinued"])
        p2 += f"Medications {drug} ({drug.upper()}) {dose} {route.title()} ({status})\n"
        p2 += f"  Dose: {dose} {freq}\n  Route: {route}\n\n"
    pages.append(p2)

    # Page 3: Lab results
    p3 = header + "\nLab Results\n\n"
    for lab_date_offset in range(0, 60, 3):
        d = base_date + timedelta(days=lab_date_offset * 30)
        date_str = d.strftime("%m/%d/%Y")
        p3 += f"{date_str} - Orders Only in Laboratory\n"
        for name, status, value in random.sample(LABS, min(4, len(LABS))):
            p3 += f"Lab {name} (Final result)\n"
            if value:
                p3 += f"  Result: {value} ({status})\n"
            p3 += f"  Resulted: {date_str}\n\n"
    pages.append(p3)

    # Pages 4-10: Clinical visits spread over 5 years
    for page_idx in range(4, 11):
        page_text = header + "\n"
        n_visits = random.randint(3, 5)
        for _ in range(n_visits):
            days_offset = random.randint(0, 1800)
            visit_date = base_date + timedelta(days=days_offset)
            date_str = visit_date.strftime("%m/%d/%Y")
            visit_type = random.choice(VISIT_TYPES)
            page_text += f"{date_str} - {visit_type}\n"
            page_text += f"Clinical Notes\n\n"

            note = random.choice(NOTES)
            page_text += f"{note}\n\n"

            # Some visits have lab orders
            if random.random() > 0.5:
                for name, status, value in random.sample(LABS, min(3, len(LABS))):
                    page_text += f"Lab {name} (Final result)\n"
                    if value:
                        page_text += f"  Result: {value} ({status})\n"
                    page_text += f"  Resulted: {date_str}\n\n"

            # Some visits have medication changes
            if random.random() > 0.6:
                drug, dose, route, freq = random.choice(MEDICATIONS)
                action = random.choice(["Started", "Continued", "Increased", "Decreased", "Discontinued"])
                page_text += f"Medications {drug} {dose} {route.title()}\n"
                page_text += f"  {action} {drug} {dose} {freq}\n\n"

            # ICD codes on some visits
            if random.random() > 0.4:
                dx_name, icd, _ = random.choice(DIAGNOSES)
                page_text += f"Diagnoses\n{dx_name.upper()} [{icd}]\n\n"

        pages.append(page_text)

    return pages


def generate_synthetic_pdf(output_path: str) -> str:
    """Generate a 10-page PDF with ~200 clinical entries."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    pages = _generate_synthetic_timeline_text()
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for i, page_text in enumerate(pages):
        for line in page_text.split("\n"):
            if not line.strip():
                story.append(Spacer(1, 6))
            else:
                story.append(Paragraph(line, styles["Normal"]))
        if i < len(pages) - 1:
            story.append(Spacer(1, 30))

    doc.build(story)

    # Count entries
    total_entries = 0
    for page in pages:
        total_entries += page.count("Lab ")
        total_entries += page.count("Medications ")
        total_entries += page.count("Diagnosis:")
        total_entries += page.count("ICD-10-CM:")
        total_entries += page.count("Diagnoses\n")
        total_entries += page.count("Clinical Notes")
    print(f"Generated {output_path}: {len(pages)} pages, ~{total_entries} entries")
    return output_path


# ── Chat simulation ──────────────────────────────────────────────────────────

SIMULATED_CHATS = [
    # (day_offset, role, content, anchor_event_ids, importance_note)
    (0, "patient", "Just uploaded my timeline PDF. Feeling nervous about what it shows.", [], "initial_upload"),
    (0, "agent", "[EoHD Report] Comprehensive timeline analysis complete. 8,139 events spanning 2020-2025. Key findings: SLE with nephritis class III, active APS, recurring flares correlating with stress periods.", ["pdf_p0003_e0001", "pdf_p0100_e0000"], "detective_report"),
    (1, "patient", "The report mentions stress correlating with flares. That makes sense — I had a terrible month at work in March 2024 and ended up hospitalized.", ["pdf_p3000_e0000"], "stress_flare_correlation"),
    (2, "doctor", "Reviewing the timeline. The March 2024 hospitalization for pleuritis aligns with the complement drop I see in the labs from Feb 2024. We should watch C3/C4 more closely during stress periods.", ["pdf_p2000_e0000", "pdf_p3000_e0000"], "doctor_clinical_observation"),
    (3, "patient", "ok thanks", [], "low_value_ack"),
    (5, "patient", "How often should I get my complement levels checked?", [], "question_no_anchor"),
    (5, "agent", "Based on your timeline, complement levels (C3/C4) have been checked quarterly. During stress periods, more frequent monitoring (monthly) would help detect flares earlier. Your doctor can adjust the schedule.", [], "agent_guidance"),
    (7, "patient", "My joints hurt today. Both knees and my hands. Started yesterday after a long walk.", [], "symptom_report"),
    (8, "doctor", "Joint pain after activity is common with SLE. Note: this is different from the inflammatory arthralgia pattern we see in the timeline. If it persists >3 days or you develop swelling, come in.", ["pdf_p0100_e0003"], "doctor_differential"),
    (10, "patient", "The joint pain went away. I think it was just overexertion.", [], "resolution"),
    (14, "patient", "Having a really hard week emotionally. My sister was diagnosed with breast cancer. I haven't been sleeping well.", [], "psychosocial_disclosure"),
    (15, "agent", "I'm sorry to hear about your sister. Emotional stress is a known trigger for SLE flares. Your timeline shows a pattern: major stressors in March 2024 preceded a flare by 2-3 weeks. Please consider reaching out to your care team if symptoms change.", ["pdf_p3000_e0000"], "agent_stress_warning"),
    (18, "patient", "Thanks. I talked to my psychiatrist. She increased my sertraline to 100mg.", ["pdf_p0002_e0008"], "med_change_disclosure"),
    (21, "patient", "Feeling better emotionally. Sleep is improving. No new joint pain.", [], "status_update"),
    (25, "patient", "hi", [], "noise"),
    (25, "patient", "Sorry, pocket text", [], "noise"),
    (27, "doctor", "Lab results from yesterday: C3 dropped to 58 from 62. C4 stable at 9. Given the recent stress, I want to see you next week for a full panel. Please monitor for rash, joint swelling, or fever.", ["pdf_p0003_e0002", "pdf_p0003_e0003"], "critical_lab_observation"),
    (28, "patient", "That's concerning. I'll watch closely. The malar rash hasn't appeared but I've had some fatigue the last few days.", [], "patient_monitoring"),
    (29, "agent", "Your C3 trend over the last 6 months: 72 → 65 → 62 → 58. This downward trajectory preceded both prior flares by 3-4 weeks. Current trajectory suggests close monitoring is warranted.", ["pdf_p0003_e0002"], "agent_trend_analysis"),
    (30, "patient", "Coming in tomorrow for labs. Fingers crossed.", [], "anticipation"),
]


def run_simulation(ptv_path: Optional[str] = None, max_chars: int = 5000) -> None:
    """
    Run 20 chats over 30 days and observe decay/eviction behavior.
    Uses a deliberately small budget (5KB) to force evictions.
    """
    print("=" * 78)
    print("  CHAT GRAPH DECAY & EVICTION SIMULATION")
    print("  20 messages over 30 days | Budget: {:,} chars".format(max_chars))
    print("=" * 78)

    if ptv_path:
        with open(ptv_path) as f:
            ptv = json.load(f)
        print(f"  PTV loaded: {len(ptv.get('events', {}))} events")
    else:
        print("  No PTV loaded (standalone mode)")

    config = DEFAULT_DECAY_CONFIG
    patient_id = "syn_maria_vasquez"
    messages: List[ChatMessage] = []
    sim_start = datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc)

    print()
    print(f"{'Day':>4} | {'Role':>8} | {'Content':40} | {'Decay':>6} | {'Active':>6} | {'Chars':>6} | {'Evicted':>7} | Notes")
    print("-" * 130)

    total_evictions = 0

    for day_offset, role, content, anchor_ids, note in SIMULATED_CHATS:
        sim_now = sim_start + timedelta(days=day_offset, hours=random.randint(8, 20))

        msg = ChatMessage(
            message_id=f"sim_{len(messages):03d}",
            patient_id=patient_id,
            role=role,
            content=content,
            created_at=sim_now.isoformat(),
            last_referenced=sim_now.isoformat(),
            decay_score=1.0,
            retention_reason=note,
            anchored_event_ids=anchor_ids,
            reference_edges={},
            author_id=None,
        )

        # Add reference edges based on role/content
        if anchor_ids:
            msg.reference_edges["ptv_event"] = anchor_ids
        if role == "doctor":
            msg.reference_edges["clarification"] = [msg.message_id]
        if role == "agent" and "Report" in content:
            msg.reference_edges["detective_report"] = [msg.message_id]
        if role == "patient" and len(content) > 50:
            msg.reference_edges["journal_entry"] = [msg.message_id]
        if not msg.has_references() and not msg.is_anchored():
            msg.reference_edges["conversation"] = [msg.message_id]

        messages.append(msg)

        # Update ALL decay scores relative to sim_now
        for m in messages:
            if m.evicted_at is None:
                m.decay_score = compute_decay_score(m, sim_now, config)

        # Check eviction
        active = [m for m in messages if m.evicted_at is None]
        current_chars = sum(m.char_count() for m in active)
        to_evict = select_eviction_candidates(active, current_chars, max_chars)
        for ev in to_evict:
            evict_message(ev, reason="budget_enforcement")
            total_evictions += 1

        active_after = [m for m in messages if m.evicted_at is None]
        chars_after = sum(m.char_count() for m in active_after)

        content_preview = content[:38] + ".." if len(content) > 40 else content
        evicted_now = len(to_evict)
        evicted_str = f"+{evicted_now}" if evicted_now else ""

        print(
            f"{day_offset:4d} | {role:>8} | {content_preview:40} | "
            f"{msg.decay_score:6.3f} | {len(active_after):6d} | "
            f"{chars_after:6d} | {evicted_str:>7} | {note}"
        )

    # Final state
    print()
    print("=" * 78)
    print("  FINAL STATE")
    print("=" * 78)

    active_final = [m for m in messages if m.evicted_at is None]
    evicted_final = [m for m in messages if m.evicted_at is not None]

    print(f"\n  Total messages sent: {len(messages)}")
    print(f"  Active (retained):   {len(active_final)}")
    print(f"  Evicted:             {len(evicted_final)}")
    print(f"  Total evictions:     {total_evictions}")
    print(f"  Chars used:          {sum(m.char_count() for m in active_final):,}")

    print(f"\n  === RETAINED MESSAGES (sorted by decay score) ===")
    for m in sorted(active_final, key=lambda x: x.decay_score, reverse=True):
        anchored = f" ⚓{len(m.anchored_event_ids)}" if m.anchored_event_ids else ""
        edges = sum(len(v) for v in m.reference_edges.values())
        print(
            f"  [{m.decay_score:.3f}] day {(datetime.fromisoformat(m.created_at) - sim_start).days:2d} "
            f"{m.role:>8} | {m.content[:55]:55}{anchored} | edges={edges} | {m.retention_reason}"
        )

    print(f"\n  === EVICTED MESSAGES ===")
    for m in evicted_final:
        print(
            f"  [EVICTED] day {(datetime.fromisoformat(m.created_at) - sim_start).days:2d} "
            f"{m.role:>8} | {m.content[:55]:55} | {m.eviction_reason}"
        )

    # Enrichment candidates
    enrichment = build_enrichment_candidates(active_final, min_decay=0.2)
    print(f"\n  === ENRICHMENT CANDIDATES ({len(enrichment)}) ===")
    for m in enrichment:
        print(f"  [{m.decay_score:.3f}] {m.role:>8} | {m.content[:60]}")

    # EoHD context
    eohd_ctx = build_chat_context_for_eohd(active_final, max_chars=3000)
    print(f"\n  === EoHD CONTEXT ({len(eohd_ctx)} chars) ===")
    print(textwrap.indent(eohd_ctx[:1500], "  "))
    if len(eohd_ctx) > 1500:
        print(f"  ... ({len(eohd_ctx) - 1500} more chars)")

    # Verify key behaviors
    print(f"\n  === BEHAVIOR VERIFICATION ===")
    evicted_ids = {m.message_id for m in evicted_final}
    active_ids = {m.message_id for m in active_final}

    checks = []

    # "ok thanks" and "hi" should be evicted (low value)
    noise_msgs = [m for m in messages if m.retention_reason in ("low_value_ack", "noise")]
    noise_evicted = sum(1 for m in noise_msgs if m.message_id in evicted_ids)
    checks.append(("Low-value messages evicted first", noise_evicted >= 2, f"{noise_evicted}/{len(noise_msgs)} evicted"))

    # Doctor messages should be retained longer
    doctor_msgs = [m for m in messages if m.role == "doctor"]
    doctor_active = sum(1 for m in doctor_msgs if m.message_id in active_ids)
    checks.append(("Doctor messages retained", doctor_active >= 2, f"{doctor_active}/{len(doctor_msgs)} active"))

    # Anchored messages should survive
    anchored_msgs = [m for m in messages if m.anchored_event_ids]
    anchored_active = sum(1 for m in anchored_msgs if m.message_id in active_ids)
    checks.append(("Anchored messages survive", anchored_active >= 3, f"{anchored_active}/{len(anchored_msgs)} active"))

    # Critical lab observation (day 27 doctor msg) should survive
    critical_lab = [m for m in messages if m.retention_reason == "critical_lab_observation"]
    critical_active = sum(1 for m in critical_lab if m.message_id in active_ids)
    checks.append(("Critical lab observation retained", critical_active == 1, f"{'active' if critical_active else 'EVICTED'}"))

    # Detective report should survive (high edge boost)
    report_msgs = [m for m in messages if m.retention_reason == "detective_report"]
    report_active = sum(1 for m in report_msgs if m.message_id in active_ids)
    checks.append(("Detective report retained", report_active >= 1, f"{report_active}/{len(report_msgs)} active"))

    for label, passed, detail in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {label}: {detail}")

    all_passed = all(p for _, p, _ in checks)
    print(f"\n  {'✅ ALL CHECKS PASSED' if all_passed else '❌ SOME CHECKS FAILED'}")


# ── Heuristic extraction test ───────────────────────────────────────────────

def test_heuristic_on_synthetic() -> None:
    """Run heuristic extraction on the synthetic timeline text."""
    print("\n" + "=" * 78)
    print("  HEURISTIC EXTRACTION TEST ON SYNTHETIC TIMELINE")
    print("=" * 78)

    from server.eoh.heuristic_page_extract import heuristic_page_extract

    pages = _generate_synthetic_timeline_text()
    total_events = 0
    total_dates = 0

    for i, text in enumerate(pages):
        result = heuristic_page_extract(i + 1, text)
        n_events = len(result.events)
        total_events += n_events
        total_dates += len(result.all_dates)
        by_type = {}
        for e in result.events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        ts_known = sum(1 for e in result.events if e.timestamp != "unknown")
        print(
            f"  Page {i+1:2d}: {n_events:3d} events, "
            f"{ts_known}/{n_events} with timestamps, "
            f"page_date={result.page_date or 'none':10}, "
            f"section={result.section_type or 'none':12}, "
            f"types={dict(by_type)}"
        )

    print(f"\n  Total: {total_events} events, {total_dates} dates found across {len(pages)} pages")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chat Graph Decay & Eviction Test Harness")
    parser.add_argument("--ptv", type=Path, help="Path to PTV JSON for context")
    parser.add_argument("--generate-pdf", type=Path, help="Generate synthetic timeline PDF")
    parser.add_argument("--budget", type=int, default=5000, help="Chat budget in chars (default: 5000 — small to force evictions)")
    parser.add_argument("--skip-heuristic", action="store_true", help="Skip heuristic extraction test")
    args = parser.parse_args()

    if args.generate_pdf:
        generate_synthetic_pdf(str(args.generate_pdf))
        print()

    run_simulation(ptv_path=str(args.ptv) if args.ptv else None, max_chars=args.budget)

    if not args.skip_heuristic:
        test_heuristic_on_synthetic()


if __name__ == "__main__":
    main()
