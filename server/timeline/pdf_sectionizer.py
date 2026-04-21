"""
pdf_sectionizer.py — Group extracted PDF pages into chapters.

Kaiser (and most EHR print-to-PDF) exports carry a stable page header:

    MM/DD/YYYY - <visit type> in <department> (continued)

Every page in an encounter repeats that header with the same date + visit type
and adds ``(continued)`` on pages 2..N. Administrative summary pages (problem
list, current medications, immunizations, documents) carry a different shape:

    Patient (continued)<Section Name> (continued)

This module walks ``[(page_num, text), ...]`` tuples in order and produces
``PdfChapter`` rows — one per encounter or summary section — so the LLM
extractor can keep the context for an entire clinical day together rather
than slicing a note across arbitrary 5-page batches.

Pure Python. No LLM calls. No DB. ~0.5 ms per page.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visit type normalization
# ---------------------------------------------------------------------------
# Collapses Kaiser visit-type strings to a compact set of kinds we use
# throughout the graph (see ``ehr.patient_timeline.event_type`` taxonomy).
_VISIT_TYPE_KIND_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"Orders?\s+Only|Laboratory\s+Order", re.I), "lab_order"),
    (re.compile(r"Appointment\s+in\s+Laboratory|Lab\s+Service", re.I), "lab"),
    (re.compile(r"Laboratory", re.I), "lab"),
    (re.compile(r"Imaging|Radiology|CT\s+Scan|MRI|X-?Ray|Ultrasound|Fluoroscopy", re.I), "imaging"),
    (re.compile(r"Pulmonary\s+Function", re.I), "pulmonary_function"),
    (re.compile(r"Surgical\s+Pathology|Pathology", re.I), "pathology"),
    (re.compile(r"Admin\w*\s+Forms|Administrative|SCAN", re.I), "admin"),
    (re.compile(r"Telephone\s+(?:Visit|Encounter|in)|Tel\s+Enc", re.I), "telephone"),
    (re.compile(r"Secure\s+Message|Patient\s+Message|Portal\s+Message|Message", re.I), "message"),
    (re.compile(r"Immunization|Vaccin", re.I), "immunization"),
    (re.compile(r"Allied\s+Health|Nurse\s+Visit|Nursing\s+Encounter", re.I), "nursing"),
    (re.compile(r"Hospital|Inpatient|Admission|Discharge|Emergency|ER\s+Visit|Urgent\s+Care", re.I), "hospital"),
    (re.compile(r"Office\s+Visit|Clinic\s+Visit|Outpatient|Follow[- ]?up", re.I), "office_visit"),
    (re.compile(r"Encounter", re.I), "encounter"),
]


def normalize_visit_type(raw: str) -> str:
    """Map a Kaiser visit-type string to a compact lowercase kind."""
    if not raw:
        return "encounter"
    for rx, kind in _VISIT_TYPE_KIND_RULES:
        if rx.search(raw):
            return kind
    return "encounter"


# ---------------------------------------------------------------------------
# Header classification
# ---------------------------------------------------------------------------
# Kaiser page chrome: "Release of Medical Information...MRN:...DOB:...Sex:...".
# Printed on every page before the content band. We strip it (up to two hits —
# some pages repeat it) so our header regexes can anchor to real page text.
_CHROME_RX = re.compile(
    r"\s*Release of Medical Information[^\n]{10,300}?"
    r"(?:MRN[:\s][^\n]{3,60}?)?"
    r"(?:DOB[:\s][^\n]{3,40}?)?"
    r"(?:Sex[:\s](?:male|female|unknown|other|M|F)[^\n]{0,60}?)?"
    r"(?=\d{1,2}/\d{1,2}/\d{2,4}|Patient\s*\(continued\)|[A-Z])",
    re.I,
)

# Encounter header: "MM/DD/YYYY - <visit type in department>[(continued)]"
# The visit-type is everything between the separator and the first '(' or
# newline, greedy up to 120 chars. Kaiser always terminates the visit-type
# phrase either with "(continued)" (continuation pages) or with a capitalized
# section marker like "Reason for Visit" / "Messages" that normalize_visit_type
# tolerates (it looks for substrings, not whole-string matches).
_ENC_HEADER_RX = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*"
    r"([A-Za-z][^(\n]{3,140})"
    r"(?:\s*(\(continued\)))?",
)

# Summary header: "Patient (continued)<Section Name> (continued)" — section may
# contain `:`, `—`, `-`, `&`, `/`, and common punctuation (e.g. `Documents —
# Patient Level:`). Also plain "Problem List (continued)" on the first such page.
_SUM_HEADER_RX = re.compile(
    r"(?:Patient\s*\(continued\)\s*)?"
    r"([A-Z][A-Za-z0-9 &/\-\u2014:]{2,60}?)"
    r"\s*\(continued\)",
    re.I,
)


@dataclass
class PageClassification:
    """Classification of a single PDF page's header."""

    kind: str  # 'encounter' | 'summary' | 'other' | 'ocr_pending'
    encounter_date: Optional[str] = None  # 'YYYY-MM-DD'
    encounter_type: Optional[str] = None  # normalized (see normalize_visit_type)
    encounter_type_raw: Optional[str] = None  # "Appointment in Laboratory Service Center"
    section_header: Optional[str] = None  # summary section name, normalized title-case
    is_continuation: bool = False


