"""
Timeline Chart Renderer — Phase 6b

Server-side Matplotlib (Agg backend) chart generation for deterministic export.
Five chart types:
  1. stability_band.png
  2. event_edge_intensity.png
  3. precedence_map.png
  4. terrain_trajectory.png
  5. flare_noise_panel.png

All charts include patient_id, date range, metric definitions footer,
and "decision support, not diagnosis" watermark.
"""

from __future__ import annotations

import io
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch

from server.timeline.analytics import (
    WindowMetrics,
    PhaseShift,
    FlareEpisode,
    PrecedenceEdge,
    TrajectoryPoint,
    classify_stability,
)

WATERMARK = "Decision support only — not a diagnosis"
COLORS = {
    "stable": "#22c55e",
    "transition": "#eab308",
    "volatile": "#ef4444",
}


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _parse_ts(ts_str: str) -> Optional[datetime]:
    from server.utils.parse_date import parse_clinical_date
    return parse_clinical_date(ts_str)


def _add_footer(ax: plt.Axes, patient_id: str, date_range: str) -> None:
    ax.annotate(
        f"Patient: {patient_id}  |  {date_range}  |  {WATERMARK}",
        xy=(0.5, -0.12),
        xycoords="axes fraction",
        ha="center",
        fontsize=6,
        color="#888888",
        style="italic",
    )


# ---------------------------------------------------------------------------
# 1. Stability Band
# ---------------------------------------------------------------------------

def render_stability_band(
    metrics: List[WindowMetrics],
    phase_shifts: List[PhaseShift],
    patient_id: str,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    dates = []
    scores = []
    for m in metrics:
        dt = _parse_ts(m.window_start)
        if dt:
            dates.append(dt)
            scores.append(m.stability_score)

    if not dates:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#94a3b8")
        return _fig_to_base64(fig)

    ax.fill_between(dates, 0, 0.4, alpha=0.15, color=COLORS["volatile"], label="Volatile")
    ax.fill_between(dates, 0.4, 0.7, alpha=0.15, color=COLORS["transition"], label="Transition")
    ax.fill_between(dates, 0.7, 1.0, alpha=0.15, color=COLORS["stable"], label="Stable")

    colors = [COLORS[classify_stability(s)] for s in scores]
    ax.plot(dates, scores, color="#60a5fa", linewidth=1.5, zorder=3)
    ax.scatter(dates, scores, c=colors, s=20, zorder=4, edgecolors="none")

    for ps in phase_shifts:
        ps_dt = _parse_ts(ps.timestamp)
        if ps_dt:
            ax.axvline(ps_dt, color="#f97316", linewidth=1, linestyle="--", alpha=0.7)
            ax.annotate(
                f"{ps.from_phase}\u2192{ps.to_phase}",
                xy=(ps_dt, 0.95),
                fontsize=6,
                color="#f97316",
                ha="center",
            )

    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Stability Score (S\u209c)", color="#94a3b8", fontsize=8)
    ax.set_title("STABILITY BAND TIMELINE", color="#e2e8f0", fontsize=10, fontweight="bold")
    ax.tick_params(colors="#64748b", labelsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(loc="upper right", fontsize=6, facecolor="#1e293b", edgecolor="#334155", labelcolor="#94a3b8")

    date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}" if dates else ""
    _add_footer(ax, patient_id, date_range)

    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 2. Event / Edge Intensity
# ---------------------------------------------------------------------------

def render_event_edge_intensity(
    metrics: List[WindowMetrics],
    patient_id: str,
) -> str:
    fig, ax1 = plt.subplots(figsize=(10, 4))
    fig.set_facecolor("#0f172a")
    ax1.set_facecolor("#1e293b")

    dates = []
    event_counts = []
    conn_loads = []
    for m in metrics:
        dt = _parse_ts(m.window_start)
        if dt:
            dates.append(dt)
            event_counts.append(m.event_count)
            conn_loads.append(m.connascence_load)

    if not dates:
        ax1.text(0.5, 0.5, "No data", transform=ax1.transAxes, ha="center", color="#94a3b8")
        return _fig_to_base64(fig)

    ax1.bar(dates, event_counts, width=5, color="#60a5fa", alpha=0.6, label="Event Count")
    ax1.set_ylabel("Event Count", color="#60a5fa", fontsize=8)
    ax1.tick_params(axis="y", colors="#60a5fa", labelsize=7)
    ax1.tick_params(axis="x", colors="#64748b", labelsize=7)

    ax2 = ax1.twinx()
    ax2.plot(dates, conn_loads, color="#f97316", linewidth=1.5, marker="o", markersize=3, label="Connascence Load")
    ax2.set_ylabel("Connascence Load (L\u209c)", color="#f97316", fontsize=8)
    ax2.tick_params(axis="y", colors="#f97316", labelsize=7)

    ax1.set_title("EVENT & EDGE INTENSITY", color="#e2e8f0", fontsize=10, fontweight="bold")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=6,
               facecolor="#1e293b", edgecolor="#334155", labelcolor="#94a3b8")

    date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}" if dates else ""
    _add_footer(ax1, patient_id, date_range)

    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 3. Precedence Map
