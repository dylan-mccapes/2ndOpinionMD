"""
heuristic_page_extract.py — Pre-LLM heuristic extraction from raw PDF page text.

Pure Python. No LLM calls. Runs before eoh-llama touches anything.
Extracts dates, medications, labs, diagnoses, and section context using
regex and pattern matching. The LLM then corrects and supplements the skeleton.

Design:
    - Cheap: ~0.5ms per page on CPython
    - Conservative: prefers false negatives over false positives
    - Transparent: every extracted field carries a `source` tag
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from server.utils.parse_date import extract_date_from_text, parse_clinical_date

# ── date patterns ────────────────────────────────────────────────────────────

# Kaiser encounter header: "MM/DD/YYYY - Visit Type in Department (continued)"
_ENCOUNTER_HEADER = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*(.+?)(?:\s*\(continued\))?$",
    re.MULTILINE,
)

# "Noted on: MM/DD/YYYY"
_NOTED_ON = re.compile(
    r"Noted\s+on:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# "Collected: M/DD/YYYY" or "Collected by: ... MM/DD/YY HHMM"
_COLLECTED = re.compile(
    r"Collected(?:\s+by)?:\s*(?:\S+\s+)?(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# "Resulted: MM/DD/YY HHMM"
_RESULTED = re.compile(
    r"Resulted:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# "Electronically signed by: ... on MM/DD/YY"
_SIGNED_ON = re.compile(
    r"(?:Electronically\s+)?signed\s+by:.*?on\s+(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# "as of MM/DD/YYYY" (problem list header)
_AS_OF = re.compile(
    r"as\s+of\s+(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# "Sent and DeliveredM/DD/YYYY" or "Sent and Delivered M/DD/YYYY"
_SENT_DELIVERED = re.compile(
    r"Sent\s+and\s+Delivered\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# General MM/DD/YYYY or MM/DD/YY anywhere in text
_ANY_DATE = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"
)

# ISO date YYYY-MM-DD
_ISO_DATE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2})\b"
)


# ── section type detection ───────────────────────────────────────────────────

_SECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"Problem\s+List", re.I), "diagnosis"),
    (re.compile(r"Immunization", re.I), "procedure"),
    (re.compile(r"(?:Current|Active)\s+Medication", re.I), "medication"),
    (re.compile(r"Medication\s+List", re.I), "medication"),
    (re.compile(r"(?:Orders\s+Only\s+in\s+)?Laboratory", re.I), "lab"),
    (re.compile(r"Lab\s+(?:Results?|Service)", re.I), "lab"),
    (re.compile(r"Clinical\s+Notes?", re.I), "note"),
    (re.compile(r"Office\s+Visit", re.I), "visit"),
    (re.compile(r"Telephone\s+(?:Visit|in)", re.I), "visit"),
    (re.compile(r"Appointment\s+in", re.I), "visit"),
    (re.compile(r"(?:Allied\s+Health|Nurse)\s+Visit", re.I), "procedure"),
    (re.compile(r"(?:Secure\s+)?Message", re.I), "note"),
    (re.compile(r"Imaging|Radiology|CT\s+Scan|MRI|X-?Ray|Ultrasound", re.I), "imaging"),
    (re.compile(r"Pulmonary\s+Function", re.I), "procedure"),
    (re.compile(r"Vital\s+Signs?", re.I), "vital_signs"),
    (re.compile(r"Surgical\s+Pathology", re.I), "procedure"),
]


# ── ICD code extraction ─────────────────────────────────────────────────────

# ICD-10-CM: X99.99 or [X99.99]
_ICD10_EXPLICIT = re.compile(
    r"ICD-10-CM:\s*([A-Z]\d{2}(?:\.\d{1,4})?)",
    re.IGNORECASE,
)
_ICD10_BRACKET = re.compile(
    r"\[([A-Z]\d{2}(?:\.\d{1,4})?)\]",
)

# ICD-9: 3-5 digit codes (less precise, only extract if explicitly labeled)
_ICD9_EXPLICIT = re.compile(
    r"ICD-9(?:-CM)?:\s*(\d{3}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


# ── medication patterns ──────────────────────────────────────────────────────

# "Drug Name (BRAND) dose% route form (status)"
# e.g. "Fluorouracil (EFUDEX) 5 % Top Crea (Discontinued)"
# e.g. "methotrexate 15 mg tablet"
_MED_DOSE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|mL|%|units?|meq)\b",
    re.IGNORECASE,
)

_MED_ROUTE = re.compile(
    r"\b(oral|PO|IV|IM|SC|subcut|topical|Top|inhaled|nasal|rectal|ophthalmic|otic|sublingual|transdermal|patch)\b",
    re.IGNORECASE,
)

_MED_FORM = re.compile(
    r"\b(tablet|cap(?:sule)?|solution|suspension|injection|cream|ointment|gel|spray|drops|inhaler|patch|suppository|syrup|elixir|powder|lozenge)\b",
    re.IGNORECASE,
)

_MED_STATUS = re.compile(
    r"\((Discontinued|Active|Completed|On Hold|Pending|Expired)\)",
    re.IGNORECASE,
)

# Drug name followed by optional brand in parens, then dose
# Matches: "Fluorouracil (EFUDEX) 5 % Top Crea"
#          "pyridostigmine 60 mg"
#          "prednisone 20 mg oral tablet"
_MED_LINE = re.compile(
    r"(?:^|\n)\s*([A-Za-z][\w\s-]{2,40}?)"              # drug name
    r"(?:\s*\(([A-Z][\w\s-]+)\))?"                       # optional brand
    r"\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|%|units?|meq))" # dose required
    r"(.*?)(?:\n|$)",                                      # rest of line
    re.IGNORECASE | re.MULTILINE,
)

# Medication orders: "Medications Drug (BRAND) dose form (status) [order_id]"
_MED_ORDER = re.compile(
    r"Medications?\s+([A-Za-z][\w\s/-]{2,50}?)"
    r"(?:\s*\(([A-Z][\w\s-]+)\))?"
    r"\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|%|units?|meq))",
    re.IGNORECASE,
)


# ── lab patterns ─────────────────────────────────────────────────────────────

# Component-value line: "ComponentName value Unit"
# e.g. "FVC pre bronchodilation, spirometry3.02L"
# e.g. "AST 43 U/L"
_LAB_RESULT = re.compile(
    r"(?:^|\n)\s*([A-Za-z][\w\s,/()-]{3,60}?)\s*"
    r"(\d+(?:\.\d+)?)\s*"
    r"(mg/dL|g/dL|mL/min|U/L|IU/L|mmol/L|mEq/L|ng/mL|pg/mL|"
    r"mcg/dL|%|mm/hr|sec|L|L/sec|cells/mcL|x10\^?[39]/[muL]+|"
    r"thou/cu\s*mm|mill/cu\s*mm)?",
    re.IGNORECASE | re.MULTILINE,
)

# Named lab orders: "Lab TEST_NAME (status) [order_id]"
_LAB_ORDER = re.compile(
    r"Lab\s+([A-Z][\w\s,/()-]{3,80}?)\s*"
    r"(?:\((?:Final|Preliminary|Edited)\s*(?:result|Result)?\s*-?\s*(?:FINAL)?\))",
    re.IGNORECASE,
)


# ── diagnosis patterns ───────────────────────────────────────────────────────

# Problem list entry: "CONDITION NAMEdate" or "CONDITION  MM/DD/YYYY"
# Kaiser format: condition name runs directly into date without space
# e.g. "HYPERLIPIDEMIA06/10/2004" or "PAIN, CHRONIC..05/05/2006"
_PROBLEM_LIST_ENTRY = re.compile(
    r"(?:^|\n)\s*(?:•\s*)?([A-Z][A-Z\s,./()-]{2,80}?)"
    r"\.{0,3}\s*"
    r"(\d{1,2}/\d{1,2}/\d{2,4})",
    re.MULTILINE,
)

_DIAGNOSIS_LABEL = re.compile(
    r"Diagnosis(?:es)?:\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)


# ── result types ─────────────────────────────────────────────────────────────

@dataclass
class HeuristicEvent:
    event_type: str
    timestamp: str  # "YYYY-MM-DD" or "unknown"
    preview: str
    source: str  # which heuristic found this
    drug_name: str = ""
    drug_dosage: str = ""
    drug_route: str = ""
    icd_code: str = ""
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "preview": self.preview[:80],
            "heuristic_source": self.source,
        }
        if self.drug_name:
            d["drug_name"] = self.drug_name
        if self.drug_dosage:
            d["drug_dosage"] = self.drug_dosage
        if self.drug_route:
            d["drug_route"] = self.drug_route
        if self.icd_code:
            d["icd_code"] = self.icd_code
        return d


@dataclass
class HeuristicPageResult:
    page_num: int
    page_date: Optional[str] = None  # encounter-level date (YYYY-MM-DD)
    section_type: Optional[str] = None
    section_header: Optional[str] = None
    events: List[HeuristicEvent] = field(default_factory=list)
    all_dates: List[str] = field(default_factory=list)  # every date found on page

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_num": self.page_num,
            "page_date": self.page_date,
            "section_type": self.section_type,
            "section_header": self.section_header,
            "events": [e.to_dict() for e in self.events],
            "dates_found": len(self.all_dates),
        }


# ── core extraction ──────────────────────────────────────────────────────────

def _normalize_date(raw: str) -> Optional[str]:
    """Parse a date string and return YYYY-MM-DD or None."""
    dt = parse_clinical_date(raw)
    if dt is None:
        return None
    if dt.year > datetime.now(timezone.utc).year + 1 or dt.year < 1900:
        return None
    return dt.strftime("%Y-%m-%d")


def _extract_page_date(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract the primary encounter date, section type, and header from page text."""
    # Encounter header is highest priority
    m = _ENCOUNTER_HEADER.search(text[:500])
    if m:
        date_str = _normalize_date(m.group(1))
        header = m.group(2).strip()
        section = None
        for pat, stype in _SECTION_PATTERNS:
            if pat.search(header):
                section = stype
                break
        return date_str, section, header

    return None, None, None