def _parse_mdy(raw: str) -> Optional[str]:
    """Parse 'M/D/YY' or 'MM/DD/YYYY' → 'YYYY-MM-DD'. None on failure."""
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            d = datetime.strptime(raw, fmt).date()
            if d.year < 1950:
                d = d.replace(year=d.year + 100)
            return d.isoformat()
        except ValueError:
            continue
    return None


def classify_page(text: str) -> PageClassification:
    """Classify one extracted page's header. Pure function; ~10 µs per call."""
    if not text or not text.strip():
        return PageClassification(kind="ocr_pending")

    head = text.strip()[:800]
    # Strip Kaiser chrome so the encounter header is close to the start
    cleaned = _CHROME_RX.sub("", head, count=2).lstrip()
    probe = cleaned[:500]

    # 1) Encounter header
    m = _ENC_HEADER_RX.match(probe)
    if m:
        date_iso = _parse_mdy(m.group(1))
        if date_iso:
            raw_type = m.group(2).strip()
            return PageClassification(
                kind="encounter",
                encounter_date=date_iso,
                encounter_type=normalize_visit_type(raw_type),
                encounter_type_raw=raw_type[:120],
                is_continuation=bool(m.group(3)),
            )

    # 2) Summary header
    m = _SUM_HEADER_RX.match(probe)
    if m:
        return PageClassification(
            kind="summary",
            section_header=m.group(1).strip().title(),
            is_continuation=True,  # (continued) marker is required by the regex
        )

    # 3) Fallback: encounter header anywhere in the first 400 chars of cleaned text
    m = _ENC_HEADER_RX.search(probe[:400])
    if m:
        date_iso = _parse_mdy(m.group(1))
        if date_iso:
            raw_type = m.group(2).strip()
            return PageClassification(
                kind="encounter",
                encounter_date=date_iso,
                encounter_type=normalize_visit_type(raw_type),
                encounter_type_raw=raw_type[:120],
                is_continuation=True,
            )

    return PageClassification(kind="other")


