"""
Graph-based figure generation for EoHD detective reports.

Produces matplotlib charts from PatientTimelineVision graphs.
Each figure function returns (png_bytes, caption_text) so the caller
can embed in PDFs or stream as base64.

Andras: replace or extend these with your analytics modules.
"""
from __future__ import annotations

import io
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np

from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.utils.parse_date import parse_clinical_date

logger = logging.getLogger(__name__)

_PALETTE = {
    "diagnosis": "#e63946",
    "medication": "#457b9d",
    "lab": "#2a9d8f",
    "procedure": "#e9c46a",
    "symptom": "#f4a261",
    "visit": "#a8dadc",
    "note": "#6c757d",
    "imaging": "#9b5de5",
    "vital": "#00bbf9",
    "plan": "#fee440",
}

_CLINICAL_TYPES = [
    "diagnosis", "medication", "lab", "procedure",
    "symptom", "visit", "note", "imaging",
]


def _color(etype: str) -> str:
    return _PALETTE.get(etype, "#adb5bd")


def _naive(dt: datetime) -> datetime:
    """Strip timezone info for consistent comparisons."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _parse_events(vision: PatientTimelineVision) -> List[Tuple[datetime, str, str]]:
    """Return (datetime, event_type, event_id) for all parseable events."""
    parsed = []
    for e in vision.events.values():
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt:
            parsed.append((_naive(dt), e.event_type, e.event_id))
    parsed.sort(key=lambda x: x[0])
    return parsed


# ── Figure 1: Clinical Event Density Heatmap ────────────────────────────

def fig_event_density_heatmap(
    vision: PatientTimelineVision,
) -> Tuple[bytes, str]:
    """Monthly event counts by clinical type — heatmap style."""
    parsed = _parse_events(vision)
    if not parsed:
        return b"", "No timestamped events available for density heatmap."

    by_month_type: Dict[str, Counter] = defaultdict(Counter)
    for dt, etype, _ in parsed:
        if etype in _CLINICAL_TYPES:
            by_month_type[dt.strftime("%Y-%m")][etype] += 1

    months = sorted(by_month_type.keys())
    if len(months) < 2:
        return b"", "Insufficient temporal range for density heatmap."

    types_present = [t for t in _CLINICAL_TYPES if any(by_month_type[m].get(t, 0) for m in months)]
    if not types_present:
        return b"", "No clinical events found for heatmap."

    # Downsample if more than 60 months: group into quarters
    if len(months) > 60:
        quarter_map: Dict[str, Counter] = defaultdict(Counter)
        for m in months:
            y, mo = m.split("-")
            qtr = f"{y}-Q{(int(mo)-1)//3+1}"
            for t in types_present:
                quarter_map[qtr][t] += by_month_type[m].get(t, 0)
        months = sorted(quarter_map.keys())
        by_month_type = quarter_map

    matrix = np.zeros((len(types_present), len(months)))
    for j, m in enumerate(months):
        for i, t in enumerate(types_present):
            matrix[i, j] = by_month_type[m].get(t, 0)

    fig, ax = plt.subplots(figsize=(min(14, max(8, len(months) * 0.18)), max(3, len(types_present) * 0.6)))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax.set_yticks(range(len(types_present)))
    ax.set_yticklabels([t.title() for t in types_present], fontsize=9)

    tick_step = max(1, len(months) // 20)
    ax.set_xticks(range(0, len(months), tick_step))
    ax.set_xticklabels([months[i] for i in range(0, len(months), tick_step)], rotation=45, ha="right", fontsize=7)
    ax.set_xlabel("Time Period", fontsize=9)
    ax.set_title("Clinical Event Density by Type", fontsize=12, fontweight="bold", pad=10)
    fig.colorbar(im, ax=ax, label="Event Count", shrink=0.8)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    # Caption
    peak_month = max(months, key=lambda m: sum(by_month_type[m].values()))
    peak_count = sum(by_month_type[peak_month].values())
    total = int(matrix.sum())
    caption = (
        f"Figure shows clinical event density across {len(months)} time periods "
        f"and {len(types_present)} event types ({total:,} events total). "
        f"Peak clinical activity occurred in {peak_month} ({peak_count} events)."
    )
    return buf.read(), caption


# ── Figure 2: Connascence Network Intensity ──────────────────────────────

def fig_connascence_chord(
    vision: PatientTimelineVision,
) -> Tuple[bytes, str]:
    """Edge density between event types — matrix heatmap of coupling strength."""
    type_pair_counts: Counter = Counter()
    type_to_events: Dict[str, int] = Counter()

    for e in vision.events.values():
        type_to_events[e.event_type] += 1
        for kind, targets in e.connascence.items():
            for tid in targets:
                target_ev = vision.events.get(tid)
                if target_ev:
                    pair = tuple(sorted([e.event_type, target_ev.event_type]))
                    type_pair_counts[pair] += 1

    if not type_pair_counts:
        return b"", "No connascence edges found for network analysis."

    types_with_edges = sorted(set(
        t for pair in type_pair_counts for t in pair
        if t in _CLINICAL_TYPES
    ))
    if len(types_with_edges) < 2:
        return b"", "Insufficient event type diversity for network chart."

    n = len(types_with_edges)
    matrix = np.zeros((n, n))
    for (t1, t2), count in type_pair_counts.items():
        if t1 in types_with_edges and t2 in types_with_edges:
            i, j = types_with_edges.index(t1), types_with_edges.index(t2)
            matrix[i, j] += count
            matrix[j, i] += count

    # Log scale for better visibility
    log_matrix = np.log1p(matrix)

    fig, ax = plt.subplots(figsize=(max(5, n * 0.8), max(4, n * 0.7)))
    im = ax.imshow(log_matrix, cmap="PuBu", interpolation="nearest")
    ax.set_xticks(range(n))
    ax.set_xticklabels([t.title() for t in types_with_edges], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels([t.title() for t in types_with_edges], fontsize=9)

    for i in range(n):
        for j in range(n):
            val = int(matrix[i, j])
            if val > 0:
                color = "white" if log_matrix[i, j] > log_matrix.max() * 0.6 else "black"
                ax.text(j, i, f"{val:,}", ha="center", va="center", fontsize=7, color=color)

    ax.set_title("Connascence Edge Density Between Event Types", fontsize=12, fontweight="bold", pad=10)
    fig.colorbar(im, ax=ax, label="log(1 + edge count)", shrink=0.8)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    top3 = type_pair_counts.most_common(3)
    top_desc = "; ".join(f"{t1}↔{t2} ({c:,} edges)" for (t1, t2), c in top3)
    total_edges = sum(type_pair_counts.values())
    caption = (
        f"Cross-type connascence matrix showing {total_edges:,} total edges "
        f"across {n} event types. Strongest coupling: {top_desc}. "
        f"High coupling indicates clinical domains that co-occur or influence each other."
    )
    return buf.read(), caption


# ── Figure 3: Temporal Coverage & Gaps ──────────────────────────────────

def fig_temporal_coverage(
    vision: PatientTimelineVision,
    gap_threshold_days: int = 90,
) -> Tuple[bytes, str]:
    """Per-type timeline coverage bars with gap markers."""
    cutoff = datetime(2000, 1, 1)
    by_type: Dict[str, List[datetime]] = defaultdict(list)
    for e in vision.events.values():
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt:
            dt = _naive(dt)
            if dt >= cutoff and e.event_type in _CLINICAL_TYPES:
                by_type[e.event_type].append(dt)

    for v in by_type.values():
        v.sort()

    types_present = [t for t in _CLINICAL_TYPES if by_type.get(t)]
    if len(types_present) < 2:
        return b"", "Insufficient event types for temporal coverage chart."

    fig, ax = plt.subplots(figsize=(12, max(3, len(types_present) * 0.5 + 1)))
    gap_annotations = []

    for i, etype in enumerate(types_present):
        dates = by_type[etype]
        color = _color(etype)

        if len(dates) >= 2:
            ax.barh(
                i, (dates[-1] - dates[0]).days,
                left=mdates.date2num(dates[0]),
                height=0.5, color=color, alpha=0.4,
                edgecolor=color, linewidth=0.5,
            )

        ax.scatter(
            [mdates.date2num(d) for d in dates],
            [i] * len(dates),
            s=3, color=color, alpha=0.6, zorder=3,
        )

        for j in range(1, len(dates)):
            delta = (dates[j] - dates[j - 1]).days
            if delta >= gap_threshold_days:
                mid = mdates.date2num(dates[j - 1]) + delta / 2
                ax.plot(
                    [mdates.date2num(dates[j - 1]), mdates.date2num(dates[j])],
                    [i, i], color="red", linewidth=1.5, linestyle="--", alpha=0.7,
                )
                gap_annotations.append((etype, dates[j - 1], dates[j], delta))

    ax.set_yticks(range(len(types_present)))
    ax.set_yticklabels([t.title() for t in types_present], fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.set_xlabel("Date", fontsize=9)
    ax.set_title(
        f"Temporal Coverage by Event Type (red dashes = gaps ≥{gap_threshold_days}d)",
        fontsize=12, fontweight="bold", pad=10,
    )
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    n_gaps = len(gap_annotations)
    if gap_annotations:
        longest = max(gap_annotations, key=lambda g: g[3])
        gap_detail = (
            f"Identified {n_gaps} data gaps ≥{gap_threshold_days} days. "
            f"Longest gap: {longest[3]} days in {longest[0]} "
            f"({longest[1].strftime('%Y-%m-%d')} to {longest[2].strftime('%Y-%m-%d')})."
        )
    else:
        gap_detail = f"No data gaps ≥{gap_threshold_days} days detected."

    caption = (
        f"Temporal coverage for {len(types_present)} event types. "
        f"Colored bars show date range; dots show individual events. "
        f"{gap_detail}"
    )
    return buf.read(), caption


# ── Figure 4: Medication Burden Over Time ────────────────────────────────

def fig_medication_burden(
    vision: PatientTimelineVision,
) -> Tuple[bytes, str]:
    """Rolling medication event frequency — proxy for treatment intensity."""
    med_dates: List[datetime] = []
    drug_mentions: Counter = Counter()

    for e in vision.events.values():
        if e.event_type != "medication":
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt:
            med_dates.append(_naive(dt))
        dn = e.annotations.get("drug_name", "")
        if dn:
            drug_mentions[dn.lower().split()[0]] += 1

    if len(med_dates) < 5:
        return b"", "Insufficient medication events for burden analysis."

    med_dates.sort()

    # Monthly bin counts
    month_counts: Counter = Counter()
    for dt in med_dates:
        month_counts[dt.strftime("%Y-%m")] += 1

    months = sorted(month_counts.keys())
    counts = [month_counts[m] for m in months]
    month_dates = [datetime.strptime(m, "%Y-%m") for m in months]

    # Rolling average (3-month window)
    window = min(3, len(counts))
    rolling = np.convolve(counts, np.ones(window) / window, mode="same")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [3, 1]})

    ax1.bar(month_dates, counts, width=25, color=_color("medication"), alpha=0.5, label="Monthly count")
    ax1.plot(month_dates, rolling, color="#c1121f", linewidth=2, label=f"{window}-mo rolling avg")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.set_xlabel("Date", fontsize=9)
    ax1.set_ylabel("Medication Events", fontsize=9)
    ax1.set_title("Medication Burden Over Time", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    # Top drugs bar chart
    top_drugs = drug_mentions.most_common(10)
    if top_drugs:
        names = [d[0][:15] for d in top_drugs]
        vals = [d[1] for d in top_drugs]
        colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(names)))
        ax2.barh(range(len(names)), vals, color=colors)
        ax2.set_yticks(range(len(names)))
        ax2.set_yticklabels(names, fontsize=8)
        ax2.set_xlabel("Mentions", fontsize=9)
        ax2.set_title("Top Medications", fontsize=10, fontweight="bold")
        ax2.invert_yaxis()
    else:
        ax2.text(0.5, 0.5, "No drug names\nextracted", ha="center", va="center", fontsize=10, color="#888")
        ax2.set_title("Top Medications", fontsize=10, fontweight="bold")

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    peak_month = max(months, key=lambda m: month_counts[m])
    peak_val = month_counts[peak_month]
    top_drug_str = ", ".join(d[0] for d in top_drugs[:3]) if top_drugs else "none extracted"
    caption = (
        f"Medication burden across {len(months)} months ({len(med_dates)} total events). "
        f"Peak: {peak_val} events in {peak_month}. "
        f"Most frequent medications: {top_drug_str}. "
        f"Rising burden may indicate treatment escalation or polypharmacy."
    )
    return buf.read(), caption


# ── Figure 5: Diagnostic Arc & Inflection Points ─────────────────────────

def fig_diagnostic_arc(
    vision: PatientTimelineVision,
) -> Tuple[bytes, str]:
    """Cumulative diagnosis count + all-type event rate showing inflection points."""
    cutoff = datetime(2000, 1, 1)
    parsed = [(dt, et, eid) for dt, et, eid in _parse_events(vision) if dt >= cutoff]
    if len(parsed) < 10:
        return b"", "Insufficient timestamped events for diagnostic arc."

    dx_dates = sorted(dt for dt, et, _ in parsed if et == "diagnosis")
    all_dates = sorted(dt for dt, _, _ in parsed)

    if not all_dates:
        return b"", "No dated events for arc chart."

    # Monthly all-event rate
    month_counts: Counter = Counter()
    for dt in all_dates:
        month_counts[dt.strftime("%Y-%m")] += 1

    months = sorted(month_counts.keys())
    month_dates_plot = [datetime.strptime(m, "%Y-%m") for m in months]
    rates = [month_counts[m] for m in months]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()

    ax1.fill_between(month_dates_plot, rates, alpha=0.2, color="#2a9d8f")
    ax1.plot(month_dates_plot, rates, color="#2a9d8f", linewidth=1.2, label="All events/month")
    ax1.set_ylabel("Events per Month (all types)", fontsize=9, color="#2a9d8f")
    ax1.tick_params(axis="y", labelcolor="#2a9d8f")

    if dx_dates:
        cumulative = list(range(1, len(dx_dates) + 1))
        ax2.step(dx_dates, cumulative, where="post", color="#e63946", linewidth=2, label="Cumulative diagnoses")
        ax2.set_ylabel("Cumulative Diagnoses", fontsize=9, color="#e63946")
        ax2.tick_params(axis="y", labelcolor="#e63946")

        # Mark inflection points: months with ≥3 new diagnoses
        dx_month_counts: Counter = Counter()
        for dt in dx_dates:
            dx_month_counts[dt.strftime("%Y-%m")] += 1
        inflections = [(m, c) for m, c in dx_month_counts.items() if c >= 3]
        for m, c in inflections:
            idate = datetime.strptime(m, "%Y-%m")
            ax1.axvline(idate, color="#e63946", alpha=0.3, linestyle=":", linewidth=1.5)
            ax1.annotate(
                f"+{c} dx", xy=(idate, max(rates) * 0.9),
                fontsize=7, color="#e63946", ha="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#e63946", alpha=0.7),
            )

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.set_xlabel("Date", fontsize=9)
    ax1.set_title("Diagnostic Arc: Event Rate & Cumulative Diagnoses", fontsize=12, fontweight="bold", pad=10)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    ax1.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    n_dx = len(dx_dates)
    span_years = (all_dates[-1] - all_dates[0]).days / 365.25 if len(all_dates) >= 2 else 0
    dx_month_counts_all: Counter = Counter()
    for dt in dx_dates:
        dx_month_counts_all[dt.strftime("%Y-%m")] += 1
    inflections = [(m, c) for m, c in dx_month_counts_all.items() if c >= 3]
    caption = (
        f"Clinical trajectory over {span_years:.1f} years. "
        f"{n_dx} diagnoses accumulated, with {len(inflections)} inflection point(s) "
        f"where ≥3 diagnoses appeared in a single month. "
        f"Peaks in event rate correlate with periods of active workup or clinical escalation."
    )
    return buf.read(), caption


# ── Run all figures ─────────────────────────────────────────────────────

ALL_FIGURES = [
    ("Clinical Event Density", fig_event_density_heatmap),
    ("Connascence Network", fig_connascence_chord),
    ("Temporal Coverage & Gaps", fig_temporal_coverage),
    ("Medication Burden", fig_medication_burden),
    ("Diagnostic Arc", fig_diagnostic_arc),
]


def generate_all_figures(
    vision: PatientTimelineVision,
) -> List[Dict[str, Any]]:
    """Run all figure generators. Returns list of dicts with keys:
        title, png_bytes, caption, error
    Figures that fail or have no data are included with empty png_bytes.
    """
    results: List[Dict[str, Any]] = []
    for title, func in ALL_FIGURES:
        try:
            png_bytes, caption = func(vision)
            results.append({
                "title": title,
                "png_bytes": png_bytes,
                "caption": caption,
                "error": None,
            })
        except Exception as exc:
            logger.warning("Figure generation failed: %s — %s", title, exc, exc_info=True)
            results.append({
                "title": title,
                "png_bytes": b"",
                "caption": f"Figure generation failed: {exc}",
                "error": str(exc),
            })
    return results
