"""
graph_finalize.py — deterministic post-processing passes for the
Patient Timeline Vision graph.

These passes run AFTER extraction + existing reduced-graph connascence
(see ``timeline_summarizer._infer_reduced_graph_connascence``) and
BEFORE final persistence.  Everything here is pure-Python, no LLM,
mechanical and testable.

Entry point:
    >>> stats = finalize_graph(vision, chapters=chapters, pages=pages_text)

``stats`` is a dict of per-pass counters suitable for logging / SSE.

Passes, in order (order matters — later passes consume earlier ones'
annotations):

    1.  _assign_canonical_ids        -> annotations.canonical_id
    2.  _backfill_timestamps         -> timestamp from chapter/page fallback
    3.  _infer_status_flags          -> annotations.status_flags
    4.  _build_entities_map          -> vision.metadata["entities"]
    5.  _seed_clinical_arcs          -> vision.arcs + annotations.arc_ids
    6.  _infer_causal_edges          -> connascence["caused_by" | "in_workup_for"]
    7.  _collapse_admin_chapters     -> suppresses page-admin events
    8.  _harvest_pros                -> adds event_type="pro" events
    9.  _extract_patient_metadata    -> vision.metadata["patient"]
    10. _compute_salience            -> annotations.salience
    11. _build_event_cards           -> annotations.card
    12. _build_index_block           -> vision.metadata["index"]
    13. _build_code_index             -> vision.metadata["code_index"]

All writes are idempotent — calling ``finalize_graph`` twice on the
same graph is a no-op (counts will be zero on the second call).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from server.eoh.patient_timeline_vision import (
    ClinicalArc,
    PatientTimelineVision,
    TimelineEventVision,
)
from server.utils.parse_date import parse_clinical_date

logger = logging.getLogger(__name__)


# =============================================================================
# Public entry point
# =============================================================================

def finalize_graph(
    vision: PatientTimelineVision,
    *,
    chapters: Optional[List[Any]] = None,
    pages_text: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """Run all deterministic finalizer passes on ``vision`` in-place.

    Parameters
    ----------
    vision :
        The graph to enrich.  Mutated in place.
    chapters :
        Optional list of ``PdfChapter`` objects (or any object exposing
        ``chapter_id``, ``kind``, ``encounter_date``, ``section_header``,
        ``pages``).  Used by arc seeding + admin collapse.  Safe to omit.
    pages_text :
        Optional ``page_num -> raw_text`` map.  Used for patient metadata
        and PRO harvesting when available.

    Returns
    -------
    stats :
        Dict of per-pass counters / structures suitable for logging.
    """
    stats: Dict[str, Any] = {}

    stats["canonical_ids"] = _assign_canonical_ids(vision)
    stats["timestamp_backfill"] = _backfill_timestamps(vision, chapters or [])
    stats["status_flags"] = _infer_status_flags(vision)
    stats["entities"] = _build_entities_map(vision)
    stats["arcs"] = _seed_clinical_arcs(vision)
    stats["causal_edges"] = _infer_causal_edges(vision, chapters or [])
    stats["admin_collapse"] = _collapse_admin_chapters(vision, chapters or [])
    stats["pros"] = _harvest_pros(vision, pages_text or {})
    stats["patient"] = _extract_patient_metadata(vision, pages_text or {})
    stats["salience"] = _compute_salience(vision)
    stats["cards"] = _build_event_cards(vision)
    stats["index"] = _build_index_block(vision)
    stats["code_index"] = _build_code_index(vision)

    return stats


# =============================================================================
# 1. Canonical (content-hashed) event IDs
# =============================================================================

_WS_RX = re.compile(r"\s+")
_NONALNUM_RX = re.compile(r"[^\w\s-]")


def _normalize_for_hash(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = (text or "").strip().lower()
    text = _NONALNUM_RX.sub(" ", text)
    return _WS_RX.sub(" ", text).strip()


def _canonical_key_for_event(ev: TimelineEventVision) -> str:
    """Content-hash fingerprint across (type, normalized preview, chapter, day)."""
    ann = ev.annotations or {}
    ts = (ev.timestamp or "unknown").strip()
    day = ts.split("T")[0][:10] if ts else "unknown"
    payload = json.dumps(
        {
            "t": (ev.event_type or "").lower(),
            "p": _normalize_for_hash(ev.preview)[:200],
            "c": str(ann.get("chapter_id") or ""),
            "d": day,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return "ev_" + hashlib.sha1(payload).hexdigest()[:16]


def _assign_canonical_ids(vision: PatientTimelineVision) -> int:
    """Stamp ``annotations.canonical_id`` on every event.

    Event keys (``event_id``) stay unchanged for backward compatibility —
    the canonical ID is an additive, content-stable fingerprint for
    registry diffing and cross-ingest deduplication.
    """
    stamped = 0
    for ev in vision.events.values():
        if ev.annotations.get("canonical_id"):
            continue
        ev.annotations["canonical_id"] = _canonical_key_for_event(ev)
        stamped += 1
    return stamped


# =============================================================================
# 2. Best-effort timestamp backfill
# =============================================================================

_UNKNOWN_TS = {"", "unknown", "n/a", "na", "none"}


def _is_known_ts(ts: str) -> bool:
    return bool(ts) and ts.strip().lower() not in _UNKNOWN_TS


def _backfill_timestamps(
    vision: PatientTimelineVision,
    chapters: List[Any],
) -> Dict[str, int]:
    """For every event whose ``timestamp`` is still 'unknown', inherit
    in this priority order:

        (a) chapter.encounter_date when the chapter is an encounter
        (b) chapter.page_date when the chapter carries one
        (c) any date already recorded in ``annotations.encounter_date``

    Records the inherited source in ``annotations.timestamp_source``.
    """
    chapter_ts: Dict[str, str] = {}
    for ch in chapters:
        cid = getattr(ch, "chapter_id", None)
        if not cid:
            continue
        enc = getattr(ch, "encounter_date", None)
        if enc and re.match(r"^\d{4}-\d{2}-\d{2}$", str(enc)):
            chapter_ts[cid] = str(enc)

    counts = {"from_chapter": 0, "from_encounter_ann": 0}
    for ev in vision.events.values():
        if _is_known_ts(ev.timestamp):
            continue
        cid = (ev.annotations or {}).get("chapter_id")
        if cid and cid in chapter_ts:
            ev.timestamp = chapter_ts[cid]
            ev.annotations.setdefault("timestamp_source", "chapter_encounter_date")
            counts["from_chapter"] += 1
            continue
        enc = (ev.annotations or {}).get("encounter_date")
        if enc and re.match(r"^\d{4}-\d{2}-\d{2}$", str(enc)):
            ev.timestamp = str(enc)
            ev.annotations.setdefault("timestamp_source", "annotations_encounter_date")
            counts["from_encounter_ann"] += 1
    return counts


# =============================================================================
# 3. Status flags
# =============================================================================

_STATUS_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("resolved", re.compile(r"\b(?:resolved|cured|in remission|cleared|healed)\b", re.I)),
    ("chronic", re.compile(r"\bchronic(?:\s*:\s*yes)?\b|\(chronic\)", re.I)),
    ("stopped", re.compile(r"\b(?:discontinued|stopped|d/c(?:'d)?|held|cancell?ed|expired)\b|\(discontinued\)", re.I)),
    ("continued", re.compile(r"\b(?:continue(?:d)?|ongoing|stable|continue\s+therapy)\b", re.I)),
    ("acute", re.compile(r"\bacute(?:ly)?\b", re.I)),
    ("flare", re.compile(r"\b(?:flare(?:-?up)?|exacerbation)\b", re.I)),
    ("worsening", re.compile(r"\b(?:worsen(?:ing|ed)?|deteriorat(?:ing|ed)?|progress(?:ed|ing))\b", re.I)),
    ("improving", re.compile(r"\b(?:improv(?:ed|ing)|better|stable)\b", re.I)),
]


def _infer_status_flags(vision: PatientTimelineVision) -> int:
    """Populate ``annotations.status_flags = [...]`` from preview text.

    Status flags are additive tags, not a single state — a medication can
    be {'continued','ongoing'} and a diagnosis can be {'chronic','flare'}.
    Downstream registry code treats them as booleans on the FHIR resource.
    """
    stamped = 0
    for ev in vision.events.values():
        text = (ev.preview or "")
        if not text:
            continue
        flags: List[str] = []
        for label, rx in _STATUS_PATTERNS:
            if rx.search(text):
                flags.append(label)
        # Special case: "Chronic: No" → explicit 'non_chronic' tag so a
        # downstream query can exclude it without string-matching.
        if re.search(r"Chronic\s*:\s*No\b", text, re.I):
            flags = [f for f in flags if f != "chronic"] + ["non_chronic"]
        if flags:
            existing = list(ev.annotations.get("status_flags") or [])
            merged = list(dict.fromkeys(existing + flags))  # preserve order, dedupe
            if merged != existing:
                ev.annotations["status_flags"] = merged
                stamped += 1
    return stamped


# =============================================================================
# 4. Entities map (drug / icd / procedure / lab / vaccine)
# =============================================================================

_ICD_IN_PREVIEW_RX = re.compile(r"\[([A-Z]\d{2}(?:\.[0-9A-Za-z]+)?)\]")
_PROC_NAMES_RX = re.compile(
    r"\b(colonoscopy|cholecystectomy|endoscopy|biopsy|"
    r"appendectomy|cystoscopy|mri|ct\s+scan|echocardiogram|"
    r"catheterization|dialysis|bronchoscopy|pacemaker|"
    r"thoracentesis|paracentesis|lumbar\s+puncture)\b",
    re.I,
)
_LAB_NAMES_RX = re.compile(
    r"\b(hba1c|hemoglobin|hgb|wbc|creatinine|sodium|potassium|"
    r"glucose|albumin|bilirubin|alt|ast|ldh|ck|troponin|ferritin|"
    r"psa|tsh|inr|esr|crp|ana|anca)\b",
    re.I,
)


def _canonical_entity_key(kind: str, name: str) -> str:
    """Return an entity key like ``drug:methotrexate`` or ``icd:I48.0``."""
    norm = _normalize_for_hash(name).replace(" ", "_")
    return f"{kind}:{norm}" if norm else ""


def _drug_display(raw: str) -> str:
    return " ".join(w.capitalize() if w.isalpha() else w for w in raw.split())


def _build_entities_map(vision: PatientTimelineVision) -> Dict[str, int]:
    """Compute the canonical entity registry.

    Stored at ``vision.metadata["entities"]`` as::

        { "drug:methotrexate": {
              "kind": "drug", "key": "...", "display": "Methotrexate",
              "event_ids": [...], "first_seen": "YYYY-MM-DD",
              "last_seen": "YYYY-MM-DD", "aliases": [...],
              "codes": [], } ,
          "icd:I48.0": {...},
          ... }

    Also stamps ``annotations.entity_keys`` (list) on each contributing event
    so agent traversal can hop event → entity → other events in O(1).
    """
    entities: Dict[str, Dict[str, Any]] = {}
    event_keys: Dict[str, List[str]] = defaultdict(list)

    def _add(eid: str, kind: str, display: str, aliases: Optional[List[str]] = None) -> None:
        key = _canonical_entity_key(kind, display)
        if not key:
            return
        ent = entities.setdefault(
            key,
            {
                "kind": kind,
                "key": key,
                "display": _drug_display(display) if kind == "drug" else display,
                "event_ids": [],
                "aliases": [],
                "codes": [],  # extension point for RxNorm/LOINC/SNOMED
                "first_seen": None,
                "last_seen": None,
            },
        )
        if eid not in ent["event_ids"]:
            ent["event_ids"].append(eid)
        for a in aliases or []:
            if a and a not in ent["aliases"]:
                ent["aliases"].append(a)
        event_keys[eid].append(key)

    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        preview = ev.preview or ""

        # drugs
        drug = ann.get("drug_name")
        if drug and isinstance(drug, str) and drug.strip():
            _add(eid, "drug", drug.strip())

        # ICDs — from annotation or preview fallback
        icd = ann.get("icd_code")
        if not icd:
            m = _ICD_IN_PREVIEW_RX.search(preview)
            if m:
                icd = m.group(1)
        if icd:
            _add(eid, "icd", str(icd).upper())

        # procedures — any match in preview for high-value procedures
        for pm in _PROC_NAMES_RX.finditer(preview):
            _add(eid, "procedure", pm.group(1).lower())

        # labs — for lab-typed events only
        if ev.event_type == "lab":
            for lm in _LAB_NAMES_RX.finditer(preview):
                _add(eid, "lab", lm.group(1).lower())

    # Derive first_seen / last_seen per entity from contributing events.
    for key, ent in entities.items():
        dated: List[datetime] = []
        for eid in ent["event_ids"]:
            ev = vision.events.get(eid)
            if not ev:
                continue
            dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
            if dt:
                dated.append(dt)
        if dated:
            ent["first_seen"] = min(dated).strftime("%Y-%m-%d")
            ent["last_seen"] = max(dated).strftime("%Y-%m-%d")

    # Stamp back onto events for fast traversal.
    for eid, keys in event_keys.items():
        ev = vision.events.get(eid)
        if not ev:
            continue
        uniq = list(dict.fromkeys(keys))
        ev.annotations["entity_keys"] = uniq

    vision.metadata["entities"] = entities
    return {"entity_count": len(entities), "events_tagged": len(event_keys)}


# =============================================================================
# 5. ClinicalArc seeding
# =============================================================================

# ICD "family" = the letter + first two digits (e.g. "I48" from "I48.0").
_ICD_FAMILY_RX = re.compile(r"^([A-Z]\d{2})")

# Pretty labels for common ICD families.  Used to name arcs.
_ICD_FAMILY_LABELS: Dict[str, str] = {
    "I48": "Atrial fibrillation / flutter",
    "I10": "Essential hypertension",
    "E11": "Type 2 diabetes mellitus",
    "E78": "Lipid disorders",
    "J45": "Asthma",
    "J44": "Chronic obstructive pulmonary disease",
    "K21": "Gastro-esophageal reflux",
    "K80": "Cholelithiasis / cholecystitis",
    "K81": "Acute cholecystitis",
    "M54": "Dorsalgia / back pain",
    "M48": "Spondylosis",
    "M51": "Intervertebral disc disorders",
    "N18": "Chronic kidney disease",
    "D64": "Anemia",
    "G70": "Myasthenia gravis",
    "Z71": "Counselling",
    "R07": "Chest pain",
    "L40": "Psoriasis",
}


def _icd_family(code: str) -> Optional[str]:
    m = _ICD_FAMILY_RX.match(code.strip().upper())
    return m.group(1) if m else None


def _date_range(event_ids: List[str], vision: PatientTimelineVision) -> Tuple[str, str]:
    dates: List[datetime] = []
    for eid in event_ids:
        ev = vision.events.get(eid)
        if not ev or not ev.timestamp:
            continue
        dt = parse_clinical_date(ev.timestamp)
        if dt:
            dates.append(dt)
    if not dates:
        return ("", "")
    return (min(dates).strftime("%Y-%m-%d"), max(dates).strftime("%Y-%m-%d"))


def _seed_clinical_arcs(vision: PatientTimelineVision) -> Dict[str, int]:
    """Seed deterministic ClinicalArcs grouped by:
      - ICD family           (arc_icd_<family>)
      - procedure            (arc_proc_<slug>)
      - encounter cluster    (arc_encounter_<date>_<type>)

    Events are tagged with ``annotations.arc_ids`` (list) — a single event
    can belong to multiple arcs (e.g. a procedure may appear in both its
    procedure arc and the encounter arc where it was performed).

    Note
    ----
    Drug "arcs" were removed in favor of a richer flat lookup at
    ``metadata.code_index.drugs`` / ``metadata.code_index.rxnorm`` (see
    :func:`_build_code_index`).  A medication name in isolation isn't an
    arc — it's a code with a chronological series of administrations, and
    dose / route are first-class there.
    """
    arcs: Dict[str, List[str]] = defaultdict(list)
    arc_names: Dict[str, str] = {}

    entities = vision.metadata.get("entities") or {}

    # 1. ICD-family arcs — collapse every ICD entity under its family.
    family_members: Dict[str, List[str]] = defaultdict(list)
    for key, ent in entities.items():
        if not key.startswith("icd:"):
            continue
        code = ent["key"].split(":", 1)[1]
        fam = _icd_family(code)
        if not fam:
            continue
        family_members[fam].extend(ent["event_ids"])
    for fam, eids in family_members.items():
        if len(eids) < 2:
            continue
        aid = f"arc_icd_{fam}"
        arcs[aid].extend(eids)
        arc_names[aid] = _ICD_FAMILY_LABELS.get(fam, f"ICD family {fam}")

    # 2. (removed) Drug arcs — superseded by metadata.code_index.drugs.

    # 3. Procedure arcs.
    for key, ent in entities.items():
        if not key.startswith("procedure:"):
            continue
        if len(ent["event_ids"]) < 2:
            continue
        aid = "arc_" + key.replace(":", "_")
        arcs[aid].extend(ent["event_ids"])
        arc_names[aid] = f"Procedure: {ent['display']}"

    # 4. Encounter-cluster arcs — one per distinct encounter_date × type.
    encounter_buckets: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        enc_date = ann.get("encounter_date")
        enc_type = ann.get("encounter_type") or "encounter"
        if not enc_date:
            continue
        encounter_buckets[(str(enc_date), str(enc_type))].append(eid)
    for (enc_date, enc_type), eids in encounter_buckets.items():
        if len(eids) < 2:
            continue
        slug = re.sub(r"[^a-z0-9_]+", "_", enc_type.lower()).strip("_") or "encounter"
        aid = f"arc_encounter_{enc_date}_{slug}"
        arcs[aid].extend(eids)
        arc_names[aid] = f"Encounter: {enc_date} · {enc_type.replace('_', ' ')}"

    # Build ClinicalArc objects, dedupe event lists, stamp arc_ids onto events.
    created = 0
    for aid, raw_eids in arcs.items():
        eids = list(dict.fromkeys(raw_eids))
        if aid in vision.arcs:
            continue
        start, end = _date_range(eids, vision)
        arc = ClinicalArc(
            arc_id=aid,
            name=arc_names.get(aid, aid),
            event_ids=eids,
            date_range=(start, end),
            summary="",
            status="seeded",
        )
        vision.arcs[aid] = arc
        created += 1

    for aid, arc in vision.arcs.items():
        for eid in arc.event_ids:
            ev = vision.events.get(eid)
            if not ev:
                continue
            existing = list(ev.annotations.get("arc_ids") or [])
            if aid not in existing:
                existing.append(aid)
                ev.annotations["arc_ids"] = existing

    return {
        "arcs_created": created,
        "arcs_total": len(vision.arcs),
    }


# =============================================================================
# 6. Causal edges (caused_by / in_workup_for)
# =============================================================================

def _infer_causal_edges(
    vision: PatientTimelineVision,
    chapters: List[Any],
) -> Dict[str, int]:
    """Within an encounter chapter whose problem list is dominated by a
    single ICD family, link that encounter's procedures/labs/imaging
    to the dominant diagnosis with ``caused_by`` or ``in_workup_for``.

    Heuristic, not semantic:
      - Gather all events per encounter chapter.
      - Find the diagnosis event whose ICD family covers the MOST
        other events in the chapter (tie-break on earliest timestamp).
      - For every non-diagnosis event in the chapter, add an edge
        ``kind=in_workup_for`` pointing to the dominant diagnosis.
      - Diagnoses in the same family point to the index dx with
        ``kind=caused_by`` (as siblings of a root condition).
    """
    if not chapters:
        return {"caused_by": 0, "in_workup_for": 0}

    chapters_by_id = {getattr(ch, "chapter_id", None): ch for ch in chapters}

    by_chapter: Dict[str, List[str]] = defaultdict(list)
    for eid, ev in vision.events.items():
        cid = (ev.annotations or {}).get("chapter_id")
        if cid:
            by_chapter[str(cid)].append(eid)

    counts = {"caused_by": 0, "in_workup_for": 0}

    for cid, eids in by_chapter.items():
        ch = chapters_by_id.get(cid)
        kind = getattr(ch, "kind", None) if ch else None
        if kind not in ("encounter", "summary"):
            continue
        if len(eids) < 3:
            continue

        # Find the dominant ICD family.
        family_counts: Counter[str] = Counter()
        index_by_family: Dict[str, str] = {}
        for eid in eids:
            ev = vision.events.get(eid)
            if not ev:
                continue
            icd = (ev.annotations or {}).get("icd_code")
            if not icd:
                m = _ICD_IN_PREVIEW_RX.search(ev.preview or "")
                if m:
                    icd = m.group(1)
            if not icd:
                continue
            fam = _icd_family(str(icd))
            if not fam:
                continue
            family_counts[fam] += 1
            # Prefer earliest-timestamped diagnosis as the "index" event.
            if ev.event_type == "diagnosis":
                cur = index_by_family.get(fam)
                if cur is None:
                    index_by_family[fam] = eid
                else:
                    cur_ev = vision.events.get(cur)
                    if (cur_ev and ev.timestamp and cur_ev.timestamp
                            and ev.timestamp < cur_ev.timestamp):
                        index_by_family[fam] = eid

        if not family_counts:
            continue
        dominant_fam, dom_count = family_counts.most_common(1)[0]
        if dom_count < 2:
            continue
        index_eid = index_by_family.get(dominant_fam)
        if not index_eid:
            continue

        for eid in eids:
            if eid == index_eid:
                continue
            ev = vision.events.get(eid)
            if not ev:
                continue
            if ev.event_type in ("procedure", "lab", "imaging", "symptom", "vital_signs"):
                vision.add_edge(
                    source_event_id=eid,
                    target_event_id=index_eid,
                    connascence_type="in_workup_for",
                    discovered_by="causal:chapter_dominant_dx",
                    metadata={"chapter_id": cid, "icd_family": dominant_fam},
                    strength=0.8,
                )
                counts["in_workup_for"] += 1
            elif ev.event_type == "diagnosis":
                # Another dx in the same family — link as sibling caused_by.
                icd = (ev.annotations or {}).get("icd_code") or ""
                fam = _icd_family(str(icd))
                if fam == dominant_fam and eid != index_eid:
                    vision.add_edge(
                        source_event_id=eid,
                        target_event_id=index_eid,
                        connascence_type="caused_by",
                        discovered_by="causal:same_family",
                        metadata={"chapter_id": cid, "icd_family": dominant_fam},
                        strength=0.6,
                    )
                    counts["caused_by"] += 1

    return counts


# =============================================================================
# 7. Chapter-level admin collapse
# =============================================================================

_ADMIN_HEADERS_RX = re.compile(
    r"(?:release|authorization|consent|demographic|registration|"
    r"billing|insurance|hipaa|power\s+of\s+attorney|cover|index|"
    r"table\s+of\s+contents)",
    re.I,
)


def _is_admin_chapter(ch: Any) -> bool:
    if getattr(ch, "kind", None) == "cover":
        return True
    header = getattr(ch, "section_header", None) or ""
    return bool(_ADMIN_HEADERS_RX.search(header))


def _collapse_admin_chapters(
    vision: PatientTimelineVision,
    chapters: List[Any],
) -> Dict[str, int]:
    """For chapters that are entirely boilerplate, replace all their
    ``administrative`` events with a single ``chapter_administrative``
    event.  The suppressed event IDs are kept in
    ``annotations.suppressed_events`` for auditability.

    Admin chapters are heuristically identified by:
      - chapter.kind == 'cover', or
      - section_header matching common boilerplate labels.
    """
    if not chapters:
        return {"admin_chapters_collapsed": 0, "events_suppressed": 0}

    collapsed = 0
    suppressed = 0

    admin_chapter_ids = {
        getattr(ch, "chapter_id", None): ch
        for ch in chapters
        if _is_admin_chapter(ch)
    }

    for cid, ch in admin_chapter_ids.items():
        if not cid:
            continue
        # Gather all events in this chapter.
        in_chapter = [
            (eid, ev) for eid, ev in vision.events.items()
            if (ev.annotations or {}).get("chapter_id") == cid
        ]
        if not in_chapter:
            continue
        admin_events = [
            (eid, ev) for eid, ev in in_chapter
            if ev.event_type in ("administrative", "clinical_note", "unknown")
        ]
        if len(admin_events) < 2:
            continue  # not worth collapsing

        suppressed_ids = [eid for eid, _ in admin_events]
        suppressed += len(suppressed_ids)

        # Build one summary event.
        first_ev = in_chapter[0][1]
        pages = sorted({
            (ev.annotations or {}).get("pdf_page")
            for _, ev in in_chapter
            if isinstance((ev.annotations or {}).get("pdf_page"), int)
        })
        header = getattr(ch, "section_header", None) or getattr(ch, "chapter_id", "Administrative")
        summary_eid = f"chap_admin_{cid}"
        vision.add_event(
            event_id=summary_eid,
            event_type="chapter_administrative",
            timestamp=first_ev.timestamp,
            preview=f"Administrative chapter: {header} (pages {pages[0] if pages else '?'}-{pages[-1] if pages else '?'}, {len(admin_events)} items collapsed)",
            discovered_by="graph_finalize:admin_collapse",
            annotations={
                "chapter_id": cid,
                "chapter_kind": getattr(ch, "kind", None),
                "section_header": header,
                "suppressed_events": suppressed_ids,
                "pages": list(pages),
            },
        )
        # Demote the individual admin events to status="suppressed" so a
        # downstream consumer can filter them but the audit trail stays.
        for eid, ev in admin_events:
            ev.status = "suppressed"
            ev.annotations["collapsed_into"] = summary_eid

        collapsed += 1

    return {"admin_chapters_collapsed": collapsed, "events_suppressed": suppressed}


# =============================================================================
# 8. PRO harvesting
# =============================================================================

# Disease-activity / PRO instruments commonly reported in rheumatology &
# longitudinal care notes.  We capture any numeric value following the
# instrument name within 20 characters.
_PRO_INSTRUMENTS: List[Tuple[str, re.Pattern, str]] = [
    ("HAQ",         re.compile(r"\bHAQ(?:-DI)?\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), ""),
    ("RAPID3",      re.compile(r"\bRAPID-?3\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), ""),
    ("CDAI",        re.compile(r"\bCDAI\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), ""),
    ("DAS28",       re.compile(r"\bDAS[-\s]?28(?:[-\s]?(?:CRP|ESR))?\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), ""),
    ("SDAI",        re.compile(r"\bSDAI\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), ""),
    ("pain_VAS",    re.compile(r"\b(?:pain\s+(?:VAS|score)|VAS\s+pain)\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), "/10"),
    ("morning_stiffness_min", re.compile(r"\bmorning\s+stiffness\b[^0-9\n]{0,30}(\d+)\s*(?:min|minutes)", re.I), "minutes"),
    ("fatigue_VAS", re.compile(r"\bfatigue\s+(?:VAS|score)\b[^0-9\n]{0,20}(\d+(?:\.\d+)?)", re.I), "/10"),
]


def _harvest_pros(
    vision: PatientTimelineVision,
    pages_text: Dict[int, str],
) -> Dict[str, int]:
    """Scan raw page text (when available) AND event previews for PRO
    instrument readings.  Emit one ``event_type='pro'`` event per hit.

    If ``pages_text`` is empty, fall back to scanning ``ev.preview`` on
    existing events — we will still catch instruments the LLM dumped into
    preview summaries.
    """
    added = 0
    seen_keys: set = set()

    def _emit(instrument: str, value: float, units: str, page: Optional[int], cid: Optional[str]) -> None:
        nonlocal added
        ts_source = "pro_regex"
        # Try to inherit a date from the chapter or nearby event.
        inherited_ts = "unknown"
        if cid:
            for ev in vision.events.values():
                if (ev.annotations or {}).get("chapter_id") == cid and _is_known_ts(ev.timestamp):
                    inherited_ts = ev.timestamp
                    break
        dedup = (instrument, round(value, 3), inherited_ts, page)
        if dedup in seen_keys:
            return
        seen_keys.add(dedup)
        eid = f"pro_{instrument.lower()}_{inherited_ts}_{page or 0}_{added:03d}"
        vision.add_event(
            event_id=eid,
            event_type="pro",
            timestamp=inherited_ts,
            preview=f"{instrument} = {value}{(' ' + units) if units else ''}",
            discovered_by="graph_finalize:pro_harvest",
            annotations={
                "instrument": instrument,
                "value": value,
                "units": units,
                "pdf_page": page,
                "chapter_id": cid,
                "timestamp_source": ts_source,
            },
        )
        added += 1

    # Pass A: raw page text (most reliable).
    # Build a reverse map from page -> chapter_id using existing events.
    page_to_chapter: Dict[int, str] = {}
    for ev in vision.events.values():
        ann = ev.annotations or {}
        pn = ann.get("pdf_page")
        cid = ann.get("chapter_id")
        if isinstance(pn, int) and cid and pn not in page_to_chapter:
            page_to_chapter[pn] = str(cid)

    for page, text in pages_text.items():
        if not text:
            continue
        cid = page_to_chapter.get(page)
        for name, rx, default_units in _PRO_INSTRUMENTS:
            for m in rx.finditer(text):
                try:
                    val = float(m.group(1))
                except (TypeError, ValueError):
                    continue
                _emit(name, val, default_units, page, cid)

    # Pass B: previews (catches anything the LLM summarized in-line).
    for ev in list(vision.events.values()):
        text = ev.preview or ""
        if not text:
            continue
        page = (ev.annotations or {}).get("pdf_page") if isinstance((ev.annotations or {}).get("pdf_page"), int) else None
        cid = (ev.annotations or {}).get("chapter_id")
        for name, rx, default_units in _PRO_INSTRUMENTS:
            for m in rx.finditer(text):
                try:
                    val = float(m.group(1))
                except (TypeError, ValueError):
                    continue
                _emit(name, val, default_units, page, cid)

    return {"pros_extracted": added}


# =============================================================================
# 9. Patient-level metadata
# =============================================================================

_DOB_RX = re.compile(r"(?:date\s+of\s+birth|dob|born)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
_SEX_RX = re.compile(r"\bsex\s*[:\-]?\s*(male|female|m|f)\b", re.I)
_NAME_RX = re.compile(
    r"(?:patient(?:\s+name)?|name)\s*[:\-]?\s*([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,3})",
)
_MRN_RX = re.compile(r"\bMRN\s*[:\-]?\s*([A-Z0-9\-]{4,20})")
_ZIP_RX = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
_SMOKING_RX = re.compile(r"\b(smoker|non[-\s]?smoker|never\s+smoked|former\s+smoker|current\s+smoker)\b", re.I)


def _extract_patient_metadata(
    vision: PatientTimelineVision,
    pages_text: Dict[int, str],
) -> Dict[str, int]:
    """Harvest coarse patient-level metadata into ``vision.metadata['patient']``.

    Uses: (a) raw pages_text when provided (cover + problem-list pages),
          (b) first 1-2 event previews as a fallback.

    This intentionally stops short of full PHI parsing.  It captures the
    handful of fields longitudinal registries universally require (DOB,
    sex, smoking, ZIP3).  Name/MRN are captured in a separate block so
    the registry export layer can redact them independently.
    """
    patient: Dict[str, Any] = vision.metadata.get("patient") or {}
    phi: Dict[str, Any] = vision.metadata.get("patient_phi") or {}

    def _pick_first_two_pages() -> str:
        keys = sorted(pages_text.keys())
        return "\n".join(pages_text[k] for k in keys[:4])

    haystack = _pick_first_two_pages() if pages_text else ""
    if not haystack:
        # Fallback: first few event previews.
        first_events = list(vision.events.values())[:20]
        haystack = "\n".join((ev.preview or "") for ev in first_events)

    if "dob" not in patient:
        m = _DOB_RX.search(haystack)
        if m:
            dt = parse_clinical_date(m.group(1))
            if dt:
                patient["dob"] = dt.strftime("%Y-%m-%d")
    if "sex" not in patient:
        m = _SEX_RX.search(haystack)
        if m:
            val = m.group(1).lower()
            patient["sex"] = "male" if val.startswith("m") else "female"
    if "smoking_status" not in patient:
        m = _SMOKING_RX.search(haystack)
        if m:
            patient["smoking_status"] = m.group(1).lower()
    if "zip3" not in patient:
        m = _ZIP_RX.search(haystack)
        if m:
            patient["zip3"] = m.group(1)[:3]

    # PHI lives in a separate block so registry_export can drop it.
    if "name" not in phi:
        m = _NAME_RX.search(haystack)
        if m:
            phi["name"] = m.group(1).strip()
    if "mrn" not in phi:
        m = _MRN_RX.search(haystack)
        if m:
            phi["mrn"] = m.group(1).strip()

    if patient:
        vision.metadata["patient"] = patient
    if phi:
        vision.metadata["patient_phi"] = phi
    return {"fields_set": len(patient), "phi_fields_set": len(phi)}


# =============================================================================
# 10. Salience
# =============================================================================

def _compute_salience(vision: PatientTimelineVision) -> Dict[str, int]:
    """Stamp ``annotations.salience`` (float) on every event.

    Formula (tuned to be simple and monotonic):

        salience = 1.0
                 + log(1 + degree)
                 + 0.5  * has_icd
                 + 0.5  * has_drug
                 + 0.5  * is_arc_hub
                 + 0.75 * has_caused_by_or_in_workup_for
    """
    event_arc_hub: set = set()
    for arc in vision.arcs.values():
        if arc.event_ids:
            event_arc_hub.add(arc.event_ids[0])

    stamped = 0
    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        degree = sum(len(t) for t in ev.connascence.values())
        has_icd = 1 if ann.get("icd_code") or _ICD_IN_PREVIEW_RX.search(ev.preview or "") else 0
        has_drug = 1 if ann.get("drug_name") else 0
        is_hub = 1 if eid in event_arc_hub else 0
        has_causal = 1 if (
            ev.connascence.get("caused_by") or ev.connascence.get("in_workup_for")
        ) else 0
        sal = (
            1.0
            + math.log1p(degree)
            + 0.5 * has_icd
            + 0.5 * has_drug
            + 0.5 * is_hub
            + 0.75 * has_causal
        )
        ev.annotations["salience"] = round(sal, 4)
        stamped += 1
    return {"events_scored": stamped}


# =============================================================================
# 11. Event cards (compact agent-streaming view)
# =============================================================================

_TITLE_TRIM_RX = re.compile(r"^\s*[a-z]", re.I)
_WHITESPACE_COLLAPSE = re.compile(r"\s+")


def _one_line(text: str, limit: int = 140) -> str:
    # Apply the pipeline-wide PHI guard before building the card excerpt so
    # that banner residue in ``ev.preview`` never reaches ``card.one_line``.
    from server.eoh.heuristic_page_extract import redact_preview_phi  # local import: avoid cycle
    t = _WHITESPACE_COLLAPSE.sub(" ", redact_preview_phi(text or "").strip())
    if len(t) <= limit:
        return t
    cut = t.rfind(" ", 0, limit)
    if cut < limit - 40:
        cut = limit
    return t[:cut].rstrip(" ,.;:-") + "\u2026"


def _event_title(ev: TimelineEventVision) -> str:
    """Best-effort short title (≤60 chars) for an event."""
    ann = ev.annotations or {}
    if ev.event_type == "medication" and ann.get("drug_name"):
        dose = ann.get("drug_dosage") or ""
        return _one_line(f"{ann['drug_name']} {dose}".strip(), 60)
    if ev.event_type == "diagnosis":
        icd = ann.get("icd_code")
        preview = ev.preview or ""
        if icd:
            # Trim "[ICD]" off the end if present.
            return _one_line(re.sub(r"\s*\[.*$", "", preview), 60)
        return _one_line(preview, 60)
    if ev.event_type == "pro":
        return _one_line(ev.preview or "", 60)
    return _one_line(ev.preview or ev.event_type, 60)


def _build_event_cards(vision: PatientTimelineVision) -> Dict[str, int]:
    """Stamp ``annotations.card`` on every event — a compact view the
    agent can stream for subgraph selection without loading full nodes.

    Shape::
        {
          "title":    <=60 chars,
          "one_line": <=140 chars,
          "ts":       "YYYY-MM-DD" | "unknown",
          "type":     event_type,
          "icd":      "I48.0" | null,
          "drug":     "methotrexate" | null,
          "arc_ids":  [...],
          "salience": 2.34,
        }
    """
    stamped = 0
    for ev in vision.events.values():
        ann = ev.annotations or {}
        icd = ann.get("icd_code")
        if not icd:
            m = _ICD_IN_PREVIEW_RX.search(ev.preview or "")
            icd = m.group(1) if m else None
        card = {
            "title": _event_title(ev),
            "one_line": _one_line(ev.preview, 140),
            "ts": ev.timestamp or "unknown",
            "type": ev.event_type,
            "icd": icd,
            "drug": ann.get("drug_name"),
            "arc_ids": list(ann.get("arc_ids") or []),
            "salience": ann.get("salience"),
        }
        ev.annotations["card"] = card
        stamped += 1
    return {"cards_built": stamped}


# =============================================================================
# 12. Index block (agent entry point)
# =============================================================================

def _build_index_block(vision: PatientTimelineVision) -> Dict[str, int]:
    """Compute a top-level traversal index at ``vision.metadata['index']``.

    Shape::
        {
          "by_year":    { "2016": [event_ids…] },
          "by_icd":     { "I48.0": [...] },
          "by_icd_family": { "I48": [...] },
          "by_drug":    { "methotrexate": [...] },
          "by_chapter": { chapter_id: [...] },
          "by_arc":     { arc_id: [...] },
          "top_salience_event_ids": [eid, ...],
          "entities_by_kind": { "drug": [...], "icd": [...], ... },
        }
    """
    by_year: Dict[str, List[str]] = defaultdict(list)
    by_icd: Dict[str, List[str]] = defaultdict(list)
    by_icd_family: Dict[str, List[str]] = defaultdict(list)
    by_drug: Dict[str, List[str]] = defaultdict(list)
    by_chapter: Dict[str, List[str]] = defaultdict(list)
    by_arc: Dict[str, List[str]] = defaultdict(list)
    salience_ordered: List[Tuple[float, str]] = []

    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        ts = ev.timestamp or ""
        if ts and ts[:4].isdigit():
            by_year[ts[:4]].append(eid)
        icd = ann.get("icd_code")
        if not icd:
            m = _ICD_IN_PREVIEW_RX.search(ev.preview or "")
            if m:
                icd = m.group(1)
        if icd:
            icd_u = str(icd).upper()
            by_icd[icd_u].append(eid)
            fam = _icd_family(icd_u)
            if fam:
                by_icd_family[fam].append(eid)
        drug = ann.get("drug_name")
        if drug:
            by_drug[str(drug).strip().lower()].append(eid)
        cid = ann.get("chapter_id")
        if cid:
            by_chapter[str(cid)].append(eid)
        for aid in (ann.get("arc_ids") or []):
            by_arc[aid].append(eid)
        sal = ann.get("salience")
        if isinstance(sal, (int, float)):
            salience_ordered.append((float(sal), eid))

    salience_ordered.sort(reverse=True)
    top_salience = [eid for _, eid in salience_ordered[:50]]

    entities_by_kind: Dict[str, List[str]] = defaultdict(list)
    for key, ent in (vision.metadata.get("entities") or {}).items():
        entities_by_kind[ent.get("kind", "unknown")].append(key)

    index = {
        "by_year": dict(by_year),
        "by_icd": dict(by_icd),
        "by_icd_family": dict(by_icd_family),
        "by_drug": dict(by_drug),
        "by_chapter": dict(by_chapter),
        "by_arc": dict(by_arc),
        "top_salience_event_ids": top_salience,
        "entities_by_kind": dict(entities_by_kind),
    }
    vision.metadata["index"] = index
    return {
        "years": len(by_year),
        "icds": len(by_icd),
        "drugs": len(by_drug),
        "chapters": len(by_chapter),
        "arcs": len(by_arc),
    }


# =============================================================================
# 13. Code index — flat per-code chronology (drugs / icd / rxnorm / labs / loinc)
# =============================================================================

def _build_code_index(vision: PatientTimelineVision) -> Dict[str, int]:
    """Build the flat per-code chronology at ``vision.metadata['code_index']``.

    Implementation lives in :mod:`server.eoh.code_index_ops`; this
    function is a thin delegate so that finalize and the single-event
    upsert (used by enrichment agents) share one definition of
    "what does this event contribute to the code index."

    See :func:`server.eoh.code_index_ops.rebuild_code_index` for the
    full shape contract.  Rationale:

    * Arcs are for **narratives** (an encounter, a diagnostic workup, an
      ICD family).
    * Codes are for **lookups** — an 8B traversal agent looking for
      "every time this patient got hydrocodone-acetaminophen" should get
      a sorted list of administrations with dose/route, not a
      single-event "arc".

    Whenever an agent writes a code onto an event that was missed here,
    it MUST pair that write with
    :func:`server.eoh.code_index_ops.upsert_event_in_code_index` (or the
    higher-level :func:`register_code_on_event`) so this index stays
    authoritative.
    """
    from server.eoh import code_index_ops
    return code_index_ops.rebuild_code_index(vision)
