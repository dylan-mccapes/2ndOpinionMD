# server/timeline/scgp_parser.py

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

CASE_CONFIG: Dict[int, Dict[str, Any]] = {
    1: {
        "patient_id": "SCGP_RA_001",
        "condition": "rheumatoid_arthritis",
        "case_type": "flare_recognition",
    },
    2: {
        "patient_id": "SCGP_SLE_001",
        "condition": "systemic_lupus_erythematosus",
        "case_type": "flare_recognition",
    },
    3: {
        "patient_id": "SCGP_ASTHMA_001",
        "condition": "asthma",
        "case_type": "flare_recognition",
    },
    4: {
        "patient_id": "SCGP_T1DM_001",
        "condition": "type_1_diabetes_mellitus",
        "case_type": "standard_mke",
    },
    5: {
        "patient_id": "SCGP_UC_001",
        "condition": "ulcerative_colitis",
        "case_type": "standard_mke",
    },
    6: {
        "patient_id": "SCGP_HF_001",
        "condition": "chronic_heart_failure",
        "case_type": "standard_mke",
    },
    7: {
        "patient_id": "SCGP_CROHNS_001",
        "condition": "crohns_disease",
        "case_type": "diagnostic_scenario",
        "misdiagnosis_pattern": "IBS_to_Crohns",
    },
    8: {
        "patient_id": "SCGP_AS_001",
        "condition": "ankylosing_spondylitis",
        "case_type": "diagnostic_scenario",
        "misdiagnosis_pattern": "mechanical_back_pain_to_AS",
    },
    9: {
        "patient_id": "SCGP_MS_001",
        "condition": "multiple_sclerosis",
        "case_type": "diagnostic_scenario",
        "misdiagnosis_pattern": "stress_anxiety_to_MS",
    },
    10: {
        "patient_id": "SCGP_RA_FIBRO_001",
        "condition": "rheumatoid_arthritis_with_fibromyalgia",
        "case_type": "diagnostic_scenario",
        "hidden_comorbidity": "fibromyalgia",
    },
}


@dataclass
class ScgpEvent:
    patient_id: str
    ts: datetime
    event_type: str
    source: str
    structured: Dict[str, Any]
    text: str
    meta: Dict[str, Any]