# ---------------------------------------------------------------------------
# Chapter assembly
# ---------------------------------------------------------------------------
@dataclass
class PdfChapter:
    """A contiguous run of PDF pages that share a clinical context."""

    chapter_id: str
    kind: str  # 'encounter' | 'summary' | 'cover' | 'ocr_pending'
    pages: List[int] = field(default_factory=list)
    page_texts: List[Tuple[int, str]] = field(default_factory=list)  # (page_num, text)
    encounter_date: Optional[str] = None
    encounter_type: Optional[str] = None
    encounter_type_raw: Optional[str] = None
    section_header: Optional[str] = None
    ocr_pending_pages: List[int] = field(default_factory=list)

    @property
    def char_len(self) -> int:
        return sum(len(t) for _, t in self.page_texts)

    @property
    def est_tokens(self) -> int:
        # 4 chars/token Kaiser PDFs are slightly denser than English prose; this is
        # conservative enough for batch packing.
        return max(0, self.char_len // 4)

    @property
    def label(self) -> str:
        if self.kind == "encounter":
            t = (self.encounter_type or "encounter").replace("_", " ")
            return f"{self.encounter_date} · {t}"
        if self.kind == "summary":
            return f"Summary · {self.section_header}" if self.section_header else "Summary"
        if self.kind == "ocr_pending":
            return f"OCR queue · {len(self.ocr_pending_pages)} page(s)"
        return "Cover / preamble"

    def to_dict(self) -> Dict[str, object]:
        """Serializable view used for SSE streaming and meta persistence."""
        return {
            "chapter_id": self.chapter_id,
            "kind": self.kind,
            "label": self.label,
            "pages": list(self.pages),
            "page_count": len(self.pages),
            "char_len": self.char_len,
            "est_tokens": self.est_tokens,
            "encounter_date": self.encounter_date,
            "encounter_type": self.encounter_type,
            "encounter_type_raw": self.encounter_type_raw,
            "section_header": self.section_header,
            "ocr_pending_pages": list(self.ocr_pending_pages),
        }


def _slug(text: str) -> str:
    """Make a stable, URL-safe slug for chapter_id construction."""
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:40] or "unk"


def _chapter_id(
    kind: str,
    first_page: int,
    *,
    encounter_date: Optional[str] = None,
    encounter_type: Optional[str] = None,
    section_header: Optional[str] = None,
) -> str:
    """Deterministic chapter id — reused by graph enrichment + timeline meta rows."""
    if kind == "encounter":
        return f"enc_{encounter_date or '0000-00-00'}_{_slug(encounter_type or 'unk')}_p{first_page:04d}"
    if kind == "summary":
        return f"sum_{_slug(section_header or 'unk')}_p{first_page:04d}"
    if kind == "ocr_pending":
        return f"ocr_p{first_page:04d}"
    return f"cover_p{first_page:04d}"


def _same_encounter(prev: PdfChapter, cls: PageClassification) -> bool:
    """Does this page belong to the previous encounter chapter?"""
    return (
        prev.kind == "encounter"
        and prev.encounter_date == cls.encounter_date
        and prev.encounter_type == cls.encounter_type
    )


def _same_summary(prev: PdfChapter, cls: PageClassification) -> bool:
    return (
        prev.kind == "summary"
        and (prev.section_header or "").lower() == (cls.section_header or "").lower()
    )


