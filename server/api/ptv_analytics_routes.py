"""
PTV-native analytics endpoint.

GET /api/timeline/ptv/analytics
    Vault session auth only — reads EXCLUSIVELY from ehr.patient_graph_vision.
    No ehr.patient_timeline access.

Workflow
--------
1. Load PatientTimelineVision from patient_graph_vision.
2. Convert dated events → analytics-compatible dicts (ts, event_type, text …).
3. Run analytics (windowed vectors, stability, phase-shifts, flares) + render
   all five Matplotlib charts.
4. Build a reduced graph skeleton for eoh-llama context (≤ 50 events + arcs).
5. Call eoh-llama to produce a plain-language interpretation of the JSON result.
6. Persist the analytics summary + interpretation as vision.metadata["last_analytics"].
7. Return:
   {
     "analytics":     { total_events, span_days, windows, phase_shifts,
                        flare_episodes, noise_floor, params },
     "charts":        { stability_band, event_edge_intensity, precedence_map,
                        terrain_trajectory, flare_noise_panel },   # base64 PNG
     "interpretation": "<plain-language narrative>",
     "graph_skeleton": { events: [...], arcs: [...] },
     "event_count":   int,
     "dated_count":   int,        # events with parseable timestamps
     "source":        "ptv",
     "disclaimer":    "…"
   }
"""
from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from server.api.session_routes import get_vault_user_from_session
from server.db.users import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/timeline",
    tags=["ptv-analytics"],
)

