"""
Canonical date parser for all of 2ndOpinionMD.

Usage:
    from server.utils.parse_date import parse_clinical_date, extract_date_from_text

    dt = parse_clinical_date("01/15/2020")      # datetime(2020, 1, 15, ...)
    dt = parse_clinical_date("2020-01-15")       # datetime(2020, 1, 15, ...)
    dt = parse_clinical_date("January 15, 2020") # datetime(2020, 1, 15, ...)
    dt = parse_clinical_date("March 2022")       # datetime(2022, 3, 1, ...)
    dt = parse_clinical_date("2019")             # datetime(2019, 1, 1, ...)
    dt = parse_clinical_date("unknown")          # None
    dt = parse_clinical_date("")                 # None

    # Extract a date from free text (e.g. a preview string):
    dt = extract_date_from_text("02/11/2016 - Patient Secure Message in Adult...")
    # datetime(2016, 2, 11, ...)

Returns a timezone-aware (UTC) datetime or None.

Challenge rating: Easy.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as _du_parser


_SKIP = frozenset({"unknown", "n/a", "none", "", "null", "unavailable", "not available"})

_DATE_PATTERN = re.compile(
    r"\b("
    r"\d{1,2}/\d{1,2}/\d{2,4}"           # MM/DD/YYYY or M/D/YY
    r"|\d{4}-\d{2}-\d{2}"                 # YYYY-MM-DD
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
    r"\s+\d{1,2},?\s+\d{4}"              # Month DD, YYYY
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
    r"\s+\d{4}"                            # Month YYYY
    r"|\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*-\d{2,4}"  # DD-Mon-YYYY
    r")",
    re.IGNORECASE,
)

_YEAR_ONLY = re.compile(r"^((?:19|20)\d{2})$")
_MONTH_YEAR = re.compile(
    r"^((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*)\s+((?:19|20)\d{2})$",
    re.IGNORECASE,
)


def _make_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_clinical_date(raw: str | None) -> Optional[datetime]:
    """Parse any reasonable date string into a UTC-aware datetime.

    Returns None for empty, null, or unparseable input.  Never raises.
    """
    if raw is None:
        return None
    s = raw.strip()
    if s.lower() in _SKIP:
        return None

    # Fast path: strict ISO (covers YYYY-MM-DD and full ISO 8601)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return _make_utc(dt)
    except (ValueError, TypeError):
        pass

    # Year-only: "2019" → 2019-01-01
    m = _YEAR_ONLY.match(s)
    if m:
        return datetime(int(m.group(1)), 1, 1, tzinfo=timezone.utc)

    # Month + Year: "March 2022" → 2022-03-01
    m = _MONTH_YEAR.match(s)
    if m:
        try:
            dt = _du_parser.parse(f"{m.group(1)} 1, {m.group(2)}")
            return _make_utc(dt)
        except Exception:
            pass

    # Flexible path: dateutil handles MM/DD/YYYY, "March 15, 2020", etc.
    try:
        dt = _du_parser.parse(s)
        return _make_utc(dt)
    except Exception:
        pass

    return None


def extract_date_from_text(text: str | None) -> Optional[datetime]:
    """Extract and parse the first date-like string from free text.

    Useful for recovering timestamps from event previews when the
    extraction LLM returned 'unknown'.  Never raises.
    """
    if not text:
        return None
    m = _DATE_PATTERN.search(text)
    if m:
        return parse_clinical_date(m.group(0))
    return None
