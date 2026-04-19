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
5. Call eoh-llama once per chart (five parallel requests) for chart-specific text.
6. Persist analytics summary + per-chart interpretations as vision.metadata["last_analytics"].
7. Return:
   {
     "analytics":        { … },
     "charts":           { stability_band, … },   # base64 PNG
     "interpretations":  { "<chart_key>": "<eoh-llama text per view>", … },
     "interpretation":   "<stability_band text; backward compat>",
     "graph_skeleton":   { events: [...], arcs: [...] },
     "event_count":      int,
     "dated_count":      int,
     "source":           "ptv",
     "disclaimer":       "…"
   }
"""
from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request

from database.models.postgresql.models import User
from server.api.session_routes import get_vault_user_from_session

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


CHART_KEYS: Tuple[str, ...] = (
    "stability_band",
    "event_edge_intensity",
    "precedence_map",
    "terrain_trajectory",
    "flare_noise_panel",
)


def _chart_prompt_spec(chart_key: str) -> Tuple[str, str]:
    """(title, instructions) for eoh-llama — one dedicated interpretation per chart."""
    specs = {
        "stability_band": (
            "Stability band timeline",
            "Interpret ONLY the stability-band view: windowed stability scores (0–1) over time, "
            "the green/yellow/red regime bands, and any phase-shift markers. "
            "Write 3–5 sentences for a patient: what the trend suggests, whether things look "
            "more stable or more volatile lately, and one question for their clinician. "
            "Do not diagnose; hedge your language.",
        ),
        "event_edge_intensity": (
            "Event & edge intensity",
            "Interpret ONLY this view: per-window event counts vs connascence load. "
            "Explain what it means when bars are high with high vs low orange line. "
            "3–5 sentences, patient-facing, no diagnosis.",
        ),
        "precedence_map": (
            "Precedence map",
            "Interpret ONLY the directed graph of event-type pairs and lags. "
            "Stress that arrows are predictive associations, not causes. "
            "Highlight 1–2 strongest patterns if any. 3–5 sentences, patient-facing.",
        ),
        "terrain_trajectory": (
            "Terrain trajectory",
            "Interpret ONLY the 2-D trajectory of windowed feature vectors (path from START to NOW). "
            "Explain clustering vs wandering path in plain language. 3–5 sentences, no diagnosis.",
        ),
        "flare_noise_panel": (
            "Flare vs noise",
            "Interpret ONLY flare episodes vs the noise floor and event intensity bars. "
            "What elevated periods might mean for follow-up. 3–5 sentences, hedged, patient-facing.",
        ),
    }
    return specs.get(chart_key, (chart_key, "Interpret this chart for a patient in 3–5 sentences. No diagnosis."))


def _context_json_for_chart(
    chart_key: str,
    analytics_payload: Dict[str, Any],
    trajectory_serial: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Slice analytics for a single chart's LLM context."""
    a = analytics_payload
    wins = a.get("windows") or []

    if chart_key == "stability_band":
        return {
            "chart": chart_key,
            "total_events": a.get("total_events"),
            "span_days": a.get("span_days"),
            "windows": [
                {
                    "window_start": (w.get("window_start") or "")[:10],
                    "stability_score": round(float(w.get("stability_score") or 0), 3),
                    "event_count": w.get("event_count"),
                }
                for w in wins[-25:]
            ],
            "phase_shifts": a.get("phase_shifts") or [],
        }

    if chart_key == "event_edge_intensity":
        return {
            "chart": chart_key,
            "windows": [
                {
                    "window_start": (w.get("window_start") or "")[:10],
                    "event_count": w.get("event_count"),
                    "connascence_load": round(float(w.get("connascence_load") or 0), 4),
                }
                for w in wins[-25:]
            ],
        }

    if chart_key == "precedence_map":
        edges = a.get("precedence_edges") or []
        return {
            "chart": chart_key,
            "precedence_edges": edges[:16],
        }

    if chart_key == "terrain_trajectory":
        return {
            "chart": chart_key,
            "trajectory_points": trajectory_serial[-40:],
            "window_count": len(wins),
        }

    if chart_key == "flare_noise_panel":
        return {
            "chart": chart_key,
            "noise_floor": a.get("noise_floor"),
            "flare_episodes": a.get("flare_episodes") or [],
            "windows_event_intensity": [
                {"window_start": (w.get("window_start") or "")[:10], "event_count": w.get("event_count")}
                for w in wins[-25:]
            ],
        }

    return {"chart": chart_key}


