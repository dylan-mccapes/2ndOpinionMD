"""
Timeline Graph Analytics — Phase 6b

Windowed feature vectors, interpretable metrics, phase-shift detection,
and flare/noise episode extraction from ehr.patient_timeline events
and PatientTimelineVision connascence edges.

All metrics store provenance (window bounds, contributing event IDs,
parameter values). Language: "predictive association", never "caused by".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_WINDOW_DAYS = 7
STABILITY_PARAMS = {"a": 1.0, "b": 0.5, "c": 0.3}
FLARE_BURSTINESS_THRESHOLD = 2.0
PHASE_SHIFT_THRESHOLD = 0.4


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class WindowVector:
    window_start: str
    window_end: str
    event_count: int
    event_types: Dict[str, int]
    edge_count: int
    edge_types: Dict[str, int]
    event_ids: List[str]
    edge_ids: List[str]


@dataclass
class WindowMetrics:
    window_start: str
    window_end: str
    drift: float
    curvature: float
    connascence_load: float
    stability_score: float
    event_count: int
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseShift:
    timestamp: str
    from_phase: str
    to_phase: str
    stability_before: float
    stability_after: float
    evidence_event_ids: List[str] = field(default_factory=list)


@dataclass
class FlareEpisode:
    start: str
    end: str
    confidence: float
    supporting_event_ids: List[str] = field(default_factory=list)
    peak_intensity: float = 0.0


@dataclass
class PrecedenceEdge:
    from_type: str
    to_type: str
    median_lag_days: float
    support_count: int
    confidence: float
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TrajectoryPoint:
    timestamp: str
    x: float
    y: float
    stability_class: str
    event_count: int


@dataclass
class AnalyticsSummary:
    patient_id: str
    window_days: int
    total_events: int
    span_days: int
    windows: List[WindowMetrics]
    phase_shifts: List[PhaseShift]
    flare_episodes: List[FlareEpisode]
    noise_floor: float
    params: Dict[str, Any]


# ---------------------------------------------------------------------------
# Core: Build windowed feature vectors
# ---------------------------------------------------------------------------

def build_windowed_vectors(
    events: List[Dict[str, Any]],
    connascence_edges: List[Dict[str, Any]],
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> List[WindowVector]:
    if not events:
        return []

    timestamps = []
    for e in events:
        ts = e.get("ts")
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        timestamps.append((ts, e))

    if not timestamps:
        return []

    timestamps.sort(key=lambda x: x[0])
    first_ts = timestamps[0][0]
    last_ts = timestamps[-1][0]

    window_delta = timedelta(days=window_days)
    vectors: List[WindowVector] = []
    win_start = first_ts

    while win_start <= last_ts:
        win_end = win_start + window_delta
        win_events = [
            e for ts, e in timestamps if win_start <= ts < win_end
        ]

        event_types: Dict[str, int] = {}
        event_ids: List[str] = []
        for e in win_events:
            etype = (e.get("event_type") or "unknown").lower()
            event_types[etype] = event_types.get(etype, 0) + 1
            eid = e.get("id") or e.get("event_id") or ""
            if eid:
                event_ids.append(str(eid))

        win_start_iso = win_start.isoformat()
        win_end_iso = win_end.isoformat()

        edge_types: Dict[str, int] = {}
        edge_ids: List[str] = []
        for edge in connascence_edges:
            edge_ts = edge.get("ts")
            if edge_ts and isinstance(edge_ts, str):
                try:
                    ets = datetime.fromisoformat(edge_ts.replace("Z", "+00:00"))
                    if ets.tzinfo is None:
                        ets = ets.replace(tzinfo=timezone.utc)
                    if win_start <= ets < win_end:
                        kind = edge.get("kind", "unknown")
                        edge_types[kind] = edge_types.get(kind, 0) + 1
                        eid = edge.get("id", "")
                        if eid:
                            edge_ids.append(str(eid))
                except Exception:
                    pass

        vectors.append(WindowVector(
            window_start=win_start_iso,
            window_end=win_end_iso,
            event_count=len(win_events),
            event_types=event_types,
            edge_count=sum(edge_types.values()),
            edge_types=edge_types,
            event_ids=event_ids,
            edge_ids=edge_ids,
        ))

        win_start = win_end

    return vectors


# ---------------------------------------------------------------------------
# Core: Compute interpretable metrics
# ---------------------------------------------------------------------------

def _vector_magnitude(v: WindowVector) -> float:
    counts = list(v.event_types.values()) + list(v.edge_types.values())
    if not counts:
        return 0.0
    return math.sqrt(sum(c * c for c in counts))


def compute_window_metrics(
    vectors: List[WindowVector],
    params: Optional[Dict[str, float]] = None,
) -> List[WindowMetrics]:
    if not vectors:
        return []

    p = params or STABILITY_PARAMS
    a = p.get("a", 1.0)
    b = p.get("b", 0.5)
    c = p.get("c", 0.3)

    magnitudes = [_vector_magnitude(v) for v in vectors]
    max_mag = max(magnitudes) if magnitudes else 1.0
    if max_mag == 0:
        max_mag = 1.0

    metrics: List[WindowMetrics] = []
    for i, v in enumerate(vectors):
        mag_i = magnitudes[i]
        mag_prev = magnitudes[i - 1] if i > 0 else mag_i

        drift = abs(mag_i - mag_prev) / max_mag

        if i >= 2:
            mag_prev2 = magnitudes[i - 2]
            d1 = mag_i - mag_prev
            d2 = mag_prev - mag_prev2
            curvature = abs(d1 - d2) / max_mag
        else:
            curvature = 0.0

        conn_load = v.edge_count / max(max_mag, 1.0)

        stability = 1.0 / (1.0 + a * drift + b * curvature + c * conn_load)

        metrics.append(WindowMetrics(
            window_start=v.window_start,
            window_end=v.window_end,
            drift=round(drift, 4),
            curvature=round(curvature, 4),
            connascence_load=round(conn_load, 4),
            stability_score=round(stability, 4),
            event_count=v.event_count,
            provenance={
                "params": {"a": a, "b": b, "c": c},
                "event_ids": v.event_ids,
                "edge_ids": v.edge_ids,
                "window_days": (
                    datetime.fromisoformat(v.window_end)
                    - datetime.fromisoformat(v.window_start)
                ).days if v.window_start and v.window_end else 7,
            },
        ))

    return metrics


def classify_stability(score: float) -> str:
    if score >= 0.7:
        return "stable"
    elif score >= 0.4:
        return "transition"
    return "volatile"


# ---------------------------------------------------------------------------
# Phase-shift detection
# ---------------------------------------------------------------------------

def detect_phase_shifts(
    metrics: List[WindowMetrics],
    threshold: float = PHASE_SHIFT_THRESHOLD,
) -> List[PhaseShift]:
    if len(metrics) < 2:
        return []

    shifts: List[PhaseShift] = []
    for i in range(1, len(metrics)):
        prev = metrics[i - 1]
        curr = metrics[i]
        delta = abs(curr.stability_score - prev.stability_score)

        if delta >= threshold:
            from_phase = classify_stability(prev.stability_score)
            to_phase = classify_stability(curr.stability_score)
            if from_phase != to_phase:
                evidence = curr.provenance.get("event_ids", [])
                shifts.append(PhaseShift(
                    timestamp=curr.window_start,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    stability_before=prev.stability_score,
                    stability_after=curr.stability_score,
                    evidence_event_ids=evidence[:10],
                ))

    return shifts


# ---------------------------------------------------------------------------
# Flare vs noise extraction
# ---------------------------------------------------------------------------

def extract_flare_episodes(
    metrics: List[WindowMetrics],
    burstiness_threshold: float = FLARE_BURSTINESS_THRESHOLD,
) -> Tuple[List[FlareEpisode], float]:
    if not metrics:
        return [], 0.0

    counts = [m.event_count for m in metrics]
    mean_count = sum(counts) / len(counts) if counts else 0
    noise_floor = mean_count

    if mean_count == 0:
        return [], 0.0

    episodes: List[FlareEpisode] = []
    in_episode = False
    ep_start = ""
    ep_events: List[str] = []
    ep_peak = 0.0

    for m in metrics:
        burstiness = m.event_count / mean_count if mean_count > 0 else 0
        is_burst = burstiness >= burstiness_threshold and m.stability_score < 0.5

        if is_burst and not in_episode:
            in_episode = True
            ep_start = m.window_start
            ep_events = list(m.provenance.get("event_ids", []))
            ep_peak = burstiness
        elif is_burst and in_episode:
            ep_events.extend(m.provenance.get("event_ids", []))
            ep_peak = max(ep_peak, burstiness)
        elif not is_burst and in_episode:
            confidence = min(ep_peak / burstiness_threshold, 1.0)
            episodes.append(FlareEpisode(
                start=ep_start,
                end=m.window_start,
                confidence=round(confidence, 3),
                supporting_event_ids=ep_events[:20],
                peak_intensity=round(ep_peak, 3),
            ))
            in_episode = False
            ep_events = []

    if in_episode:
        confidence = min(ep_peak / burstiness_threshold, 1.0)
        episodes.append(FlareEpisode(
            start=ep_start,
            end=metrics[-1].window_end,
            confidence=round(confidence, 3),
            supporting_event_ids=ep_events[:20],
            peak_intensity=round(ep_peak, 3),
        ))

    return episodes, round(noise_floor, 2)


# ---------------------------------------------------------------------------
# Lagged precedence associations
# ---------------------------------------------------------------------------

def compute_precedence_edges(
    events: List[Dict[str, Any]],
    max_lag_days: int = 30,
    min_support: int = 2,
) -> List[PrecedenceEdge]:
    parsed: List[Tuple[datetime, str, Dict[str, Any]]] = []
    for e in events:
        ts = e.get("ts")
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        etype = (e.get("event_type") or "unknown").lower()
        parsed.append((ts, etype, e))

    parsed.sort(key=lambda x: x[0])

    lag_pairs: Dict[Tuple[str, str], List[float]] = {}
    for i, (ts_a, type_a, _) in enumerate(parsed):
        for j in range(i + 1, min(i + 50, len(parsed))):
            ts_b, type_b, _ = parsed[j]
            lag = (ts_b - ts_a).total_seconds() / 86400.0
            if lag > max_lag_days:
                break
            if type_a == type_b:
                continue
            key = (type_a, type_b)
            if key not in lag_pairs:
                lag_pairs[key] = []
            lag_pairs[key].append(lag)

    edges: List[PrecedenceEdge] = []
    for (from_t, to_t), lags in lag_pairs.items():
        if len(lags) < min_support:
            continue
        lags.sort()
        median_lag = lags[len(lags) // 2]
        confidence = min(len(lags) / 10.0, 1.0)
        edges.append(PrecedenceEdge(
            from_type=from_t,
            to_type=to_t,
            median_lag_days=round(median_lag, 1),
            support_count=len(lags),
            confidence=round(confidence, 3),
        ))

    edges.sort(key=lambda e: e.support_count, reverse=True)
    return edges[:20]


# ---------------------------------------------------------------------------
# Trajectory embedding (PCA-like 2D projection)
# ---------------------------------------------------------------------------

def compute_trajectory_points(
    vectors: List[WindowVector],
    metrics: List[WindowMetrics],
) -> List[TrajectoryPoint]:
    if not vectors or not metrics:
        return []

    all_types = set()
    for v in vectors:
        all_types.update(v.event_types.keys())
        all_types.update(v.edge_types.keys())
    type_list = sorted(all_types)

    if not type_list:
        return []

    feature_matrix: List[List[float]] = []
    for v in vectors:
        row = []
        for t in type_list:
            row.append(v.event_types.get(t, 0) + v.edge_types.get(t, 0))
        feature_matrix.append(row)

    n = len(feature_matrix)
    dim = len(type_list)
    means = [0.0] * dim
    for row in feature_matrix:
        for j in range(dim):
            means[j] += row[j]
    means = [m / n for m in means]

    centered = []
    for row in feature_matrix:
        centered.append([row[j] - means[j] for j in range(dim)])

    if dim >= 2:
        pc1 = [0.0] * dim
        pc2 = [0.0] * dim
        for j in range(dim):
            var = sum(r[j] ** 2 for r in centered)
            pc1[j] = var
        total_var = sum(pc1)
        if total_var > 0:
            pc1 = [v / total_var for v in pc1]
        else:
            pc1 = [1.0 / dim] * dim

        for j in range(dim):
            pc2[j] = (j / dim) * (1 - pc1[j])
        pc2_total = sum(abs(x) for x in pc2)
        if pc2_total > 0:
            pc2 = [x / pc2_total for x in pc2]
    else:
        pc1 = [1.0] * dim
        pc2 = [0.0] * dim

    points: List[TrajectoryPoint] = []
    for i, (v, m) in enumerate(zip(vectors, metrics)):
        x = sum(centered[i][j] * pc1[j] for j in range(dim))
        y = sum(centered[i][j] * pc2[j] for j in range(dim))
        points.append(TrajectoryPoint(
            timestamp=v.window_start,
            x=round(x, 4),
            y=round(y, 4),
            stability_class=classify_stability(m.stability_score),
            event_count=v.event_count,
        ))

    return points


# ---------------------------------------------------------------------------
# High-level: full analytics summary
# ---------------------------------------------------------------------------

def compute_analytics_summary(
    patient_id: str,
    events: List[Dict[str, Any]],
    connascence_edges: Optional[List[Dict[str, Any]]] = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    params: Optional[Dict[str, float]] = None,
) -> AnalyticsSummary:
    edges = connascence_edges or []
    vectors = build_windowed_vectors(events, edges, window_days)
    metrics = compute_window_metrics(vectors, params)
    phase_shifts = detect_phase_shifts(metrics)
    flare_episodes, noise_floor = extract_flare_episodes(metrics)

    span_days = 0
    if events:
        ts_list = []
        for e in events:
            ts = e.get("ts")
            if ts is None:
                continue
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_list.append(ts)
        if len(ts_list) >= 2:
            ts_list.sort()
            span_days = (ts_list[-1] - ts_list[0]).days

    return AnalyticsSummary(
        patient_id=patient_id,
        window_days=window_days,
        total_events=len(events),
        span_days=span_days,
        windows=metrics,
        phase_shifts=phase_shifts,
        flare_episodes=flare_episodes,
        noise_floor=noise_floor,
        params=params or STABILITY_PARAMS,
    )
