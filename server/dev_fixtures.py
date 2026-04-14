"""
Dev fixtures — Norman Eric Roberts patient timeline.

Loaded from artifacts/timeline_ollama_20260329_1805/ when DEV_AUTH_BYPASS=true.
Provides the full PTV event set to timeline endpoints without a DB connection.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEV_TIMELINE_ID = "norman-dev-timeline"
DEV_PATIENT_NAME = "Norman Eric Roberts"
DEV_PATIENT_DOB = "1947-08-17"

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts" / "timeline_ollama_20260329_1805"

_PTV_VISION_FILE = _ARTIFACTS_DIR / "patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
_PTV_SNAPSHOT_FILE = _ARTIFACTS_DIR / "patient_timeline_snapshot_norman_eric_roberts_20260329_195915.json"


def _resolve_ptv_candidate_files() -> List[Path]:
    """
    Allow UX dev to point at a specific Norman timeline export (for example one
    derived from NormanEricRoberts_decrypted).
    """
    out: List[Path] = []
    env_snapshot = (os.getenv("DEV_TIMELINE_SNAPSHOT_FILE") or "").strip()
    env_vision = (os.getenv("DEV_TIMELINE_VISION_FILE") or "").strip()
    if env_snapshot:
        out.append(Path(env_snapshot))
    if env_vision:
        out.append(Path(env_vision))
    out.extend([_PTV_SNAPSHOT_FILE, _PTV_VISION_FILE])
    return out

# ---------------------------------------------------------------------------
# Active flag
# ---------------------------------------------------------------------------

def is_active() -> bool:
    return (
        os.getenv("DEV_AUTH_BYPASS", "").lower() == "true"
        and os.getenv("APP_ENV", "local") != "production"
    )


# ---------------------------------------------------------------------------
# Event loading and transformation
# ---------------------------------------------------------------------------

def _parse_timestamp(raw: Any, fallback_dt: datetime) -> str:
    """Convert PTV timestamp to ISO string. Falls back to fallback_dt."""
    if not raw or raw == "unknown":
        return fallback_dt.isoformat() + "Z"
    if isinstance(raw, datetime):
        return raw.isoformat() + "Z"
    s = str(raw).strip()
    # Try common formats
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt).isoformat() + "Z"
        except ValueError:
            continue
    # ISO-like with fractional or Z suffix
    try:
        from dateutil import parser as dp
        return dp.parse(s).isoformat() + "Z"
    except Exception:
        pass
    return fallback_dt.isoformat() + "Z"


def _ptv_event_to_api(event_id: str, ev: Dict[str, Any], fallback_dt: datetime) -> Dict[str, Any]:
    """Transform a PTV event dict to the shape returned by GET /api/timeline/{id}."""
    raw_ts = ev.get("timestamp") or ev.get("ts") or "unknown"
    ts = _parse_timestamp(raw_ts, fallback_dt)

    event_type = ev.get("event_type") or ev.get("type") or "clinical_event"
    discovered = ev.get("discovered_by") or []
    source = discovered[0] if discovered else "ptv"
    preview = ev.get("preview") or ev.get("text") or ""
    annotations = ev.get("annotations") or {}

    return {
        "ts": ts,
        "event_type": event_type,
        "source": source,
        "structured": None,
        "text": preview[:500] if preview else None,
        "meta": {**annotations, "event_id": event_id},
    }


@lru_cache(maxsize=1)
def _load_events_cached() -> List[Dict[str, Any]]:
    """Load and transform events from the PTV JSON. Result is cached in memory."""

    # Try override paths first, then defaults.
    for path in _resolve_ptv_candidate_files():
        if path.exists():
            logger.info("DEV_FIXTURES: loading Norman timeline from %s", path.name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                break
            except Exception as e:
                logger.warning("DEV_FIXTURES: failed to load %s: %s", path.name, e)
    else:
        logger.warning("DEV_FIXTURES: no artifact file found — returning empty timeline")
        return []

    # Events can be a dict (PTV format) or a list.
    raw_events = data.get("events") or data.get("timeline_events") or []
    if isinstance(raw_events, dict):
        items = list(raw_events.items())
    elif isinstance(raw_events, list):
        items = [(ev.get("event_id", str(i)), ev) for i, ev in enumerate(raw_events)]
    else:
        return []

    # Base date: spread events from 1980 to 2025 for those without timestamps.
    base_date = datetime(1980, 1, 1)
    total = max(len(items), 1)
    span_days = 365 * 45  # 45 years

    results: List[Dict[str, Any]] = []
    for idx, (eid, ev) in enumerate(items):
        if not isinstance(ev, dict):
            continue
        # Skip status=excluded events.
        if ev.get("status") == "excluded":
            continue
        fallback_dt = base_date + timedelta(days=int(idx * span_days / total))
        results.append(_ptv_event_to_api(eid, ev, fallback_dt))

    # Sort by timestamp ascending.
    results.sort(key=lambda e: e["ts"])

    logger.info("DEV_FIXTURES: loaded %d Norman events", len(results))
    return results


# ---------------------------------------------------------------------------
# Public API (consumed by patched endpoints)
# ---------------------------------------------------------------------------

def get_timeline_status() -> Dict[str, Any]:
    """Return the shape expected by GET /api/timeline/status."""
    if not is_active():
        return {"has_timeline": False, "timeline_id": None, "event_count": 0, "last_updated": None}
    events = _load_events_cached()
    last_updated = events[-1]["ts"] if events else None
    return {
        "has_timeline": True,
        "timeline_id": DEV_TIMELINE_ID,
        "event_count": len(events),
        "last_updated": last_updated,
    }


def get_timeline_events(limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    """Return the shape expected by GET /api/timeline/{patient_id}."""
    events = _load_events_cached()
    page = events[offset: offset + limit]
    return {
        "patient_id": DEV_TIMELINE_ID,
        "events": page,
        "total_events": len(events),
    }


def is_dev_patient_id(patient_id: str) -> bool:
    return patient_id == DEV_TIMELINE_ID