def _extract_section_type(text: str) -> Optional[str]:
    """Detect section type from page text."""
    for pat, stype in _SECTION_PATTERNS:
        if pat.search(text[:600]):
            return stype
    return None


def _extract_all_dates(text: str) -> List[str]:
    """Find all parseable dates in page text. Returns YYYY-MM-DD strings."""
    dates = set()
    for m in _ANY_DATE.finditer(text):
        d = _normalize_date(m.group(1))
        if d:
            dates.add(d)
    for m in _ISO_DATE.finditer(text):
        d = _normalize_date(m.group(1))
        if d:
            dates.add(d)
    return sorted(dates)


# "Diagnosis: CONDITION NAME" pattern often precedes ICD codes
_DX_LABEL_BEFORE_ICD = re.compile(
    r"Diagnosis:\s*([A-Z][A-Z\s,./()-]{2,80}?)(?=\s*(?:Noted|Chronic|ICD|\n|$))",
    re.IGNORECASE,
)


def _extract_icd_codes(text: str) -> List[Tuple[str, str]]:
    """Extract (icd_code, condition_name) tuples."""
    results = []
    seen_codes: set = set()

    # First pass: "Diagnosis: CONDITION\n...ICD-10-CM: CODE" blocks
    for m in _DX_LABEL_BEFORE_ICD.finditer(text):
        condition = m.group(1).strip()
        after = text[m.end():m.end() + 200]
        icd_m = _ICD10_EXPLICIT.search(after)
        if icd_m and icd_m.group(1) not in seen_codes:
            seen_codes.add(icd_m.group(1))
            results.append((icd_m.group(1), condition))

    # Second pass: [CODE] in brackets with preceding context
    for m in _ICD10_BRACKET.finditer(text):
        code = m.group(1)
        if code in seen_codes:
            continue
        seen_codes.add(code)
        start = max(0, m.start() - 80)
        context = text[start:m.start()].strip().split("\n")[-1].strip()
        # Clean trailing punctuation and ICD labels
        context = re.sub(r"\s*ICD-10-CM:\s*$", "", context).strip()
        context = re.sub(r"\s*Diagnoses\s*$", "", context, flags=re.I).strip()
        results.append((code, context))

    # Third pass: remaining ICD-10-CM: CODE not yet captured
    for m in _ICD10_EXPLICIT.finditer(text):
        code = m.group(1)
        if code in seen_codes:
            continue
        seen_codes.add(code)
        start = max(0, m.start() - 80)
        context = text[start:m.start()].strip().split("\n")[-1].strip()
        context = re.sub(r"\s*ICD-10-CM:\s*$", "", context).strip()
        results.append((code, context))

    return results