async def _call_eoh_llama_chart(
    ollama_base: str,
    model: str,
    chart_key: str,
    analytics_payload: Dict[str, Any],
    trajectory_serial: List[Dict[str, Any]],
    skeleton: Dict[str, Any],
) -> tuple[str, Optional[str]]:
    """Returns (chart_key, interpretation_text_or_None)."""
    import httpx

    title, instructions = _chart_prompt_spec(chart_key)
    ctx = _context_json_for_chart(chart_key, analytics_payload, trajectory_serial)
    sk_trim = json.dumps(skeleton, indent=2)[:2200]

    prompt = (
        f"You are a clinical second-opinion assistant. The patient is looking at "
        f"one analytics chart from their Patient Timeline Vision (PTV).\n\n"
        f"CHART: {title}\n"
        f"TASK: {instructions}\n\n"
        f"DATA FOR THIS CHART (JSON):\n{json.dumps(ctx, indent=2)}\n\n"
        f"GRAPH SKELETON (truncated):\n{sk_trim}\n\n"
        "Write ONLY the interpretation paragraphs — no preamble, no markdown headers."
    )

    try:
        async with httpx.AsyncClient(timeout=75) as http:
            resp = await http.post(
                f"{ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_ctx": 6144, "temperature": 0.12},
                },
            )
            resp.raise_for_status()
            text = (resp.json().get("message") or {}).get("content", "").strip() or None
            return chart_key, text
    except Exception as exc:
        logger.warning("eoh-llama chart %s interpretation failed: %s", chart_key, exc)
        return chart_key, None


async def _interpret_all_charts_parallel(
    ollama_base: str,
    model: str,
    analytics_payload: Dict[str, Any],
    trajectory_serial: List[Dict[str, Any]],
    skeleton: Dict[str, Any],
) -> Dict[str, Optional[str]]:
    """One eoh-llama call per chart; run in parallel."""
    import asyncio

    tasks = [
        _call_eoh_llama_chart(
            ollama_base, model, key, analytics_payload, trajectory_serial, skeleton
        )
        for key in CHART_KEYS
    ]
    results = await asyncio.gather(*tasks)
    out: Dict[str, Optional[str]] = {}
    for k, text in results:
        out[k] = text
    return out


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

    # ── 4. Build graph skeleton + trajectory serial for LLM ──────────────────
    skeleton = _build_graph_skeleton(vision_events, vision_arcs)
    trajectory_serial = [
        {
            "timestamp": p.timestamp,
            "x": round(p.x, 4),
            "y": round(p.y, 4),
            "stability_class": p.stability_class,
            "event_count": p.event_count,
        }
        for p in traj_points
    ]

    # ── 5. eoh-llama — one interpretation per chart (parallel) ─────────────────
    interpretations = await _interpret_all_charts_parallel(
        _ollama_base(),
        model,
        analytics_payload,
        trajectory_serial,
        skeleton,
    )
    # Backward compat: single field = stability band if present, else first non-empty
    interpretation = interpretations.get("stability_band")
    if not interpretation:
        for _k in CHART_KEYS:
            if interpretations.get(_k):
                interpretation = interpretations[_k]
                break

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
            "interpretations": interpretations,
            "interpretation": interpretation,
        }
        await save_timeline_vision_pg(pool, vision)
    except Exception as save_err:
        logger.warning("ptv_analytics: failed to persist last_analytics: %s", save_err)

    return {
        "analytics": analytics_payload,
        "charts": charts,
        "interpretations": interpretations,
        "interpretation": interpretation,
        "graph_skeleton": skeleton,
        "event_count": total_count,
        "dated_count": dated_count,
        "source": "ptv",
        "disclaimer": _DISCLAIMER,
    }
