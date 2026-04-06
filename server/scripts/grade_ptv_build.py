#!/usr/bin/env python3
"""
grade_ptv_build.py — Auto-score a PTV build against the acceptance rubric.

Reads a PatientTimelineVision JSON file and produces a structured scorecard
with pass/fail gates from RUBRIC_PTV_BUILD_ACCEPTANCE_20260301.md.

Usage:
    cd 2ndOpinionMD-MVP/server
    python scripts/grade_ptv_build.py /path/to/patient_timeline_vision_*.json
    python scripts/grade_ptv_build.py /path/to/patient_timeline_vision_*.json --json
    python scripts/grade_ptv_build.py /path/to/patient_timeline_vision_*.json -o scorecard.json

Rubric gates:
    1.1  Timestamp Integrity    >=95% → Accept, 90-95% → Candidate, <90% → Reject
    1.2  Event-Type Accuracy    <=5%  → Accept, 5-10%  → Candidate, >10% → Reject
    1.3  Deduplication          <=10% → Accept, 10-20% → Candidate, >20% → Reject
    1.4  Medication Normal.     >=60% → Accept, 40-60% → Candidate, <40% → Reject
    1.5  Graph Connectivity     <=30% → Accept, 30-50% → Candidate, >50% → Reject

Soft gates and behavioral validations are scored but do not hard-gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPT_DIR = Path(__file__).parent
_SERVER_DIR = _SCRIPT_DIR.parent
_MVP_DIR = _SERVER_DIR.parent
if str(_MVP_DIR) not in sys.path:
    sys.path.insert(0, str(_MVP_DIR))

from server.utils.parse_date import extract_date_from_text, parse_clinical_date

# ── constants ────────────────────────────────────────────────────────────────

CLINICAL_TYPES = frozenset({
    "diagnosis", "lab", "medication", "procedure", "visit",
    "note", "symptom", "imaging", "vital_signs", "allergy",
    "immunization", "flare",
})

BOILERPLATE_TYPES = frozenset({"page"})

# Section keywords → expected event types
SECTION_TYPE_MAP: Dict[str, frozenset] = {
    "problem list": frozenset({"diagnosis"}),
    "immunization": frozenset({"immunization", "procedure"}),
    "current medication": frozenset({"medication"}),
    "medication list": frozenset({"medication"}),
    "active medication": frozenset({"medication"}),
    "lab": frozenset({"lab"}),
    "radiology": frozenset({"imaging"}),
    "vital": frozenset({"vital_signs"}),
}

VACCINE_PATTERNS = re.compile(
    r"\b(vaccin|immuniz|tdap|mmr|hep\s*[ab]|influenza\s+vaccine|covid.?19\s+vaccine"
    r"|pneumo|zoster|shingrix|prevnar|fluvirin|gardasil)\b",
    re.IGNORECASE,
)

DIAGNOSIS_PATTERNS = re.compile(
    r"\b(diabetes|hypertension|asthma|copd|myasthenia|cancer|carcinoma"
    r"|arthritis|heart failure|atrial fibrillation|anemia|depression"
    r"|anxiety|hypothyroid|hyperlipidemia|chronic kidney|osteoporosis"
    r"|stroke|seizure|epilepsy|hepatitis|cirrhosis|pneumonia)\b",
    re.IGNORECASE,
)

DRUG_PATTERNS = re.compile(
    r"\b(mg|mcg|tablet|capsule|injection|oral|inhaler|patch|cream"
    r"|solution|suspension|drops|ointment|gel|spray|suppository"
    r"|prednisone|metformin|lisinopril|atorvastatin|omeprazole"
    r"|metoprolol|amlodipine|gabapentin|tramadol|hydrocodone)\b",
    re.IGNORECASE,
)


# ── gate result types ────────────────────────────────────────────────────────

@dataclass
class GateResult:
    name: str
    metric: float
    threshold_accept: float
    threshold_candidate: float
    level: str  # "accept" | "candidate" | "reject"
    detail: str = ""

    @property
    def emoji(self) -> str:
        return {"accept": "🟢", "candidate": "🟡", "reject": "❌"}[self.level]


@dataclass
class SoftGateResult:
    name: str
    score: str  # "consistent" | "mixed" | "poor" | descriptive
    detail: str = ""


@dataclass
class Scorecard:
    source_file: str
    patient_id: str
    built_at: str
    total_events: int
    clinical_events: int
    hard_gates: List[GateResult] = field(default_factory=list)
    soft_gates: List[SoftGateResult] = field(default_factory=list)
    overall_level: str = ""
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for g in d["hard_gates"]:
            g["emoji"] = {"accept": "🟢", "candidate": "🟡", "reject": "❌"}[g["level"]]
        return d


# ── scoring functions ────────────────────────────────────────────────────────

def _classify_level_low_is_good(value: float, accept: float, candidate: float) -> str:
    """Lower is better (mis-type rate, dup rate, orphan rate)."""
    if value <= accept:
        return "accept"
    if value <= candidate:
        return "candidate"
    return "reject"


def _classify_level_high_is_good(value: float, accept: float, candidate: float) -> str:
    """Higher is better (coverage, drug_name %)."""
    if value >= accept:
        return "accept"
    if value >= candidate:
        return "candidate"
    return "reject"


def score_timestamp_integrity(
    events: Dict[str, Dict[str, Any]],
) -> Tuple[GateResult, Dict[str, Any]]:
    """1.1 — Timestamp coverage, confidence proxy, plausibility."""
    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES}
    total = len(clinical)
    if total == 0:
        return GateResult("1.1 Timestamp Integrity", 0, 95, 90, "reject",
                          "No clinical events"), {}

    now = datetime.now(timezone.utc)
    unknown_count = 0
    future_count = 0
    pre_1900_count = 0
    explicit_count = 0
    recoverable_count = 0

    for e in clinical.values():
        ts_raw = e.get("timestamp", "")
        ts_source = e.get("annotations", {}).get("timestamp_source", "")

        dt = parse_clinical_date(ts_raw)
        if dt is None:
            recovered = extract_date_from_text(e.get("preview", ""))
            if recovered:
                recoverable_count += 1
            unknown_count += 1
            continue

        if dt.year > now.year + 1:
            future_count += 1
        if dt.year < 1900:
            pre_1900_count += 1

        if ts_source in ("explicit_on_line", "section_anchored"):
            explicit_count += 1
        elif ts_source == "":
            explicit_count += 1

    coverage = (total - unknown_count) / total * 100
    future_pct = future_count / total * 100
    level = _classify_level_high_is_good(coverage, 95, 90)

    detail_parts = [
        f"Coverage: {coverage:.1f}% ({total - unknown_count}/{total} have timestamps)",
        f"Future/implausible: {future_count} ({future_pct:.2f}%)",
        f"Pre-1900: {pre_1900_count}",
    ]
    if recoverable_count:
        detail_parts.append(
            f"Recoverable from preview text: {recoverable_count} "
            f"(potential +{recoverable_count/total*100:.1f}%)"
        )

    extras = {
        "unknown_count": unknown_count,
        "future_count": future_count,
        "pre_1900_count": pre_1900_count,
        "recoverable_from_preview": recoverable_count,
        "coverage_pct": round(coverage, 2),
    }

    return GateResult(
        "1.1 Timestamp Integrity", round(coverage, 2), 95, 90, level,
        " | ".join(detail_parts),
    ), extras


def score_event_type_accuracy(
    events: Dict[str, Dict[str, Any]],
) -> Tuple[GateResult, Dict[str, Any]]:
    """1.2 — Mis-typed event detection via heuristic cross-check."""
    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES}
    total = len(clinical)
    if total == 0:
        return GateResult("1.2 Event-Type Accuracy", 100, 5, 10, "reject",
                          "No clinical events"), {}

    mistyped = 0
    mistype_examples: List[str] = []

    for eid, e in clinical.items():
        etype = e.get("event_type", "")
        preview = e.get("preview", "").lower()

        suspect = False
        if etype != "immunization" and etype != "procedure" and VACCINE_PATTERNS.search(preview):
            suspect = True
        if etype == "lab" and DIAGNOSIS_PATTERNS.search(preview) and "result" not in preview:
            suspect = True
        if etype == "diagnosis" and DRUG_PATTERNS.search(preview) and "mg" in preview:
            if not DIAGNOSIS_PATTERNS.search(preview):
                suspect = True

        if suspect:
            mistyped += 1
            if len(mistype_examples) < 5:
                mistype_examples.append(
                    f"{eid}: type={etype}, preview={e.get('preview', '')[:80]}"
                )

    rate = mistyped / total * 100
    level = _classify_level_low_is_good(rate, 5, 10)

    return GateResult(
        "1.2 Event-Type Accuracy", round(rate, 2), 5, 10, level,
        f"Mis-typed: {mistyped}/{total} ({rate:.1f}%)",
    ), {"mistyped_count": mistyped, "examples": mistype_examples}


def score_deduplication(
    events: Dict[str, Dict[str, Any]],
) -> Tuple[GateResult, Dict[str, Any]]:
    """1.3 — Duplicate detection via (preview_80, drug_name, date) hash."""
    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES}
    total = len(clinical)
    if total == 0:
        return GateResult("1.3 Deduplication", 0, 10, 20, "reject",
                          "No clinical events"), {}

    hashes: Counter = Counter()
    for e in clinical.values():
        preview = e.get("preview", "").strip().lower()[:80]
        drug = (e.get("annotations", {}).get("drug_name", "") or "").strip().lower()
        ts = e.get("timestamp", "").strip().lower()
        hashes[(preview, drug, ts)] += 1

    dupes = sum(c - 1 for c in hashes.values() if c > 1)
    rate = dupes / total * 100
    level = _classify_level_low_is_good(rate, 10, 20)

    top_dupes = [(h, c) for h, c in hashes.most_common(5) if c > 1]
    examples = [f"{c}x: {h[0][:60]}" for h, c in top_dupes]

    return GateResult(
        "1.3 Deduplication", round(rate, 2), 10, 20, level,
        f"Duplicate rate: {dupes}/{total} ({rate:.1f}%)",
    ), {"duplicate_count": dupes, "top_clusters": examples}


def score_medication_normalization(
    events: Dict[str, Dict[str, Any]],
) -> Tuple[GateResult, Dict[str, Any]]:
    """1.4 — drug_name, structured fields, RxNorm coverage."""
    meds = {eid: e for eid, e in events.items()
            if e.get("event_type") == "medication"}
    total = len(meds)
    if total == 0:
        return GateResult("1.4 Medication Normalization", 0, 60, 40, "candidate",
                          "No medication events"), {}

    with_drug = 0
    with_dose = 0
    with_route = 0
    with_rxcui = 0

    for e in meds.values():
        ann = e.get("annotations", {})
        if ann.get("drug_name"):
            with_drug += 1
        if ann.get("drug_dosage") or ann.get("dose"):
            with_dose += 1
        if ann.get("drug_route") or ann.get("route"):
            with_route += 1
        if ann.get("rxcui"):
            with_rxcui += 1

    drug_pct = with_drug / total * 100
    level = _classify_level_high_is_good(drug_pct, 60, 40)

    detail_parts = [
        f"drug_name: {with_drug}/{total} ({drug_pct:.1f}%)",
        f"dose/route: {with_dose}/{total}, {with_route}/{total}",
        f"RxNorm: {with_rxcui}/{total} ({with_rxcui/total*100:.1f}%)",
    ]

    return GateResult(
        "1.4 Medication Normalization", round(drug_pct, 2), 60, 40, level,
        " | ".join(detail_parts),
    ), {
        "with_drug_name": with_drug,
        "with_dose": with_dose,
        "with_route": with_route,
        "with_rxcui": with_rxcui,
        "total_meds": total,
    }


def score_graph_connectivity(
    events: Dict[str, Dict[str, Any]],
) -> Tuple[GateResult, Dict[str, Any]]:
    """1.5 — Orphan rate, avg edges, edge type presence."""
    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES}
    total = len(clinical)
    if total == 0:
        return GateResult("1.5 Graph Connectivity", 100, 30, 50, "reject",
                          "No clinical events"), {}

    orphans = 0
    edge_counts: List[int] = []
    edge_types: Counter = Counter()

    for e in clinical.values():
        conn = e.get("connascence", {})
        if isinstance(conn, list):
            n_edges = len(conn)
            edge_counts.append(n_edges)
            if n_edges == 0:
                orphans += 1
            for entry in conn:
                if isinstance(entry, dict):
                    edge_types[entry.get("type", "unknown")] += 1
        elif isinstance(conn, dict):
            n_edges = sum(len(v) for v in conn.values())
            edge_counts.append(n_edges)
            if n_edges == 0:
                orphans += 1
            for kind, targets in conn.items():
                edge_types[kind] += len(targets)
        else:
            edge_counts.append(0)
            orphans += 1

    orphan_rate = orphans / total * 100
    avg_edges = sum(edge_counts) / total if total else 0
    level = _classify_level_low_is_good(orphan_rate, 30, 50)

    key_types = {"temporal", "treatment", "diagnostic"}
    present = key_types & set(edge_types.keys())
    missing = key_types - present

    detail_parts = [
        f"Orphans: {orphans}/{total} ({orphan_rate:.1f}%)",
        f"Avg edges/node: {avg_edges:.1f}",
        f"Edge types: {dict(edge_types.most_common())}",
    ]
    if missing:
        detail_parts.append(f"Missing key types: {missing}")

    return GateResult(
        "1.5 Graph Connectivity", round(orphan_rate, 2), 30, 50, level,
        " | ".join(detail_parts),
    ), {
        "orphan_count": orphans,
        "avg_edges": round(avg_edges, 2),
        "edge_type_counts": dict(edge_types),
        "missing_key_types": sorted(missing),
    }


# ── soft gates ───────────────────────────────────────────────────────────────

def score_section_awareness(events: Dict[str, Dict[str, Any]]) -> SoftGateResult:
    """2.1 — Do events respect their source section types?"""
    checked = 0
    consistent = 0

    for e in events.values():
        preview = e.get("preview", "").lower()
        etype = e.get("event_type", "")
        for section_kw, expected_types in SECTION_TYPE_MAP.items():
            if section_kw in preview:
                checked += 1
                if etype in expected_types:
                    consistent += 1
                break

    if checked == 0:
        return SoftGateResult("2.1 Section Awareness", "not_assessed",
                              "No section keywords detected in previews")
    rate = consistent / checked * 100
    score = "consistent" if rate >= 90 else ("mixed" if rate >= 60 else "poor")
    return SoftGateResult(
        "2.1 Section Awareness", score,
        f"{consistent}/{checked} section-matched ({rate:.1f}%)",
    )


def score_date_clustering(events: Dict[str, Dict[str, Any]]) -> SoftGateResult:
    """2.3 — Detect suspicious date clustering (many diagnoses on same date)."""
    dx_dates: Counter = Counter()
    for e in events.values():
        if e.get("event_type") != "diagnosis":
            continue
        ts = e.get("timestamp", "")
        dt = parse_clinical_date(ts)
        if dt:
            dx_dates[dt.strftime("%Y-%m-%d")] += 1

    if not dx_dates:
        return SoftGateResult("2.3 Clinical Plausibility (Date Clustering)",
                              "not_assessed", "No dated diagnoses")

    top = dx_dates.most_common(5)
    worst_date, worst_count = top[0]
    suspicious = [(d, c) for d, c in top if c > 10]

    if not suspicious:
        return SoftGateResult("2.3 Clinical Plausibility (Date Clustering)",
                              "consistent",
                              f"Max cluster: {worst_count} on {worst_date}")

    return SoftGateResult(
        "2.3 Clinical Plausibility (Date Clustering)", "mixed",
        f"Suspicious clusters: {suspicious} — may be problem-list 'as of' dates",
    )


def score_vocabulary_hygiene(events: Dict[str, Dict[str, Any]]) -> SoftGateResult:
    """2.4 — Check for empty types, 'Other' bucket, narrative in structured fields."""
    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES or e.get("event_type", "") == ""}
    empty_type = sum(1 for e in clinical.values() if not e.get("event_type"))
    long_preview = sum(1 for e in clinical.values() if len(e.get("preview", "")) > 500)
    total = len(clinical) or 1

    issues = []
    if empty_type:
        issues.append(f"{empty_type} events with empty type")
    if long_preview:
        issues.append(f"{long_preview} events with >500char preview (narrative in structured?)")

    score = "consistent" if not issues else "mixed"
    return SoftGateResult("2.4 Vocabulary Hygiene", score, " | ".join(issues) or "Clean")


# ── main grading pipeline ────────────────────────────────────────────────────

def grade_ptv_build(ptv_path: str | Path) -> Scorecard:
    """Load a PTV JSON and produce a full scorecard."""
    ptv_path = Path(ptv_path)
    with open(ptv_path) as f:
        data = json.load(f)

    events = data.get("events", {})
    patient_id = data.get("patient_id", "unknown")
    built_at = data.get("built_at", "unknown")

    clinical = {eid: e for eid, e in events.items()
                if e.get("event_type", "") in CLINICAL_TYPES}

    sc = Scorecard(
        source_file=str(ptv_path),
        patient_id=patient_id,
        built_at=built_at,
        total_events=len(events),
        clinical_events=len(clinical),
    )

    # Hard gates
    gate_fns = [
        score_timestamp_integrity,
        score_event_type_accuracy,
        score_deduplication,
        score_medication_normalization,
        score_graph_connectivity,
    ]
    extras_all: Dict[str, Dict] = {}
    for fn in gate_fns:
        result, extras = fn(events)
        sc.hard_gates.append(result)
        extras_all[result.name] = extras

    # Soft gates
    sc.soft_gates.append(score_section_awareness(events))
    sc.soft_gates.append(score_date_clustering(events))
    sc.soft_gates.append(score_vocabulary_hygiene(events))

    # Overall: worst hard gate wins
    levels = [g.level for g in sc.hard_gates]
    if "reject" in levels:
        sc.overall_level = "reject"
    elif "candidate" in levels:
        sc.overall_level = "candidate"
    else:
        sc.overall_level = "accept"

    emoji = {"accept": "🟢", "candidate": "🟡", "reject": "❌"}[sc.overall_level]
    sc.summary = f"{emoji} Overall: {sc.overall_level.upper()} — {sc.clinical_events} clinical events from {sc.total_events} total"

    return sc


def print_scorecard(sc: Scorecard) -> None:
    """Pretty-print a scorecard to stdout."""
    print("=" * 72)
    print(f"  PTV BUILD ACCEPTANCE SCORECARD")
    print(f"  Patient: {sc.patient_id}")
    print(f"  Built:   {sc.built_at}")
    print(f"  Source:  {sc.source_file}")
    print(f"  Events:  {sc.total_events} total, {sc.clinical_events} clinical")
    print("=" * 72)
    print()

    print("─── HARD GATES (pass/fail) ─────────────────────────────────────────")
    for g in sc.hard_gates:
        print(f"  {g.emoji} {g.name}")
        print(f"     Metric: {g.metric}  (Accept: {g.threshold_accept}, Candidate: {g.threshold_candidate})")
        print(f"     {g.detail}")
        print()

    print("─── SOFT GATES (advisory) ──────────────────────────────────────────")
    for g in sc.soft_gates:
        icon = {"consistent": "🟢", "mixed": "🟡", "poor": "❌"}.get(g.score, "⚪")
        print(f"  {icon} {g.name}: {g.score}")
        if g.detail:
            print(f"     {g.detail}")
        print()

    print("─── OVERALL ────────────────────────────────────────────────────────")
    print(f"  {sc.summary}")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="Grade a PTV build against the acceptance rubric.",
    )
    parser.add_argument("ptv_json", help="Path to patient_timeline_vision_*.json")
    parser.add_argument("--json", action="store_true",
                        help="Output scorecard as JSON instead of pretty-print")
    parser.add_argument("-o", "--output", help="Write scorecard JSON to file")
    args = parser.parse_args()

    sc = grade_ptv_build(args.ptv_json)

    if args.json:
        print(json.dumps(sc.to_dict(), indent=2))
    else:
        print_scorecard(sc)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(sc.to_dict(), f, indent=2)
        print(f"\nScorecard written to {args.output}")

    sys.exit(0 if sc.overall_level == "accept" else 1)


if __name__ == "__main__":
    main()