def _extract_medications(text: str) -> List[HeuristicEvent]:
    """Extract medication events from page text."""
    meds = []
    seen_drugs: set = set()

    for m in _MED_LINE.finditer(text):
        drug = m.group(1).strip().rstrip("(").strip()
        if len(drug) < 3 or drug.lower() in ("the", "and", "for", "with", "this"):
            continue
        # Skip if it looks like a section header
        if any(kw in drug.lower() for kw in ("visit", "note", "result", "order", "status")):
            continue
        dose = m.group(3).strip()
        rest = m.group(4) if m.group(4) else ""
        route_m = _MED_ROUTE.search(rest) or _MED_ROUTE.search(dose)
        route = _normalize_route(route_m.group(1)) if route_m else ""

        drug_key = drug.lower().split()[0]
        if drug_key in seen_drugs:
            continue
        seen_drugs.add(drug_key)

        meds.append(HeuristicEvent(
            event_type="medication",
            timestamp="unknown",
            preview=f"{drug} {dose}".strip()[:80],
            source="regex_med_line",
            drug_name=drug.split("(")[0].strip(),
            drug_dosage=dose,
            drug_route=route,
        ))

    for m in _MED_ORDER.finditer(text):
        drug = m.group(1).strip()
        if len(drug) < 3:
            continue
        drug_key = drug.lower().split()[0]
        if drug_key in seen_drugs:
            continue
        seen_drugs.add(drug_key)
        dose = m.group(3).strip()

        meds.append(HeuristicEvent(
            event_type="medication",
            timestamp="unknown",
            preview=f"{drug} {dose}".strip()[:80],
            source="regex_med_order",
            drug_name=drug.split("(")[0].strip(),
            drug_dosage=dose,
        ))

    return meds