# ---------------------------------------------------------------------------

def render_precedence_map(
    edges: List[PrecedenceEdge],
    patient_id: str,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    if not edges:
        ax.text(0.5, 0.5, "No precedence data", transform=ax.transAxes, ha="center", color="#94a3b8")
        ax.set_title("PRECEDENCE MAP", color="#e2e8f0", fontsize=10, fontweight="bold")
        return _fig_to_base64(fig)

    top_edges = edges[:12]

    node_set: set = set()
    for e in top_edges:
        node_set.add(e.from_type)
        node_set.add(e.to_type)
    nodes = sorted(node_set)

    import math as _math
    positions: Dict[str, tuple] = {}
    n = len(nodes)
    for i, node in enumerate(nodes):
        angle = 2 * _math.pi * i / max(n, 1)
        positions[node] = (0.5 + 0.35 * _math.cos(angle), 0.5 + 0.35 * _math.sin(angle))

    for node, (x, y) in positions.items():
        ax.scatter(x, y, s=200, color="#3b82f6", zorder=5, edgecolors="#60a5fa", linewidths=1)
        ax.annotate(node.upper(), xy=(x, y), ha="center", va="center", fontsize=6,
                    color="#e2e8f0", fontweight="bold", zorder=6)

    for e in top_edges:
        x1, y1 = positions[e.from_type]
        x2, y2 = positions[e.to_type]
        alpha = min(e.confidence + 0.3, 1.0)
        lw = 0.5 + e.support_count * 0.3
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", color="#f97316", lw=min(lw, 3), alpha=alpha),
        )
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.annotate(
            f"{e.median_lag_days:.0f}d (n={e.support_count})",
            xy=(mid_x, mid_y),
            fontsize=5,
            color="#94a3b8",
            ha="center",
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("PRECEDENCE MAP (Predictive Associations)", color="#e2e8f0", fontsize=10, fontweight="bold")
    ax.axis("off")

    _add_footer(ax, patient_id, "All-time")

    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 4. Terrain Trajectory
# ---------------------------------------------------------------------------

def render_terrain_trajectory(
    points: List[TrajectoryPoint],
    patient_id: str,
) -> str:
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    if not points:
        ax.text(0.5, 0.5, "No trajectory data", transform=ax.transAxes, ha="center", color="#94a3b8")
        ax.set_title("TERRAIN TRAJECTORY", color="#e2e8f0", fontsize=10, fontweight="bold")
        return _fig_to_base64(fig)

    xs = [p.x for p in points]
    ys = [p.y for p in points]
    colors = [COLORS.get(p.stability_class, "#64748b") for p in points]
    sizes = [max(20, p.event_count * 8) for p in points]

    ax.plot(xs, ys, color="#475569", linewidth=0.8, zorder=2, linestyle="--")
    ax.scatter(xs, ys, c=colors, s=sizes, zorder=3, edgecolors="none", alpha=0.8)

    if points:
        ax.annotate("START", xy=(xs[0], ys[0]), fontsize=6, color="#22c55e",
                     xytext=(5, 5), textcoords="offset points")
        ax.annotate("NOW", xy=(xs[-1], ys[-1]), fontsize=6, color="#ef4444",
                     xytext=(5, 5), textcoords="offset points")

    total_dist = sum(
        ((xs[i] - xs[i-1])**2 + (ys[i] - ys[i-1])**2)**0.5
        for i in range(1, len(xs))
    )

    ax.set_xlabel("PC1", color="#94a3b8", fontsize=8)
    ax.set_ylabel("PC2", color="#94a3b8", fontsize=8)
    ax.set_title(
        f"TERRAIN TRAJECTORY  |  Distance: {total_dist:.2f}",
        color="#e2e8f0", fontsize=10, fontweight="bold",
    )
    ax.tick_params(colors="#64748b", labelsize=7)

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["stable"], markersize=8, label="Stable"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["transition"], markersize=8, label="Transition"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["volatile"], markersize=8, label="Volatile"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=6,
              facecolor="#1e293b", edgecolor="#334155", labelcolor="#94a3b8")

    dates = [p.timestamp for p in points]
    date_range = ""
    if dates:
        d0 = _parse_ts(dates[0])
        d1 = _parse_ts(dates[-1])
        if d0 and d1:
            date_range = f"{d0.strftime('%Y-%m-%d')} to {d1.strftime('%Y-%m-%d')}"
    _add_footer(ax, patient_id, date_range)

    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 5. Flare / Noise Panel
