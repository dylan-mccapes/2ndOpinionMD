#!/usr/bin/env python3
"""
gen_forward_exemplar.py
=======================

Generate a synthetic FORWARD-shaped PatientTimelineVision (PTV) exemplar cohort
of 5 patients, 5 years of PROs each, for Kaleb Michaud's RA-conference and
Congressional presentation materials.

All patient graphs are synthetic, deterministic (seeded per patient), and
clearly labeled via metadata.synthetic=true + a disclaimer field at graph root.
Event previews are clean (no [SYNTHETIC] prefix) so slide screenshots render
well; the synthetic status is unambiguous from metadata and filenames.

Usage
-----
    python server/scripts/gen_forward_exemplar.py

Output
------
    artifacts/forward_exemplar_5pt/
        ptv_synth_P1_early_responder.json
        ptv_synth_P2_escalation_single_flare.json
        ptv_synth_P3_cycler_multi_flare.json
        ptv_synth_P4_subclinical_flare_uc_wins.json
        ptv_synth_P5_honest_uncertainty_missing.json
        MANIFEST.json

Schema
------
Matches production PTV schema (ptv.2.1-forward-exemplar).  In addition to
the primitives in the reference real graph (arcs, cards, salience,
canonical_id, entity_keys, status_flags, connascence including in_workup_for
and caused_by), this generator populates:
  - arc.summary, arc.open_questions, arc.cross_arc_edges
  - event_type "pro", "therapy_episode", "flare", "derived_metric"
  - connascence "pro_shift", "flare_window", "therapy_episode"
  - entity_keys "instrument:haq2" etc. and "rxnorm:<cui>"
  - metadata.synthetic, metadata.disclaimer, metadata.schema_version,
    metadata.study_cohorts, metadata.generator.seed
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "forward_exemplar_5pt"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = "ptv.2.1-forward-exemplar"
GENERATOR_NAME = "gen_forward_exemplar.py"
GENERATOR_VERSION = "1.0.0"
BUILT_AT = datetime.now(timezone.utc).isoformat()

DISCLAIMER = (
    "SYNTHETIC demonstration cohort. All patient data are programmatically "
    "generated for illustration of the 2ndOpinionMD PatientTimelineVision schema "
    "and the Uncertainty-Carrier governance framework (SSRN 6554940). No real "
    "patient records were used, referenced, or derived from. Not for clinical "
    "decision-making. Intended use: conference presentation and FORWARD pilot "
    "shape review."
)

# -----------------------------------------------------------------------------
# Domain constants
# -----------------------------------------------------------------------------

# RxNorm CUIs (ingredient level).  Validate against local RxNav snapshot
# before any production use.
RXNORM = {
    "methotrexate":         "6851",
    "hydroxychloroquine":   "5521",
    "adalimumab":           "327361",
    "etanercept":           "3008",
    "upadacitinib":         "2282525",
    "tofacitinib":          "1187085",
    "prednisone":           "8640",
    "folic_acid":           "4511",
}

# PRO instruments used in FORWARD (subset relevant to this demo).
INSTRUMENTS = {
    "haq2":       {"name": "HAQ-II",               "min": 0,  "max": 3,   "mcid": 0.22},
    "vas_pain":   {"name": "VAS Pain",             "min": 0,  "max": 100, "mcid": 20},
    "vas_global": {"name": "VAS Patient Global",   "min": 0,  "max": 100, "mcid": 20},
    "pas2":       {"name": "PAS-II",               "min": 0,  "max": 10,  "mcid": 0.5},
    "rdci":       {"name": "RDCI",                 "min": 0,  "max": 9,   "mcid": None},
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def canonical_id(*parts: Any) -> str:
    s = "|".join(str(p) for p in parts)
    return "ev_" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def salience_for(event_type: str, status_flags: list[str] | None) -> float:
    base = {
        "pro": 6.2,
        "medication": 5.5,
        "flare": 8.0,
        "therapy_episode": 6.5,
        "derived_metric": 7.2,
        "diagnosis": 7.5,
        "clinical_note": 4.2,
        "visit": 4.5,
    }.get(event_type, 5.0)
    bump = 0.0
    for f in status_flags or []:
        bump += {
            "flare": 1.5, "worsening": 0.8, "acute": 0.8, "stopped": 0.4,
            "improving": 0.2, "chronic": 0.1, "continued": 0.05,
            "titrating": 0.3, "rechallenged": 0.4, "ineffective": 0.6,
        }.get(f, 0.0)
    return round(base + bump + 0.01, 4)


def mk_event(
    *,
    event_id: str,
    event_type: str,
    ts: str,
    title: str,
    annotations: dict[str, Any],
    connascence: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    status_flags = annotations.get("status_flags") or []
    s = salience_for(event_type, status_flags)
    card = {
        "ts": ts or "unknown",
        "icd": annotations.get("icd_code"),
        "drug": annotations.get("drug_name"),
        "type": event_type,
        "title": title,
        "arc_ids": list(annotations.get("arc_ids", [])),
        "one_line": title,
        "salience": s,
        "coverage": annotations.get("coverage") or {
            "has_code": bool(annotations.get("entity_keys")),
            "has_date": bool(ts and ts != "unknown"),
            "has_value": "value" in annotations or "raw_score" in annotations,
            "has_dose": "dose_mg" in annotations,
        },
    }
    ann = {
        "card": card,
        "salience": s,
        "canonical_id": canonical_id(event_id, event_type, ts, title),
        "extracted_by": "synthetic_generator_v1",
        **annotations,
    }
    ann.setdefault("entity_keys", [])
    ann.setdefault("arc_ids", [])
    return {
        "status": "included",
        "preview": title,
        "event_id": event_id,
        "timestamp": ts or "unknown",
        "event_type": event_type,
        "annotations": ann,
        "connascence": connascence or {},
        "discovered_by": [f"{GENERATOR_NAME}@{GENERATOR_VERSION}"],
    }


def mk_arc(
    *,
    arc_id: str,
    name: str,
    status: str = "enriched",
    event_ids: list[str],
    date_range: tuple[str, str],
    summary: str = "",
    open_questions: list[str] | None = None,
    cross_arc_edges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "arc_id": arc_id,
        "status": status,
        "summary": summary,
        "event_ids": list(event_ids),
        "date_range": list(date_range),
        "open_questions": list(open_questions or []),
        "cross_arc_edges": list(cross_arc_edges or []),
    }


def iso(d: date) -> str:
    return d.isoformat()


# -----------------------------------------------------------------------------
# Scenario definitions
# -----------------------------------------------------------------------------

@dataclass
class Scenario:
    code: str
    label: str
    phenotype: str
    seed: int
    sex: str
    age_at_baseline: int
    rdci_baseline: int
    headline: str  # one-line story for the manifest


SCENARIOS: list[Scenario] = [
    Scenario("P1", "early MTX responder", "early_responder",
             seed=101, sex="F", age_at_baseline=52, rdci_baseline=1,
             headline="Early MTX responder; five-year improving trajectory; narrow UCs."),
    Scenario("P2", "MTX -> TNFi escalation, one flare", "escalation_single_flare",
             seed=202, sex="M", age_at_baseline=61, rdci_baseline=2,
             headline="Single flare at year 2 triggers adalimumab add-on; trajectory returns to baseline."),
    Scenario("P3", "cycler, three flares, JAKi end", "cycler_multi_flare",
             seed=303, sex="F", age_at_baseline=45, rdci_baseline=3,
             headline="Three flares over five years; cycles TNFi -> TNFi -> JAKi; wide UCs reflect volatility."),
    Scenario("P4", "hero: subclinical flare predicted by UC", "subclinical_flare_uc_wins",
             seed=404, sex="F", age_at_baseline=38, rdci_baseline=1,
             headline="UC elevated flare probability at rounds 3-4; overt flare at round 5. Governance win."),
    Scenario("P5", "hero: honest uncertainty with missing data", "honest_uncertainty_missing",
             seed=505, sex="M", age_at_baseline=70, rdci_baseline=4,
             headline="Rounds 4 and 6 questionnaires missing; UC widths widen and basis cites insufficient data."),
]


# -----------------------------------------------------------------------------
# Trajectory generators
# -----------------------------------------------------------------------------

ROUNDS = 10              # 10 semi-annual rounds = 5 years
STEP_DAYS = 183          # ~six months


def _baseline_date(sc: Scenario) -> date:
    # 2021-Q1 baseline so the 5-yr trajectory lands in 2025 (recent but past).
    return date(2021, 1, 15) + timedelta(days=(sc.seed % 60) - 30)


def _round_dates(sc: Scenario) -> list[date | None]:
    d0 = _baseline_date(sc)
    r: list[date | None] = [d0 + timedelta(days=STEP_DAYS * i) for i in range(ROUNDS)]
    if sc.phenotype == "honest_uncertainty_missing":
        # Mark rounds 4 and 6 as missing
        r[4] = None
        r[6] = None
    return r


def _trajectory(sc: Scenario) -> list[dict[str, float | None]]:
    """Return one dict per round with the four PRO scores (or None if missing)."""
    rng = random.Random(sc.seed)
    pts: list[dict[str, float | None]] = []

    # Start points per phenotype (HAQ-II, VAS pain, VAS global, PAS-II)
    if sc.phenotype == "early_responder":
        haq, pain, glob, pas2 = 1.40, 65.0, 55.0, 5.5
    elif sc.phenotype == "escalation_single_flare":
        haq, pain, glob, pas2 = 1.10, 50.0, 45.0, 4.5
    elif sc.phenotype == "cycler_multi_flare":
        haq, pain, glob, pas2 = 1.60, 70.0, 65.0, 6.2
    elif sc.phenotype == "subclinical_flare_uc_wins":
        haq, pain, glob, pas2 = 0.80, 35.0, 30.0, 3.0
    elif sc.phenotype == "honest_uncertainty_missing":
        haq, pain, glob, pas2 = 1.30, 55.0, 50.0, 5.0
    else:
        haq, pain, glob, pas2 = 1.00, 40.0, 40.0, 4.0

    # Per-round trajectory rules
    for i in range(ROUNDS):
        if sc.phenotype == "early_responder":
            # Monotonic improvement with small noise
            haq = max(0.3, haq - 0.08 + rng.uniform(-0.03, 0.03))
            pain = max(10, pain - 4.0 + rng.uniform(-3, 3))
            glob = max(10, glob - 3.5 + rng.uniform(-3, 3))
            pas2 = max(1.0, pas2 - 0.35 + rng.uniform(-0.15, 0.15))

        elif sc.phenotype == "escalation_single_flare":
            if i == 4:
                # Flare at round 4
                haq += 0.60
                pain += 25
                glob += 25
                pas2 += 1.5
            elif i == 5:
                # Plateau at flare, escalation starts
                pass
            elif i > 5:
                # Improvement post-adalimumab add-on
                haq = max(0.6, haq - 0.15 + rng.uniform(-0.05, 0.05))
                pain = max(20, pain - 8 + rng.uniform(-3, 3))
                glob = max(20, glob - 7 + rng.uniform(-3, 3))
                pas2 = max(2.0, pas2 - 0.6 + rng.uniform(-0.2, 0.2))

        elif sc.phenotype == "cycler_multi_flare":
            flare_rounds = {2, 5, 8}
            if i in flare_rounds:
                haq += 0.45
                pain += 20
                glob += 18
                pas2 += 1.2
            else:
                haq = max(0.9, haq - 0.10 + rng.uniform(-0.05, 0.08))
                pain = max(30, pain - 5 + rng.uniform(-4, 4))
                glob = max(25, glob - 5 + rng.uniform(-4, 4))
                pas2 = max(3.0, pas2 - 0.30 + rng.uniform(-0.15, 0.15))

        elif sc.phenotype == "subclinical_flare_uc_wins":
            # Rounds 0-2 stable.  Rounds 3-4 subclinical drift (below MCID).
            # Round 5 overt flare.  Post-round-5 recovery on adalimumab.
            if i <= 2:
                haq += rng.uniform(-0.02, 0.02)
                pain += rng.uniform(-2, 2)
                glob += rng.uniform(-2, 2)
                pas2 += rng.uniform(-0.1, 0.1)
            elif i in (3, 4):
                haq += 0.10 + rng.uniform(-0.02, 0.02)       # below 0.22 MCID
                pain += 9 + rng.uniform(-2, 2)                # below 20 MCID
                glob += 8 + rng.uniform(-2, 2)
                pas2 += 0.25 + rng.uniform(-0.05, 0.05)
            elif i == 5:
                haq += 0.35
                pain += 25
                glob += 22
                pas2 += 1.1
            else:
                haq = max(0.55, haq - 0.10 + rng.uniform(-0.03, 0.03))
                pain = max(20, pain - 6 + rng.uniform(-3, 3))
                glob = max(18, glob - 5 + rng.uniform(-3, 3))
                pas2 = max(2.0, pas2 - 0.4 + rng.uniform(-0.15, 0.15))

        elif sc.phenotype == "honest_uncertainty_missing":
            if i == 7:
                haq += 0.40
                pain += 22
                glob += 20
                pas2 += 1.2
            else:
                haq += rng.uniform(-0.03, 0.03)
                pain += rng.uniform(-3, 3)
                glob += rng.uniform(-3, 3)
                pas2 += rng.uniform(-0.15, 0.15)

        # Clip to instrument ranges
        haq_c = round(max(0.0, min(3.0, haq)), 2)
        pain_c = round(max(0.0, min(100.0, pain)), 1)
        glob_c = round(max(0.0, min(100.0, glob)), 1)
        pas2_c = round(max(0.0, min(10.0, pas2)), 2)

        # Missing-round handling
        if sc.phenotype == "honest_uncertainty_missing" and i in (4, 6):
            pts.append({"haq2": None, "vas_pain": None, "vas_global": None, "pas2": None})
        else:
            pts.append({"haq2": haq_c, "vas_pain": pain_c, "vas_global": glob_c, "pas2": pas2_c})

    return pts


# -----------------------------------------------------------------------------
# UC (Uncertainty Carrier) emission
# -----------------------------------------------------------------------------

def _uc_width(points_since_baseline: list[dict[str, float | None]], missing_recent: int) -> float:
    """Simple monotone-in-variance, monotone-in-missingness UC width proxy (0..1)."""
    values = [p["haq2"] for p in points_since_baseline if p["haq2"] is not None]
    if len(values) < 2:
        return 0.60
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    base = min(0.5, math.sqrt(var) * 0.9)
    return round(min(0.95, base + 0.12 * missing_recent), 3)


def _flare_probability(traj: list[dict[str, float | None]], i: int) -> dict[str, Any]:
    """
    Compute a flare probability band and basis list from PRO-composite drift
    since baseline (deterministic; not an LLM call).
    """
    if i == 0:
        return {
            "point_estimate": 0.05,
            "band_90": [0.02, 0.15],
            "basis": ["baseline round; insufficient trajectory data"],
            "confidence": "low",
        }
    # Cumulative MCID-normalized deltas from round 0 (last non-missing)
    def last_known(key: str, up_to: int) -> float | None:
        for j in range(up_to, -1, -1):
            v = traj[j].get(key)
            if v is not None:
                return v
        return None

    haq0 = traj[0]["haq2"]
    pain0 = traj[0]["vas_pain"]
    haqn = last_known("haq2", i)
    painn = last_known("vas_pain", i)
    missing_recent = sum(1 for j in range(max(0, i - 2), i + 1) if traj[j]["haq2"] is None)

    if haq0 is None or haqn is None or pain0 is None or painn is None:
        width = 0.55
        pe = 0.25
        basis = [
            "recent questionnaire(s) missing",
            "insufficient PRO trajectory to compute MCID-normalized delta",
        ]
        return {
            "point_estimate": round(pe, 3),
            "band_90": [round(max(0.01, pe - width / 2), 3), round(min(0.99, pe + width / 2), 3)],
            "basis": basis,
            "confidence": "insufficient_data",
        }

    d_haq = (haqn - haq0) / INSTRUMENTS["haq2"]["mcid"]     # in MCID units
    d_pain = (painn - pain0) / INSTRUMENTS["vas_pain"]["mcid"]
    composite = 0.5 * max(0.0, d_haq) + 0.5 * max(0.0, d_pain)
    pe = round(min(0.95, 0.05 + 0.35 * composite), 3)
    width = _uc_width(traj[: i + 1], missing_recent)
    band = [round(max(0.01, pe - width / 2), 3), round(min(0.99, pe + width / 2), 3)]
    basis = [
        f"HAQ-II delta since baseline = {d_haq:.2f} MCID units",
        f"VAS pain delta since baseline = {d_pain:.2f} MCID units",
        f"rounds with missing data in last 3 rounds: {missing_recent}",
    ]
    if missing_recent:
        basis.append("UC width widened due to missing recent questionnaire(s)")
    conf = "insufficient_data" if missing_recent >= 2 else ("moderate" if width > 0.25 else "high")
    return {
        "point_estimate": pe,
        "band_90": band,
        "basis": basis,
        "confidence": conf,
    }


# -----------------------------------------------------------------------------
# Graph builder
# -----------------------------------------------------------------------------

def _med_course_for(sc: Scenario) -> list[dict[str, Any]]:
    """Return a list of medication courses keyed by ingredient."""
    if sc.phenotype == "early_responder":
        return [
            {"ingredient": "methotrexate",       "start_round": 0,  "stop_round": None,  "dose_mg": 15, "freq": "weekly"},
            {"ingredient": "folic_acid",          "start_round": 0,  "stop_round": None,  "dose_mg": 1,  "freq": "daily"},
            {"ingredient": "hydroxychloroquine",  "start_round": 1,  "stop_round": None,  "dose_mg": 200,"freq": "bid"},
        ]
    if sc.phenotype == "escalation_single_flare":
        return [
            {"ingredient": "methotrexate",       "start_round": 0,  "stop_round": None,  "dose_mg": 20, "freq": "weekly"},
            {"ingredient": "folic_acid",          "start_round": 0,  "stop_round": None,  "dose_mg": 1,  "freq": "daily"},
            {"ingredient": "adalimumab",          "start_round": 5,  "stop_round": None,  "dose_mg": 40, "freq": "q2w"},
        ]
    if sc.phenotype == "cycler_multi_flare":
        return [
            {"ingredient": "methotrexate",       "start_round": 0,  "stop_round": None,  "dose_mg": 20, "freq": "weekly"},
            {"ingredient": "folic_acid",          "start_round": 0,  "stop_round": None,  "dose_mg": 1,  "freq": "daily"},
            {"ingredient": "etanercept",          "start_round": 2,  "stop_round": 5,     "dose_mg": 50, "freq": "weekly"},
            {"ingredient": "adalimumab",          "start_round": 5,  "stop_round": 8,     "dose_mg": 40, "freq": "q2w"},
            {"ingredient": "upadacitinib",        "start_round": 8,  "stop_round": None,  "dose_mg": 15, "freq": "daily"},
        ]
    if sc.phenotype == "subclinical_flare_uc_wins":
        return [
            {"ingredient": "methotrexate",       "start_round": 0,  "stop_round": None,  "dose_mg": 15, "freq": "weekly"},
            {"ingredient": "folic_acid",          "start_round": 0,  "stop_round": None,  "dose_mg": 1,  "freq": "daily"},
            {"ingredient": "adalimumab",          "start_round": 5,  "stop_round": None,  "dose_mg": 40, "freq": "q2w"},
        ]
    if sc.phenotype == "honest_uncertainty_missing":
        return [
            {"ingredient": "methotrexate",       "start_round": 0,  "stop_round": None,  "dose_mg": 12.5, "freq": "weekly"},
            {"ingredient": "hydroxychloroquine",  "start_round": 0,  "stop_round": None,  "dose_mg": 200, "freq": "bid"},
            {"ingredient": "prednisone",          "start_round": 7,  "stop_round": 9,     "dose_mg": 10,  "freq": "daily"},
        ]
    return []


def _flare_rounds(sc: Scenario) -> list[int]:
    return {
        "early_responder": [],
        "escalation_single_flare": [4],
        "cycler_multi_flare": [2, 5, 8],
        "subclinical_flare_uc_wins": [5],
        "honest_uncertainty_missing": [7],
    }[sc.phenotype]


def _uc_anticipation_rounds(sc: Scenario) -> list[int]:
    """Rounds where UC crosses an anticipation threshold even without an overt flare."""
    if sc.phenotype == "subclinical_flare_uc_wins":
        return [3, 4]
    return []


def build_graph(sc: Scenario) -> dict[str, Any]:
    traj = _trajectory(sc)
    dates = _round_dates(sc)
    meds = _med_course_for(sc)
    flare_rounds = _flare_rounds(sc)
    anticip_rounds = _uc_anticipation_rounds(sc)

    patient_id = f"synth_{sc.code.lower()}_{sc.phenotype}"
    events: dict[str, dict[str, Any]] = {}
    arcs: dict[str, dict[str, Any]] = {}

    # --- Diagnosis node (RA) ---
    dx_date = _baseline_date(sc) - timedelta(days=365 * max(1, sc.seed % 5))
    dx_id = f"{sc.code}_dx_ra"
    events[dx_id] = mk_event(
        event_id=dx_id,
        event_type="diagnosis",
        ts=iso(dx_date),
        title="RHEUMATOID ARTHRITIS, SEROPOSITIVE [M05.9]",
        annotations={
            "icd_code": "M05.9",
            "entity_keys": ["icd:m05_9"],
            "arc_ids": ["arc_icd_M05"],
            "status_flags": ["chronic"],
            "heuristic_source": "synthetic_generator",
        },
    )

    # --- RA ICD arc ---
    arcs["arc_icd_M05"] = mk_arc(
        arc_id="arc_icd_M05",
        name="Rheumatoid arthritis (M05)",
        status="enriched",
        event_ids=[dx_id],
        date_range=(iso(dx_date), iso(_baseline_date(sc) + timedelta(days=STEP_DAYS * (ROUNDS - 1)))),
        summary="Seropositive RA; longitudinal PRO trajectory over five years captured via FORWARD semi-annual questionnaires.",
        open_questions=[],
        cross_arc_edges=[],
    )

    # --- PRO events per round ---
    round_pro_ids: list[list[str]] = [[] for _ in range(ROUNDS)]
    for i in range(ROUNDS):
        d = dates[i]
        if d is None:
            # Missing-round marker event (so the graph reflects the gap)
            mid = f"{sc.code}_r{i:02d}_missing"
            events[mid] = mk_event(
                event_id=mid,
                event_type="administrative",
                ts="unknown",
                title=f"Questionnaire round {i + 1}: not completed",
                annotations={
                    "status_flags": ["missing_questionnaire"],
                    "round": i,
                    "entity_keys": [f"round:{i}"],
                    "arc_ids": [f"arc_study_epoch_m{(i+1)*6:02d}"],
                },
            )
            round_pro_ids[i].append(mid)
            continue

        for inst_key, inst in INSTRUMENTS.items():
            if inst_key == "rdci":
                # RDCI is annual; emit once per year (rounds 0,2,4,6,8)
                if i % 2 != 0:
                    continue
                raw = sc.rdci_baseline
            else:
                raw = traj[i].get(inst_key)
                if raw is None:
                    continue
            eid = f"{sc.code}_r{i:02d}_{inst_key}"
            title = f"{inst['name']} = {raw}"
            # Delta-from-baseline flags (status)
            sf: list[str] = ["continued"]
            if inst_key == "haq2" and isinstance(traj[0].get("haq2"), (int, float)) and isinstance(raw, (int, float)):
                d_units = (raw - traj[0]["haq2"]) / inst["mcid"]
                if d_units >= 1.0:
                    sf = ["worsening"]
                elif d_units <= -1.0:
                    sf = ["improving"]
            events[eid] = mk_event(
                event_id=eid,
                event_type="pro",
                ts=iso(d),
                title=title,
                annotations={
                    "instrument": inst["name"],
                    "instrument_key": inst_key,
                    "raw_score": raw,
                    "mcid": inst["mcid"],
                    "units": "index" if inst_key in ("haq2", "pas2") else ("points" if inst_key == "rdci" else "mm"),
                    "self_reported_at": iso(d),
                    "round": i,
                    "entity_keys": [f"instrument:{inst_key}", f"round:{i}"],
                    "arc_ids": [f"arc_study_epoch_m{(i+1)*6:02d}"] + (
                        [f"arc_flare_r{i:02d}"] if i in flare_rounds else []
                    ),
                    "status_flags": sf,
                    "heuristic_source": "synthetic_generator",
                },
            )
            round_pro_ids[i].append(eid)

        # same_encounter connascence within a round
        for a in round_pro_ids[i]:
            peers = [x for x in round_pro_ids[i] if x != a]
            events[a]["connascence"]["same_encounter"] = peers
        # temporal edge to previous round's first event
        if i > 0 and round_pro_ids[i] and round_pro_ids[i - 1]:
            events[round_pro_ids[i][0]]["connascence"].setdefault("temporal", []).append(round_pro_ids[i - 1][0])

    # --- Study-epoch arcs ---
    for i, d in enumerate(dates):
        arc_id = f"arc_study_epoch_m{(i+1)*6:02d}"
        if d is None:
            # Epoch exists even if the round is missing
            midlike = [eid for eid in round_pro_ids[i]]
            dr = (iso(_baseline_date(sc) + timedelta(days=STEP_DAYS * i)),
                  iso(_baseline_date(sc) + timedelta(days=STEP_DAYS * i)))
        else:
            midlike = round_pro_ids[i]
            dr = (iso(d), iso(d))
        arcs[arc_id] = mk_arc(
            arc_id=arc_id,
            name=f"Study epoch month {(i+1)*6}",
            status="locked",
            event_ids=midlike,
            date_range=dr,
            summary=(
                f"FORWARD round {i+1} PROs"
                + (" (not completed)" if d is None else "")
                + "."
            ),
            open_questions=(["Round not completed; UC width widened; consider outreach."]
                            if d is None else []),
            cross_arc_edges=[],
        )

    # --- Medication + therapy_episode events and arcs ---
    for m in meds:
        ing = m["ingredient"]
        start_i = m["start_round"]
        stop_i = m["stop_round"]
        s_d = dates[start_i] or (_baseline_date(sc) + timedelta(days=STEP_DAYS * start_i))
        e_d = (dates[stop_i] or (_baseline_date(sc) + timedelta(days=STEP_DAYS * stop_i))) if stop_i is not None else None

        med_id = f"{sc.code}_med_{ing}"
        ing_title = ing.replace("_", " ").title()
        med_entity_keys = [f"rxnorm:{RXNORM[ing]}", f"ingredient:{ing}"]
        status_flags = ["stopped"] if stop_i is not None else ["continued"]
        events[med_id] = mk_event(
            event_id=med_id,
            event_type="medication",
            ts=iso(s_d),
            title=f"{ing_title} {m['dose_mg']} mg {m['freq']}",
            annotations={
                "drug_name": ing_title,
                "ingredient": ing,
                "rxnorm_cui": RXNORM[ing],
                "dose_mg": m["dose_mg"],
                "dose_unit": "mg",
                "frequency": m["freq"],
                "start_date": iso(s_d),
                "stop_date": iso(e_d) if e_d else None,
                "reason_for_stop": ("ineffective" if stop_i in flare_rounds else ("switch" if stop_i is not None else None)),
                "entity_keys": med_entity_keys,
                "arc_ids": [f"arc_therapy_{ing}"],
                "status_flags": status_flags,
                "drug_norm_source": "synthetic_rxnav_snapshot",
            },
        )

        ep_id = f"{sc.code}_tepi_{ing}"
        events[ep_id] = mk_event(
            event_id=ep_id,
            event_type="therapy_episode",
            ts=iso(s_d),
            title=f"Therapy episode: {ing_title}" + (" (ongoing)" if e_d is None else f" -> {iso(e_d)}"),
            annotations={
                "ingredient": ing,
                "rxnorm_cui": RXNORM[ing],
                "start_date": iso(s_d),
                "stop_date": iso(e_d) if e_d else None,
                "reason_for_stop": events[med_id]["annotations"]["reason_for_stop"],
                "entity_keys": med_entity_keys,
                "arc_ids": [f"arc_therapy_{ing}"],
                "status_flags": status_flags,
            },
        )

        arcs[f"arc_therapy_{ing}"] = mk_arc(
            arc_id=f"arc_therapy_{ing}",
            name=f"Therapy course: {ing_title}",
            status="enriched",
            event_ids=[med_id, ep_id],
            date_range=(iso(s_d), iso(e_d) if e_d else iso(_baseline_date(sc) + timedelta(days=STEP_DAYS * (ROUNDS - 1)))),
            summary=(
                f"{ing_title} started round {start_i+1}"
                + (f"; stopped round {stop_i+1} ({events[med_id]['annotations']['reason_for_stop']})." if stop_i is not None
                   else "; ongoing through study window.")
            ),
            open_questions=[],
            cross_arc_edges=[],
        )

    # --- Flare events and flare arcs ---
    for fi in flare_rounds:
        fdate = dates[fi] or (_baseline_date(sc) + timedelta(days=STEP_DAYS * fi))
        fid = f"{sc.code}_flare_r{fi:02d}"
        events[fid] = mk_event(
            event_id=fid,
            event_type="flare",
            ts=iso(fdate),
            title=f"PRO-composite flare, round {fi+1}",
            annotations={
                "detector": "pro_composite_v1",
                "definition": "worsening >= MCID on HAQ-II AND VAS pain, relative to patient baseline, with treatment-escalation anchor",
                "round": fi,
                "entity_keys": [f"round:{fi}", "flare:pro_composite"],
                "arc_ids": [f"arc_flare_r{fi:02d}"],
                "status_flags": ["flare", "acute"],
            },
            connascence={
                "flare_window": round_pro_ids[fi],
                "same_encounter": round_pro_ids[fi],
            },
        )
        arcs[f"arc_flare_r{fi:02d}"] = mk_arc(
            arc_id=f"arc_flare_r{fi:02d}",
            name=f"Flare window (round {fi+1})",
            status="enriched",
            event_ids=[fid] + round_pro_ids[fi],
            date_range=(iso(fdate), iso(fdate)),
            summary=(
                f"PRO-composite flare detected at round {fi+1}. "
                f"HAQ-II and VAS-pain crossed MCID thresholds against patient baseline; "
                f"treatment escalation recorded within the same epoch."
            ),
            open_questions=(
                [
                    "Earlier UC-anticipated rounds 3-4 suggest a pre-flare signal; would earlier escalation have prevented this event?"
                ] if sc.phenotype == "subclinical_flare_uc_wins" else
                [
                    "Missing rounds reduce confidence in the flare onset date; interpret with the UC width in mind."
                ] if sc.phenotype == "honest_uncertainty_missing" else
                []
            ),
            cross_arc_edges=[],
        )

    # --- UC emissions at overt flare rounds + any anticipation rounds ---
    uc_rounds = sorted(set(list(flare_rounds) + anticip_rounds + [0, ROUNDS - 1]))
    for i in uc_rounds:
        udate = dates[i] or (_baseline_date(sc) + timedelta(days=STEP_DAYS * i))
        uc = _flare_probability(traj, i)
        uid = f"{sc.code}_uc_r{i:02d}"
        anticipation = i in anticip_rounds
        arc_ids = ([f"arc_flare_r{i:02d}"] if i in flare_rounds else []) + [f"arc_study_epoch_m{(i+1)*6:02d}"]
        title = (
            f"UC flare probability = {uc['point_estimate']:.2f} "
            f"(90% band {uc['band_90'][0]:.2f}-{uc['band_90'][1]:.2f}, "
            f"confidence {uc['confidence']})"
        )
        events[uid] = mk_event(
            event_id=uid,
            event_type="derived_metric",
            ts=iso(udate),
            title=title,
            annotations={
                "kind": "uncertainty_carrier",
                "metric": "flare_probability_90",
                "point_estimate": uc["point_estimate"],
                "band_90": uc["band_90"],
                "basis": uc["basis"],
                "confidence": uc["confidence"],
                "round": i,
                "anticipation": anticipation,
                "evidence_event_ids": round_pro_ids[i],
                "governance_ref": "SSRN 6554940 (Uncertainty Carriers)",
                "entity_keys": [f"round:{i}", "uc:flare_probability"],
                "arc_ids": arc_ids,
                "status_flags": (["worsening"] if anticipation else []) + (["flare"] if i in flare_rounds else []),
            },
            connascence={
                "temporal": [e for e in round_pro_ids[i]],
                "flare_window": ([f"{sc.code}_flare_r{i:02d}"] if i in flare_rounds else []),
            },
        )
        # Attach UC to flare arc when present
        if i in flare_rounds:
            arcs[f"arc_flare_r{i:02d}"]["event_ids"].append(uid)

    # --- Cross-arc edges (therapy <-> flare, anticipation <-> flare) ---
    for m in meds:
        ing = m["ingredient"]
        t_arc = f"arc_therapy_{ing}"
        if t_arc not in arcs:
            continue
        for fi in flare_rounds:
            f_arc = f"arc_flare_r{fi:02d}"
            if f_arc not in arcs:
                continue
            # If therapy started at or near a flare round, mark shares_therapy
            if m["start_round"] == fi or m["start_round"] == fi + 1:
                arcs[t_arc]["cross_arc_edges"].append({
                    "peer_arc_id": f_arc, "kind": "initiated_in_response_to", "strength": 1.0
                })
                arcs[f_arc]["cross_arc_edges"].append({
                    "peer_arc_id": t_arc, "kind": "treated_by", "strength": 1.0
                })
            # If therapy stopped at a flare round, mark ineffective
            if m["stop_round"] == fi:
                arcs[t_arc]["cross_arc_edges"].append({
                    "peer_arc_id": f_arc, "kind": "preceded_ineffectiveness", "strength": 0.9
                })

    # Subclinical-flare hero: link the anticipation round's UC to the flare arc
    if sc.phenotype == "subclinical_flare_uc_wins":
        flare_arc = f"arc_flare_r05"
        if flare_arc in arcs:
            for ai in anticip_rounds:
                uc_ev = f"{sc.code}_uc_r{ai:02d}"
                if uc_ev in events:
                    arcs[flare_arc]["cross_arc_edges"].append({
                        "peer_arc_id": f"arc_study_epoch_m{(ai+1)*6:02d}",
                        "kind": "pre_flare_anticipation",
                        "strength": 0.8,
                        "evidence_event_id": uc_ev,
                    })

    # --- metadata.index.by_arc ---
    by_arc = {aid: list(a["event_ids"]) for aid, a in arcs.items()}

    # --- Graph root ---
    graph = {
        "arcs": arcs,
        "events": events,
        "built_at": BUILT_AT,
        "metadata": {
            "synthetic": True,
            "disclaimer": DISCLAIMER,
            "schema_version": SCHEMA_VERSION,
            "study_cohorts": ["FORWARD_RA_2026_PILOT"],
            "intended_use": "conference presentation and FORWARD pilot shape review",
            "generator": {
                "name": GENERATOR_NAME,
                "version": GENERATOR_VERSION,
                "seed": sc.seed,
            },
            "demographics": {
                "sex": sc.sex,
                "age_at_baseline": sc.age_at_baseline,
                "rdci_baseline": sc.rdci_baseline,
            },
            "pro": {
                "source": "forward_synthetic",
                "forward": {"patient_reported_outcomes_channel": True},
                "mirrored_journal_ids": [eid for eid in events if events[eid]["event_type"] == "pro"],
                "instruments": [INSTRUMENTS[k]["name"] for k in INSTRUMENTS],
            },
            "phenotype_label": sc.label,
            "phenotype_headline": sc.headline,
            "index": {"by_arc": by_arc},
        },
        "patient_id": patient_id,
        "session_only": False,
    }
    return graph


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    manifest: dict[str, Any] = {
        "cohort": "FORWARD_RA_2026_PILOT_EXEMPLAR",
        "built_at": BUILT_AT,
        "schema_version": SCHEMA_VERSION,
        "synthetic": True,
        "disclaimer": DISCLAIMER,
        "pilot_scope_agreed_with_kaleb_2026_04_22": {
            "n_patients": 5,
            "followup_years": 5,
            "rounds_per_patient": ROUNDS,
            "data_class": "Patient-Reported Outcomes (FORWARD semi-annual questionnaires)",
            "instruments": [INSTRUMENTS[k]["name"] for k in INSTRUMENTS],
            "out_of_scope": ["labs", "imaging", "biosamples", "-omics", "DAS28"],
        },
        "patients": [],
    }

    for sc in SCENARIOS:
        g = build_graph(sc)
        fname = f"ptv_synth_{sc.code}_{sc.phenotype}.json"
        (OUT_DIR / fname).write_text(json.dumps(g, indent=2), encoding="utf-8")
        n_events = len(g["events"])
        n_arcs = len(g["arcs"])
        manifest["patients"].append({
            "code": sc.code,
            "file": fname,
            "phenotype": sc.phenotype,
            "label": sc.label,
            "headline": sc.headline,
            "n_events": n_events,
            "n_arcs": n_arcs,
            "seed": sc.seed,
            "demographics": g["metadata"]["demographics"],
            "patient_id": g["patient_id"],
        })
        print(f"wrote {fname}  events={n_events}  arcs={n_arcs}")

    (OUT_DIR / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote MANIFEST.json  -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