def _parse_rtf_text(path: str) -> List[str]:
    """Read the RTF and return the content lines as plain text.

    This file is basically:
      - RTF header/control lines
      - Plain text lines (some with tabs) ending in a trailing backslash '\'
    We:
      - drop the RTF header/control-only lines
      - strip off the trailing '\' when present
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    lines = raw.splitlines()
    cleaned: List[str] = []

    for line in lines:
        line = line.rstrip()

        # Keep empty lines as separators
        if not line:
            cleaned.append("")
            continue

        # Drop the main RTF header line
        if line.startswith("{\\rtf"):
            continue

        # Drop pure RTF control lines like:
        #   \margl1440...
        #   \pard\tx720...
        # etc. (no tab characters, just control codes)
        if line.startswith("\\") and "\t" not in line:
            continue

        # Many content lines end with a trailing '\' from RTF;
        # strip exactly one if present.
        if line.endswith("\\"):
            line = line[:-1]

        cleaned.append(line)

    return cleaned


def _parse_date(date_str: str) -> datetime:
    """
    Parse date strings like 'Jan 2019', 'Aug 2024',
    'Aug 2024 (3 days later)', etc.
    """
    base = date_str.split("(")[0].strip()
    parts = base.split()

    # Jan 2019 -> we use 15th as neutral mid-month
    if len(parts) == 2:
        dt = datetime.strptime(base, "%b %Y")
        return dt.replace(day=15, tzinfo=timezone.utc)

    # e.g. 'Aug 15 2019' (not present currently, but future-proof)
    if len(parts) == 3:
        try:
            dt = datetime.strptime(base, "%b %d %Y")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Fallback: now (should not happen if inputs follow spec)
    return datetime.now(timezone.utc)


def _parse_band(band_str: str) -> Optional[int]:
    """
    '3 (moderate)' -> 3
    '4 (flare)' -> 4
    """
    band_str = band_str.strip()
    m = re.match(r"(\d+)", band_str)
    if not m:
        return None
    return int(m.group(1))


def _infer_event_type(band: Optional[int], symptoms: str, interp: str) -> str:
    s = (symptoms + " " + interp).lower()
    if band is not None and band >= 4:
        return "flare"
    if "flare" in s or "exacerbation" in s or "dka" in s or "acute" in s:
        return "flare"
    # Everything else we treat as a visit-level event by default
    if "remission" in s or "stable" in s:
        return "visit"
    return "visit"


def parse_scgp_rtf(path: str) -> List[ScgpEvent]:
    """
    Parse synthetic-patient-timelines.rtf into ScgpEvent objects.

    This function is intentionally self-contained so we can use it
    from both scripts and tests without pulling in DB or Pydantic.
    """
    lines = _parse_rtf_text(path)

    # Locate all "Case N:" boundaries
    case_indices: List[tuple[int, str]] = [
        (i, line)
        for i, line in enumerate(lines)
        if line.startswith("Case ")
    ]

    events: List[ScgpEvent] = []

    for idx, (start_idx, header) in enumerate(case_indices):
        case_number = int(header.split(":")[0].replace("Case", "").strip())
        cfg = CASE_CONFIG.get(case_number)
        if not cfg:
            # Unknown case – skip quietly for now
            continue

        patient_id = cfg["patient_id"]

        # Determine end index: next case or end of file
        if idx + 1 < len(case_indices):
            end_idx = case_indices[idx + 1][0]
        else:
            end_idx = len(lines)

        case_lines = lines[start_idx:end_idx]

        condition_line = next(
            (l for l in case_lines if l.startswith("Condition:")),
            None,
        )
        patient_line = next(
            (l for l in case_lines if l.startswith("Patient:")),
            None,
        )

        condition_text = condition_line.split("Condition:", 1)[1].strip() if condition_line else ""
        patient_text = patient_line.split("Patient:", 1)[1].strip() if patient_line else ""

        # Find the table header and rows after it
        header_idx = None
        for i, l in enumerate(case_lines):
            if l.startswith("Date\tSymptoms\tLabs (key results)\tStability Band\tClinical Interpretation"):
                header_idx = i
                break

        if header_idx is None:
            # Some weird case; skip this case
            continue

        row_lines = []
        for row in case_lines[header_idx + 1 :]:
            if not row.strip():
                break
            # Heuristic: must have at least 5 tab-separated fields
            parts = row.split("\t")
            if len(parts) < 5:
                break
            row_lines.append(row)

        for row in row_lines:
            date_str, symptoms, labs, band_str, interp = row.split("\t", 4)
            ts = _parse_date(date_str)
            band = _parse_band(band_str)
            event_type = _infer_event_type(band, symptoms, interp)

            structured: Dict[str, Any] = {
                "condition": cfg["condition"],
                "case_id": patient_id,
                "stability_band": band,
                "category": cfg["case_type"],
                "symptoms": {
                    "raw": symptoms,
                },
                "labs": {
                    "raw": labs,
                },
            }

            meta: Dict[str, Any] = {
                "scgp_version": "v1",
                "eoh_version": "v5",
                "case_number": case_number,
                "case_header": header,
                "condition_text": condition_text,
                "patient_text": patient_text,
            }
            # Optional labels for diagnostic/misdx cases
            for key in ("misdiagnosis_pattern", "hidden_comorbidity"):
                if key in cfg:
                    meta[key] = cfg[key]

            text = (
                f"{condition_text} | {patient_text} | "
                f"Symptoms: {symptoms} | Labs: {labs} | Interpretation: {interp}"
            )

            events.append(
                ScgpEvent(
                    patient_id=patient_id,
                    ts=ts,
                    event_type=event_type,
                    source="scgp_synthetic",
                    structured=structured,
                    text=text,
                    meta=meta,
                )
            )

    return events