# ---------------------------------------------------------------------------

def render_flare_noise_panel(
    metrics: List[WindowMetrics],
    flare_episodes: List[FlareEpisode],
    noise_floor: float,
    patient_id: str,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")

    dates = []
    counts = []
    for m in metrics:
        dt = _parse_ts(m.window_start)
        if dt:
            dates.append(dt)
            counts.append(m.event_count)

    if not dates:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", color="#94a3b8")
        return _fig_to_base64(fig)

    ax.bar(dates, counts, width=5, color="#60a5fa", alpha=0.5, label="Event Intensity")
    ax.axhline(noise_floor, color="#64748b", linewidth=1, linestyle=":", label=f"Noise Floor ({noise_floor:.1f})")

    for ep in flare_episodes:
        ep_start = _parse_ts(ep.start)
        ep_end = _parse_ts(ep.end)
        if ep_start and ep_end:
            ax.axvspan(ep_start, ep_end, alpha=0.2, color="#ef4444")
            mid = ep_start + (ep_end - ep_start) / 2
            ax.annotate(
                f"FLARE ({ep.confidence:.0%})",
                xy=(mid, max(counts) * 0.9 if counts else 1),
                fontsize=6,
                color="#ef4444",
                ha="center",
                fontweight="bold",
            )

    ax.set_ylabel("Event Intensity", color="#94a3b8", fontsize=8)
    ax.set_title("FLARE vs NOISE", color="#e2e8f0", fontsize=10, fontweight="bold")
    ax.tick_params(colors="#64748b", labelsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(loc="upper right", fontsize=6, facecolor="#1e293b", edgecolor="#334155", labelcolor="#94a3b8")

    date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}" if dates else ""
    _add_footer(ax, patient_id, date_range)

    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Full chart set
# ---------------------------------------------------------------------------

def render_all_charts(
    metrics: List[WindowMetrics],
    phase_shifts: List[PhaseShift],
    flare_episodes: List[FlareEpisode],
    noise_floor: float,
    precedence_edges: List[PrecedenceEdge],
    trajectory_points: List[TrajectoryPoint],
    patient_id: str,
) -> Dict[str, str]:
    return {
        "stability_band": render_stability_band(metrics, phase_shifts, patient_id),
        "event_edge_intensity": render_event_edge_intensity(metrics, patient_id),
        "precedence_map": render_precedence_map(precedence_edges, patient_id),
        "terrain_trajectory": render_terrain_trajectory(trajectory_points, patient_id),
        "flare_noise_panel": render_flare_noise_panel(metrics, flare_episodes, noise_floor, patient_id),
    }