def _normalize_route(raw: str) -> str:
    """Normalize route string to standard values."""
    r = raw.lower().strip()
    mapping = {
        "po": "oral", "oral": "oral",
        "iv": "IV", "im": "IM", "sc": "SC", "subcut": "SC",
        "top": "topical", "topical": "topical",
        "inhaled": "inhaled", "nasal": "nasal", "rectal": "rectal",
        "ophthalmic": "ophthalmic", "otic": "otic",
        "sublingual": "oral", "transdermal": "topical", "patch": "topical",
    }
    return mapping.get(r, r)


def _extract_labs(text: str) -> List[HeuristicEvent]:
    """Extract lab events from page text."""
    labs = []

    for m in _LAB_ORDER.finditer(text):
        name = m.group(1).strip()
        if len(name) < 2 or len(name) > 80:
            continue
        labs.append(HeuristicEvent(
            event_type="lab",
            timestamp="unknown",
            preview=name[:80],
            source="regex_lab_order",
        ))

    return labs


def _extract_diagnoses(text: str) -> List[HeuristicEvent]:
    """Extract diagnosis events from problem list entries and ICD codes."""
    dx = []
    seen: set = set()

    for m in _PROBLEM_LIST_ENTRY.finditer(text):
        condition = m.group(1).strip().rstrip("•").strip()
        date_raw = m.group(2)
        if len(condition) < 3 or len(condition) > 80:
            continue
        if condition.lower() in seen:
            continue
        # Skip obvious non-diagnoses
        if any(kw in condition.lower() for kw in (
            "release of", "kaiser", "generated", "page", "patient"
        )):
            continue
        seen.add(condition.lower())
        ts = _normalize_date(date_raw) or "unknown"
        dx.append(HeuristicEvent(
            event_type="diagnosis",
            timestamp=ts,
            preview=condition[:80],
            source="regex_problem_list",
        ))

    for icd, context in _extract_icd_codes(text):
        context_clean = context.strip().rstrip("[").strip()
        if context_clean.lower() in seen:
            continue
        if len(context_clean) < 3:
            context_clean = icd
        seen.add(context_clean.lower())
        dx.append(HeuristicEvent(
            event_type="diagnosis",
            timestamp="unknown",
            preview=f"{context_clean} [{icd}]"[:80],
            source="regex_icd_code",
            icd_code=icd,
        ))

    return dx