_DISCLAIMER = (
    "This is a decision-support tool, not a diagnosis. "
    "Metrics reflect predictive associations derived from graph topology, "
    "not clinical causation. All findings require clinical correlation."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ptv_events_to_analytics(vision_events: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert PatientTimelineVision.events dict → analytics-compatible list.
    Only events that carry a parseable timestamp are included.
    """
    from server.utils.parse_date import parse_clinical_date, extract_date_from_text

    out: List[Dict[str, Any]] = []
    for eid, raw in vision_events.items():
        if not isinstance(raw, dict):
            continue
        ts_raw = (raw.get("timestamp") or "").strip()
        preview = (raw.get("preview") or "")
        ts = parse_clinical_date(ts_raw) if ts_raw else None
        if ts is None and preview:
            ts = extract_date_from_text(preview)
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        discovered = raw.get("discovered_by") or []
        src = "ptv"
        if isinstance(discovered, list) and discovered:
            src = ",".join(str(x) for x in discovered[:3])
        elif isinstance(discovered, str) and discovered:
            src = discovered
        out.append({
            "id": str(raw.get("event_id") or eid),
            "ts": ts,
            "event_type": raw.get("event_type") or "unknown",
            "source": src,
            "text": preview[:4000] if preview else None,
            "structured": None,
            "meta": {"from_ptv": True},
        })
    out.sort(key=lambda e: e["ts"])
    return out


def _build_graph_skeleton(
    vision_events: Dict[str, Any],
    vision_arcs: Dict[str, Any],
    max_events: int = 50,
) -> Dict[str, Any]:
    """
    Reduced graph structure for eoh-llama context.
    Returns event stubs (id, type, date, preview[:120]) + arc summaries.
    """
    from server.utils.parse_date import parse_clinical_date, extract_date_from_text

    events_out: List[Dict[str, Any]] = []
    for eid, raw in vision_events.items():
        if not isinstance(raw, dict):
            continue
        ts_raw = (raw.get("timestamp") or "").strip()
        preview = (raw.get("preview") or "")
        ts = parse_clinical_date(ts_raw) if ts_raw else None
        if ts is None and preview:
            ts = extract_date_from_text(preview)
        date_str = ts.strftime("%Y-%m-%d") if ts else "unknown"
        events_out.append({
            "id": str(raw.get("event_id") or eid),
            "type": raw.get("event_type") or "unknown",
            "date": date_str,
            "preview": preview[:120] if preview else "",
            "connascence_count": sum(
                len(v) for v in (raw.get("connascence") or {}).values()
            ),
        })

    events_out.sort(key=lambda e: e["date"])
    if len(events_out) > max_events:
        step = len(events_out) // max_events
        events_out = events_out[::step][:max_events]

    arcs_out: List[Dict[str, Any]] = []
    for aid, arc in vision_arcs.items():
        if not isinstance(arc, dict):
            continue
        arcs_out.append({
            "id": str(arc.get("arc_id") or aid),
            "name": arc.get("name") or "",
            "status": arc.get("status") or "unexplored",
            "event_count": len(arc.get("event_ids") or []),
            "summary": (arc.get("summary") or "")[:200],
        })

    return {"events": events_out, "arcs": arcs_out}


async def _call_eoh_llama(
    ollama_base: str,
    model: str,
    analytics_json: Dict[str, Any],
    skeleton: Dict[str, Any],
) -> Optional[str]:
    """Call eoh-llama with analytics JSON + graph skeleton for interpretation."""
    import httpx

    # Trim analytics for prompt: drop per-window provenance, keep summary fields
    a = analytics_json
    windows_summary = [
        {
            "window_start": w["window_start"][:10],
            "stability_score": round(w["stability_score"], 3),
            "event_count": w["event_count"],
            "drift": round(w["drift"], 3),
        }
        for w in (a.get("windows") or [])
    ]

    analytics_compact = {
        "total_events": a.get("total_events"),
        "span_days": a.get("span_days"),
        "windows": windows_summary[-20:],  # last 20 windows
        "phase_shifts": [
            {
                "timestamp": ps["timestamp"][:10] if ps.get("timestamp") else "",
                "from_phase": ps.get("from_phase"),
                "to_phase": ps.get("to_phase"),
            }
            for ps in (a.get("phase_shifts") or [])
        ],
        "flare_episodes": [
            {
                "start": fe["start"][:10] if fe.get("start") else "",
                "end": fe["end"][:10] if fe.get("end") else "",
                "confidence": round(fe.get("confidence") or 0, 2),
            }
            for fe in (a.get("flare_episodes") or [])
        ],
        "noise_floor": a.get("noise_floor"),
    }

    prompt = (
        "You are a clinical second-opinion assistant reviewing a patient's "
        "longitudinal health timeline graph.\n\n"
        "Below is a JSON analytics summary computed from their Patient Timeline "
        "Vision (PTV) graph. Your task is to write a clear, plain-language "
        "interpretation (4–6 sentences) that a patient could read and understand. "
        "Focus on:\n"
        "  • Overall stability trend and what it means for the patient\n"
        "  • Phase shifts if any — what changed and when\n"
        "  • Flare episodes if any — periods of heightened activity\n"
        "  • Whether the trajectory suggests improvement, worsening, or stability\n"
        "  • One practical question the patient might bring to their next appointment\n\n"
        "Do NOT make diagnoses. Use hedged language (e.g. 'the data suggests', "
        "'this may indicate'). Reference specific dates when available.\n\n"
        f"ANALYTICS JSON:\n{json.dumps(analytics_compact, indent=2)}\n\n"
        f"GRAPH SKELETON ({len(skeleton.get('events', []))} events, "
        f"{len(skeleton.get('arcs', []))} arcs shown):\n"
        f"{json.dumps(skeleton, indent=2)[:3000]}\n\n"
        "INTERPRETATION:"
    )

    try:
        async with httpx.AsyncClient(timeout=90) as http:
            resp = await http.post(
                f"{ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_ctx": 8192, "temperature": 0.15},
                },
            )
            resp.raise_for_status()
            return (resp.json().get("message") or {}).get("content", "").strip() or None
    except Exception as exc:
        logger.warning("eoh-llama interpretation failed: %s", exc)
        return None


def _ollama_base() -> str:
    """Reuse the same helper used in session_routes."""
    from server.api.session_routes import _ollama_native_base_url
    return _ollama_native_base_url()


# ---------------------------------------------------------------------------
# GET /api/timeline/ptv/analytics
# ---------------------------------------------------------------------------

@router.get("/ptv/analytics")
async def ptv_analytics(
    request: Request,
    model: str = "eoh-llama3.1:8b",
    window_days: int = 7,
    user: User = Depends(get_vault_user_from_session),
) -> Dict[str, Any]:
    """
    Compute analytics exclusively from patient_graph_vision, call eoh-llama
    for plain-language interpretation, and persist last_analytics into
    vision.metadata.

    No ehr.patient_timeline access — PTV is the only source of truth.
    """
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool unavailable")

    patient_id = str(user.id)

    # ── 1. Load PTV ──────────────────────────────────────────────────────────
    from server.eoh.patient_timeline_vision import (
        load_timeline_vision_pg,
        save_timeline_vision_pg,
    )

    vision = await load_timeline_vision_pg(pool, patient_id)
    if vision is None or not vision.events:
        raise HTTPException(
            status_code=404,
            detail=(
                "No timeline graph found. Upload documents or ingest a clinical "
                "PDF to build your Patient Timeline Vision."
            ),
        )

    vision_dict = vision.to_dict()
    vision_events = vision_dict.get("events") or {}
    vision_arcs = vision_dict.get("arcs") or {}

    # ── 2. Convert PTV events → analytics format ─────────────────────────────
    events = _ptv_events_to_analytics(vision_events)
    dated_count = len(events)
    total_count = len(vision_events)

    if dated_count < 2:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Timeline has {total_count} event(s) but only {dated_count} "
                "carry parseable dates. Ingest a clinical PDF so eoh-llama can "
                "extract dated events."
            ),
        )

    # ── 3. Run analytics ─────────────────────────────────────────────────────
    from server.timeline.analytics import (
        build_windowed_vectors,
        compute_window_metrics,
        detect_phase_shifts,
        extract_flare_episodes,
        compute_precedence_edges,
        compute_trajectory_points,
        compute_analytics_summary,
    )
    from server.timeline.charts import render_all_charts

    summary = compute_analytics_summary(
        patient_id=patient_id,
        events=events,
        connascence_edges=[],
        window_days=window_days,
    )

    prec_edges = compute_precedence_edges(events)
    vectors = build_windowed_vectors(events, [], window_days)
    traj_points = compute_trajectory_points(vectors, summary.windows)

    charts = render_all_charts(
        metrics=summary.windows,
        phase_shifts=summary.phase_shifts,
        flare_episodes=summary.flare_episodes,
        noise_floor=summary.noise_floor,
        precedence_edges=prec_edges,
        trajectory_points=traj_points,
        patient_id=patient_id,
    )

    analytics_payload: Dict[str, Any] = {
        "total_events": summary.total_events,
        "span_days": summary.span_days,
        "windows": [
            {
                "window_start": w.window_start,
                "window_end": w.window_end,
                "drift": w.drift,
                "curvature": w.curvature,
                "connascence_load": w.connascence_load,
                "stability_score": w.stability_score,
                "event_count": w.event_count,
            }
            for w in summary.windows
        ],
        "phase_shifts": [
            {
                "timestamp": ps.timestamp,
                "from_phase": ps.from_phase,
                "to_phase": ps.to_phase,
                "stability_before": ps.stability_before,
                "stability_after": ps.stability_after,
            }
            for ps in summary.phase_shifts
        ],
        "flare_episodes": [
            {
                "start": fe.start,
                "end": fe.end,
                "confidence": fe.confidence,
                "peak_intensity": fe.peak_intensity,
            }
            for fe in summary.flare_episodes
        ],
        "precedence_edges": [
            {
                "from_type": e.from_type,
                "to_type": e.to_type,
                "median_lag_days": e.median_lag_days,
                "support_count": e.support_count,
                "confidence": e.confidence,
            }
            for e in prec_edges
        ],
        "noise_floor": summary.noise_floor,
        "params": summary.params,
    }

    # ── 4. Build graph skeleton ───────────────────────────────────────────────
    skeleton = _build_graph_skeleton(vision_events, vision_arcs)

    # ── 5. eoh-llama interpretation ───────────────────────────────────────────
    interpretation = await _call_eoh_llama(
        _ollama_base(), model, analytics_payload, skeleton
    )

    # ── 6. Persist last_analytics into vision.metadata ────────────────────────
    try:
        from datetime import datetime

        vision.metadata["last_analytics"] = {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "window_days": window_days,
            "total_events": summary.total_events,
            "dated_count": dated_count,
            "span_days": summary.span_days,
            "phase_shift_count": len(summary.phase_shifts),
            "flare_episode_count": len(summary.flare_episodes),
            "noise_floor": summary.noise_floor,
            "latest_stability": (
                summary.windows[-1].stability_score if summary.windows else None
            ),
            "interpretation": interpretation,
        }
        await save_timeline_vision_pg(pool, vision)
    except Exception as save_err:
        logger.warning("ptv_analytics: failed to persist last_analytics: %s", save_err)

    return {
        "analytics": analytics_payload,
        "charts": charts,
        "interpretation": interpretation,
        "graph_skeleton": skeleton,
        "event_count": total_count,
        "dated_count": dated_count,
        "source": "ptv",
        "disclaimer": _DISCLAIMER,
    }
