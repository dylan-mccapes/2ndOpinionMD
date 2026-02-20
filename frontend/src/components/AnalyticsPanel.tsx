import { useState, useEffect } from 'react';
import { apiFetch, authHeaders } from '../lib/api';

interface WindowMetric {
  window_start: string;
  window_end: string;
  drift: number;
  curvature: number;
  connascence_load: number;
  stability_score: number;
  event_count: number;
}

interface PhaseShift {
  timestamp: string;
  from_phase: string;
  to_phase: string;
  stability_before: number;
  stability_after: number;
  evidence_event_ids: string[];
}

interface FlareEpisode {
  start: string;
  end: string;
  confidence: number;
  peak_intensity: number;
  supporting_event_ids: string[];
}

interface PrecedenceEdge {
  from_type: string;
  to_type: string;
  median_lag_days: number;
  support_count: number;
  confidence: number;
}

interface AnalyticsSummaryResponse {
  patient_id: string;
  total_events: number;
  span_days: number;
  windows: WindowMetric[];
  phase_shifts: PhaseShift[];
  flare_episodes: FlareEpisode[];
  noise_floor: number;
  charts: Record<string, string>;
  disclaimer: string;
}

interface PrecedenceResponse {
  edges: PrecedenceEdge[];
  total_edges: number;
}

type ActiveChart = 'stability_band' | 'event_edge_intensity' | 'precedence_map' | 'terrain_trajectory' | 'flare_noise_panel';

const CHART_LABELS: Record<ActiveChart, string> = {
  stability_band: 'STABILITY BAND',
  event_edge_intensity: 'EVENT INTENSITY',
  precedence_map: 'PRECEDENCE MAP',
  terrain_trajectory: 'TERRAIN TRAJECTORY',
  flare_noise_panel: 'FLARE vs NOISE',
};

interface AnalyticsPanelProps {
  patientId: string;
  token: string;
}

export function AnalyticsPanel({ patientId, token }: AnalyticsPanelProps) {
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [precedence, setPrecedence] = useState<PrecedenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChart, setActiveChart] = useState<ActiveChart>('stability_band');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    if (!patientId || !token) return;

    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        const [summaryRes, precedenceRes] = await Promise.all([
          apiFetch<AnalyticsSummaryResponse>(
            `/api/timeline/${patientId}/analytics/summary?window_days=7`,
            { headers: authHeaders(token) },
          ),
          apiFetch<PrecedenceResponse>(
            `/api/timeline/${patientId}/analytics/precedence`,
            { headers: authHeaders(token) },
          ),
        ]);
        setSummary(summaryRes);
        setPrecedence(precedenceRes);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [patientId, token]);

  const handleExport = async () => {
    if (!patientId || !token) return;
    setExporting(true);
    setExportError('');
    try {
      const res = await apiFetch<Record<string, unknown>>(
        `/api/timeline/${patientId}/analytics/export`,
        {
          method: 'POST',
          headers: authHeaders(token),
        },
      );
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_${patientId}_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-blue)' }}>
          TIMELINE ANALYTICS
        </span>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Loading analytics...</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-blue)' }}>
          TIMELINE ANALYTICS
        </span>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {error || 'No timeline data available for this patient.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-blue)' }}>
            TIMELINE ANALYTICS
          </span>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-3 py-1 rounded text-xs font-mono font-bold"
            style={{
              backgroundColor: 'var(--accent-blue)',
              color: '#fff',
              opacity: exporting ? 0.5 : 1,
            }}
          >
            {exporting ? 'EXPORTING...' : 'EXPORT PACKAGE'}
          </button>
        </div>

        {exportError && (
          <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent-red)' }}>{exportError}</p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Events</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {summary.total_events}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Span</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {summary.span_days}d
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Phase Shifts</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--accent-yellow)' }}>
              {summary.phase_shifts.length}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Flare Ep.</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--accent-red)' }}>
              {summary.flare_episodes.length}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Noise Floor</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {summary.noise_floor}
            </span>
          </div>
        </div>

        <div
          className="flex gap-1 mb-3 border-b overflow-x-auto"
          style={{ borderColor: 'var(--border-color)' }}
        >
          {(Object.keys(CHART_LABELS) as ActiveChart[]).map((key) => (
            <button
              key={key}
              onClick={() => setActiveChart(key)}
              className="px-2 py-1.5 text-xs font-mono font-bold whitespace-nowrap"
              style={{
                color: activeChart === key ? 'var(--accent-blue)' : 'var(--text-secondary)',
                borderBottom: activeChart === key ? '2px solid var(--accent-blue)' : '2px solid transparent',
                background: 'none',
                border: 'none',
                borderBottomWidth: '2px',
                borderBottomStyle: 'solid',
                borderBottomColor: activeChart === key ? 'var(--accent-blue)' : 'transparent',
                cursor: 'pointer',
              }}
            >
              {CHART_LABELS[key]}
            </button>
          ))}
        </div>

        {summary.charts[activeChart] && (
          <img
            src={`data:image/png;base64,${summary.charts[activeChart]}`}
            alt={CHART_LABELS[activeChart]}
            className="w-full rounded mb-3"
          />
        )}
      </div>

      {summary.phase_shifts.length > 0 && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-yellow)' }}>
            PHASE SHIFTS
          </span>
          <div className="space-y-2">
            {summary.phase_shifts.map((ps, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <div>
                  <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                    {ps.from_phase.toUpperCase()} → {ps.to_phase.toUpperCase()}
                  </span>
                  <span className="text-xs font-mono ml-2" style={{ color: 'var(--text-muted)' }}>
                    {new Date(ps.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <div className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                  S: {ps.stability_before.toFixed(2)} → {ps.stability_after.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary.flare_episodes.length > 0 && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-red)' }}>
            FLARE EPISODES
          </span>
          <div className="space-y-2">
            {summary.flare_episodes.map((fe, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <div>
                  <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                    {new Date(fe.start).toLocaleDateString()} — {new Date(fe.end).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-red)' }}>
                    {(fe.confidence * 100).toFixed(0)}% confidence
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    peak: {fe.peak_intensity.toFixed(1)}x
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {precedence && precedence.edges.length > 0 && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-blue)' }}>
            LAGGED ASSOCIATIONS
          </span>
          <p className="text-xs font-mono mb-2" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
            Predictive associations only — not causal claims.
          </p>
          <div className="space-y-1">
            {precedence.edges.slice(0, 10).map((edge, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
                  {edge.from_type.toUpperCase()} → {edge.to_type.toUpperCase()}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
                    ~{edge.median_lag_days}d lag
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    n={edge.support_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs font-mono" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
        {summary.disclaimer}
      </p>
    </div>
  );
}