def _extract_noted_dates(text: str) -> List[Tuple[str, str]]:
    """Extract 'Noted on:' dates with preceding context."""
    results = []
    for m in _NOTED_ON.finditer(text):
        d = _normalize_date(m.group(1))
        if d:
            start = max(0, m.start() - 120)
            context = text[start:m.start()].strip().split("\n")[-1]
            results.append((d, context))
    return results


# ── main entry point ─────────────────────────────────────────────────────────

def heuristic_page_extract(page_num: int, text: str) -> HeuristicPageResult:
    """
    Run all heuristic extractors on a single page of raw PDF text.

    Returns a HeuristicPageResult with the page-level date, section type,
    and all extracted events. Each event carries a `source` tag identifying
    which heuristic found it.

    Pure Python. No LLM. ~0.5ms per page.
    """
    result = HeuristicPageResult(page_num=page_num)

    # Page-level context
    page_date, section_type, header = _extract_page_date(text)
    result.page_date = page_date
    result.section_type = section_type or _extract_section_type(text)
    result.section_header = header

    # All dates on page (for timestamp recovery)
    result.all_dates = _extract_all_dates(text)

    # Extract events by type
    result.events.extend(_extract_medications(text))
    result.events.extend(_extract_labs(text))
    result.events.extend(_extract_diagnoses(text))

    # Apply page date to events that have unknown timestamps
    if page_date:
        for ev in result.events:
            if ev.timestamp == "unknown":
                ev.timestamp = page_date
                ev.source += "+page_date"

    # Apply section type to events without explicit typing if section is clear
    if result.section_type:
        for ev in result.events:
            if ev.confidence < 0.7:
                ev.event_type = result.section_type

    return result


def heuristic_extract_batch(
    pages: List[Tuple[int, str]],
) -> Dict[int, HeuristicPageResult]:
    """Run heuristic extraction on a batch of pages. Returns page_num -> result."""
    return {pn: heuristic_page_extract(pn, txt) for pn, txt in pages}


def skeleton_for_llm(
    page_num: int,
    text: str,
    heuristic: HeuristicPageResult,
) -> str:
    """
    Build a compact skeleton string for the LLM prompt.
    The LLM sees what heuristics already found and only needs to
    correct, supplement, and add what was missed.
    """
    parts = []
    if heuristic.page_date:
        parts.append(f"page_date: {heuristic.page_date}")
    if heuristic.section_type:
        parts.append(f"section: {heuristic.section_type}")
    if heuristic.events:
        parts.append(f"pre_extracted: {len(heuristic.events)} events")
        for ev in heuristic.events[:10]:
            line = f"  - {ev.event_type}: {ev.preview[:60]}"
            if ev.timestamp != "unknown":
                line += f" [{ev.timestamp}]"
            if ev.drug_name:
                line += f" (drug={ev.drug_name})"
            if ev.icd_code:
                line += f" (icd={ev.icd_code})"
            parts.append(line)
    if heuristic.all_dates and not heuristic.page_date:
        parts.append(f"dates_on_page: {', '.join(heuristic.all_dates[:5])}")

    return "\n".join(parts) if parts else ""
