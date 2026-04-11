"""
pii_scrub.py — Strip personally identifiable information from clinical text.

Runs during ingestion, BEFORE events reach the graph or database.
Pure regex — no LLM, no network calls. ~0.1ms per page.

Scrubs:
  - MRN / medical record numbers
  - SSN (xxx-xx-xxxx)
  - Phone numbers (US formats)
  - Dates of birth (explicit "DOB:" labels — clinical dates are preserved)
  - Street addresses (number + street name patterns)
  - Patient name headers (Kaiser "Name: LAST, FIRST" pattern)
  - Email addresses
  - Fax numbers

Design:
  - Conservative: only scrubs patterns with high-confidence PII markers
  - Clinical dates, lab values, medication doses are NEVER touched
  - Each scrub inserts a typed placeholder like [MRN] or [PHONE]
  - Caller can pass known patient names for targeted scrubbing
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# ── MRN patterns ─────────────────────────────────────────────────────────────

# "MRN: 110005992681" or "MRN 110005992681" or "Medical Record Number: ..."
_MRN = re.compile(
    r"(?:MRN|Medical\s+Record\s+(?:Number|No\.?|#))[\s:]*(\d{6,15})",
    re.IGNORECASE,
)

# ── SSN ──────────────────────────────────────────────────────────────────────

_SSN = re.compile(
    r"\b(\d{3}-\d{2}-\d{4})\b"
)

# ── Phone numbers ────────────────────────────────────────────────────────────

# Matches: 925-210-8834, (925) 210-8834, 925.210.8834, +1-925-210-8834
_PHONE = re.compile(
    r"(?:\+1[-.\s]?)?"
    r"(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"
)

# ── Fax ──────────────────────────────────────────────────────────────────────

_FAX = re.compile(
    r"(?:Fax|FAX|fax)[\s:]*(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    re.IGNORECASE,
)

# ── DOB (only when explicitly labeled — bare dates are clinical) ─────────────

_DOB = re.compile(
    r"(?:DOB|Date\s+of\s+Birth|D\.O\.B\.?)[\s:]*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)

# ── Email ────────────────────────────────────────────────────────────────────

_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# ── Street address ───────────────────────────────────────────────────────────

# "25 N Via Monte" / "1234 Main St" / "PO Box 1234" etc.
_ADDRESS = re.compile(
    r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3}"
    r"\s*(?:,\s*[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)?"
    r"\s*,?\s*(?:CA|AZ|TX|NY|FL|WA|OR|NV|CO|IL|OH|PA|GA|NC|VA|MA|NJ|MD|MI|MN|WI|MO|TN|IN|SC|AL|LA|KY|OK|CT|IA|UT|MS|AR|KS|NE|NM|WV|ID|HI|NH|ME|MT|RI|DE|SD|ND|AK|VT|WY|DC)"
    r"\s+\d{5}(?:-\d{4})?\b",
    re.MULTILINE,
)

# Simpler address: "25 N Via Monte\nWalnut Creek, CA 94598"
_ADDRESS_MULTILINE = re.compile(
    r"\b\d{1,6}\s+[A-Z][a-zA-Z\s]{2,40}\n[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b",
)

# ── Patient name in header ───────────────────────────────────────────────────

# Kaiser format: "Norman Eric Roberts" appearing after MRN/DOB block
# We handle this via the `known_names` parameter rather than regex guessing.

# Sex is clinically relevant (especially for autoimmune) — never scrub it.


# ── Core scrub function ──────────────────────────────────────────────────────

def scrub_pii(
    text: str,
    known_names: Optional[List[str]] = None,
) -> str:
    """
    Remove PII from clinical text, replacing with typed placeholders.

    Args:
        text: Raw clinical text (e.g. from a PDF page).
        known_names: Optional list of patient name strings to scrub.
                     Each entry is matched case-insensitively as a whole word.

    Returns:
        Scrubbed text with placeholders like [MRN], [PHONE], [DOB], etc.
    """
    # Order matters: longer patterns first to avoid partial matches

    # Fax (before phone, since fax patterns contain phone-like numbers)
    text = _FAX.sub("[FAX]", text)

    # MRN
    text = _MRN.sub("[MRN]", text)

    # SSN
    text = _SSN.sub("[SSN]", text)

    # DOB (only labeled instances)
    text = _DOB.sub("[DOB]", text)

    # Email
    text = _EMAIL.sub("[EMAIL]", text)

    # Address (multiline first, then single-line)
    text = _ADDRESS_MULTILINE.sub("[ADDRESS]", text)
    text = _ADDRESS.sub("[ADDRESS]", text)

    # Phone (after fax/address to avoid double-scrubbing)
    text = _PHONE.sub("[PHONE]", text)

    # Known patient names
    if known_names:
        for name in known_names:
            if not name or len(name) < 2:
                continue
            pattern = re.compile(
                r"\b" + re.escape(name) + r"\b",
                re.IGNORECASE,
            )
            text = pattern.sub("[PATIENT_NAME]", text)

    return text


def scrub_pages(
    pages: List[Tuple[int, str]],
    known_names: Optional[List[str]] = None,
) -> List[Tuple[int, str]]:
    """Scrub PII from a list of (page_num, text) tuples. Returns new list."""
    return [(pn, scrub_pii(txt, known_names)) for pn, txt in pages]


def extract_patient_names_from_header(
    pages: List[Tuple[int, str]],
    max_pages: int = 5,
) -> List[str]:
    """
    Attempt to extract patient name(s) from the first few pages.

    Looks for Kaiser-style header patterns:
      "Norman Eric Roberts"  (after MRN line)
      "ROBERTS, NORMAN"      (name, first format)

    Returns a list of name variants to pass to scrub_pii().
    """
    names: List[str] = []
    seen: set = set()

    # Pattern: "MRN: ...\n...DOB: ...\nSex: ...\nPatientName" or similar
    _name_near_mrn = re.compile(
        r"(?:MRN|Medical\s+Record)[^\n]*\n"
        r"(?:.*?(?:DOB|Date\s+of\s+Birth)[^\n]*\n)?"
        r"(?:.*?Sex:[^\n]*\n)?"
        r"\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$",
        re.MULTILINE | re.IGNORECASE,
    )

    # "LAST, FIRST MIDDLE" format
    _name_comma = re.compile(
        r"\b([A-Z]{2,})\s*,\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
    )

    # Kaiser concatenated: text runs "...8834Norman Eric RobertsMRN: 110005992681"
    # Name sits between a phone/address block and MRN
    _name_before_mrn = re.compile(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
        r"(?=\s*(?:MRN|Medical\s+Record))",
        re.MULTILINE,
    )

    # "Patient: FIRST LAST" or "Patient Name: FIRST LAST"
    _name_patient_label = re.compile(
        r"Patient(?:\s+Name)?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
    )

    def _add_name(name: str) -> None:
        name = name.strip()
        if len(name) < 4 or name.lower() in seen:
            return
        # Skip common false positives
        skip_phrases = {
            "release of", "kaiser permanente", "problem list",
            "medical information", "walnut creek", "active coverage",
            "kaiser permanente disclosure", "clinical notes",
            "office visit", "telephone visit", "secure message",
            "lab results", "vital signs", "current medications",
            "medication list", "problem list continued",
        }
        if name.lower() in skip_phrases:
            return
        skip_words = {
            "kaiser", "permanente", "disclosure", "information",
            "release", "continued", "patient", "clinical",
            "medical", "active", "coverage", "hospital",
        }
        if name.lower() in skip_words:
            return
        seen.add(name.lower())
        names.append(name)
        for part in name.split():
            if len(part) > 2 and part.lower() not in seen:
                seen.add(part.lower())
                names.append(part)

    for pn, txt in pages[:max_pages]:
        chunk = txt[:1500]

        for m in _name_near_mrn.finditer(chunk):
            _add_name(m.group(1))

        for m in _name_before_mrn.finditer(chunk):
            _add_name(m.group(1))

        for m in _name_patient_label.finditer(chunk):
            _add_name(m.group(1))

        for m in _name_comma.finditer(chunk):
            last = m.group(1).strip().title()
            first = m.group(2).strip()
            _add_name(f"{first} {last}")
            _add_name(last)
            _add_name(first)

    return names