def sectionize_pages(
    pages: List[Tuple[int, str]],
    *,
    total_pages: Optional[int] = None,
) -> List[PdfChapter]:
    """Walk the page list and emit chapter rows.

    Rules:
    - Empty / OCR-pending pages join the current chapter but their page number
      is recorded on ``ocr_pending_pages`` so ``ocr_forge`` can queue them
      after the text-only PTV build completes.
    - Pages whose header we couldn't classify ('other') are appended to the
      current chapter (Kaiser prints blank continuation pages between real
      ones). If there's no current chapter yet, they start a 'cover' chapter.
    - New encounter page → flush and start new encounter chapter.
    - Summary section → flush if previous wasn't the same summary section.
    """
    chapters: List[PdfChapter] = []
    current: Optional[PdfChapter] = None

    def _flush() -> None:
        nonlocal current
        if current and (current.pages or current.ocr_pending_pages):
            chapters.append(current)
        current = None

    def _start(kind: str, first_page: int, cls: Optional[PageClassification]) -> PdfChapter:
        cls = cls or PageClassification(kind=kind)
        cid = _chapter_id(
            kind,
            first_page,
            encounter_date=cls.encounter_date,
            encounter_type=cls.encounter_type,
            section_header=cls.section_header,
        )
        return PdfChapter(
            chapter_id=cid,
            kind=kind,
            encounter_date=cls.encounter_date,
            encounter_type=cls.encounter_type,
            encounter_type_raw=cls.encounter_type_raw,
            section_header=cls.section_header,
        )

    for page_num, text in pages:
        cls = classify_page(text)

        # OCR-pending pages: no useful text. Carry along with current chapter if
        # one exists; otherwise open a dedicated ocr_pending chapter so the
        # caller can track them separately.
        if cls.kind == "ocr_pending":
            if current is None:
                current = _start("ocr_pending", page_num, cls)
            current.ocr_pending_pages.append(page_num)
            current.pages.append(page_num)
            continue

        if cls.kind == "encounter":
            if current is None or not _same_encounter(current, cls):
                _flush()
                current = _start("encounter", page_num, cls)
        elif cls.kind == "summary":
            if current is None or not _same_summary(current, cls):
                _flush()
                current = _start("summary", page_num, cls)
        else:  # 'other' — bleed / cover / misc
            if current is None:
                current = _start("cover", page_num, cls)
            # don't flush; just append

        current.pages.append(page_num)
        if text and text.strip():
            current.page_texts.append((page_num, text))

    _flush()
    return chapters


# ---------------------------------------------------------------------------
# Chapter-aware batch packer
# ---------------------------------------------------------------------------
@dataclass
class ChapterBatch:
    """A group of chapter slices to send to the LLM in one call."""

    batch_index: int
    pages: List[Tuple[int, str]]  # flattened pages for this LLM call
    chapter_ids: List[str]        # chapters represented in this batch
    primary_chapter_id: str       # chapter label shown in the UI
    split_note: Optional[str] = None  # populated when the batch is part of a split chapter

    @property
    def char_len(self) -> int:
        return sum(len(t) for _, t in self.pages)


def pack_chapters_into_batches(
    chapters: List[PdfChapter],
    *,
    max_chars: int,
    max_pages_per_batch: Optional[int] = None,
    per_page_overhead_chars: int = 64,
) -> List[ChapterBatch]:
    """Greedy pack: keep chapters intact where possible; split long ones cleanly.

    - Pack consecutive chapters together until the next chapter would overflow
      ``max_chars`` (or ``max_pages_per_batch`` if set).
    - A chapter whose own size exceeds the per-batch cap is split into
      contiguous page runs, each tagged with the chapter header so the LLM
      knows it's looking at one slice of the same encounter.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    batches: List[ChapterBatch] = []
    buf_pages: List[Tuple[int, str]] = []
    buf_chapter_ids: List[str] = []
    buf_primary: Optional[str] = None
    buf_size = 0

    def _flush_buf() -> None:
        nonlocal buf_pages, buf_chapter_ids, buf_primary, buf_size
        if not buf_pages:
            return
        batches.append(
            ChapterBatch(
                batch_index=len(batches),
                pages=buf_pages,
                chapter_ids=list(dict.fromkeys(buf_chapter_ids)),
                primary_chapter_id=buf_primary or buf_chapter_ids[0],
            )
        )
        buf_pages = []
        buf_chapter_ids = []
        buf_primary = None
        buf_size = 0

    for chapter in chapters:
        # Ignore pure OCR-pending chapters here — they have no text for the LLM.
        if not chapter.page_texts:
            continue

        chapter_size = chapter.char_len + per_page_overhead_chars * max(len(chapter.page_texts), 1)

        # Chapter fits in a single batch AND the running buffer has room → append.
        if (
            chapter_size <= max_chars
            and buf_size + chapter_size <= max_chars
            and (max_pages_per_batch is None or len(buf_pages) + len(chapter.page_texts) <= max_pages_per_batch)
        ):
            buf_pages.extend(chapter.page_texts)
            buf_chapter_ids.append(chapter.chapter_id)
            if buf_primary is None:
                buf_primary = chapter.chapter_id
            buf_size += chapter_size
            continue

        # Otherwise flush the current buffer before handling this chapter.
        _flush_buf()

        # Chapter fits alone → single-chapter batch.
        if chapter_size <= max_chars and (
            max_pages_per_batch is None or len(chapter.page_texts) <= max_pages_per_batch
        ):
            buf_pages = list(chapter.page_texts)
            buf_chapter_ids = [chapter.chapter_id]
            buf_primary = chapter.chapter_id
            buf_size = chapter_size
            continue

        # Oversized chapter → split into page runs. Each run gets a split_note
        # so the LLM preamble can say "you are seeing part N of encounter X".
        sub_index = 0
        run_pages: List[Tuple[int, str]] = []
        run_size = 0
        total_subs_guess = max(
            1,
            -(-chapter_size // max_chars),  # ceil div
        )
        for pn, txt in chapter.page_texts:
            need = len(txt) + per_page_overhead_chars
            if need > max_chars:
                logger.warning(
                    "pdf_sectionizer: page %d (chapter %s) exceeds per-batch cap (%d chars); truncating",
                    pn,
                    chapter.chapter_id,
                    max_chars,
                )
                txt = txt[: max(0, max_chars - per_page_overhead_chars)]
                need = len(txt) + per_page_overhead_chars

            pages_overflow = max_pages_per_batch is not None and len(run_pages) >= max_pages_per_batch
            if run_pages and (run_size + need > max_chars or pages_overflow):
                sub_index += 1
                batches.append(
                    ChapterBatch(
                        batch_index=len(batches),
                        pages=run_pages,
                        chapter_ids=[chapter.chapter_id],
                        primary_chapter_id=chapter.chapter_id,
                        split_note=(
                            f"part {sub_index} of long {chapter.kind} chapter "
                            f"{chapter.chapter_id}; est. {total_subs_guess} parts total"
                        ),
                    )
                )
                run_pages = []
                run_size = 0

            run_pages.append((pn, txt))
            run_size += need

        if run_pages:
            sub_index += 1
            batches.append(
                ChapterBatch(
                    batch_index=len(batches),
                    pages=run_pages,
                    chapter_ids=[chapter.chapter_id],
                    primary_chapter_id=chapter.chapter_id,
                    split_note=(
                        f"part {sub_index} of long {chapter.kind} chapter "
                        f"{chapter.chapter_id}; est. {total_subs_guess} parts total"
                    ) if total_subs_guess > 1 else None,
                )
            )

    _flush_buf()
    return batches


# ---------------------------------------------------------------------------
# ETA heuristics
# ---------------------------------------------------------------------------
def estimate_batch_seconds(
    batch_pages: int,
    batch_chars: int,
    *,
    model: str,
) -> float:
    """Rough per-batch duration estimate shown on the streaming UI.

    Tuned from observed run-times on the Norman Roberts record:
      - ``eoh-llama3.1:8b`` @ ~32k context: 14 s per page + 4 s per 10k chars of input.
      - ``gpt-4.1``:                       3 s per 25k chars of input.
    """
    m = (model or "").lower()
    if m.startswith("gpt-4.1") and not m.startswith("gpt-4.1-mini"):
        return max(8.0, 3.0 + batch_chars / 25_000.0)
    if m.startswith("gpt-4.1-mini") or "openai" in m or "gpt-" in m:
        return max(5.0, 2.5 + batch_chars / 40_000.0)
    # eoh-llama 8B / other local Ollama models
    return max(12.0, 14.0 * max(1, batch_pages) + batch_chars / 10_000.0)


# ---------------------------------------------------------------------------
# Utility: a stable artifact ID for saving a sectionized run
# ---------------------------------------------------------------------------
def artifact_signature(pages: List[Tuple[int, str]]) -> str:
    """Short deterministic ID for a page list (first 12 chars of a SHA-256)."""
    h = hashlib.sha256()
    for pn, txt in pages:
        h.update(f"{pn}\x1f{len(txt)}\x1f".encode())
    return h.hexdigest()[:12]
