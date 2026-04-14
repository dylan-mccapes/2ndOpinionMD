import { useState, useEffect } from 'react';
import { apiFetch, authHeaders } from '../lib/api';
import { Card, SectionLabel, DS, InlineMessage } from '../lib/ui';

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

  const asNum = (value: unknown, fallback = 0): number => {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  };
  const asLabel = (value: unknown, fallback = 'UNKNOWN'): string => {
    const s = String(value ?? '').trim();
    return s ? s.toUpperCase() : fallback;
  };

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
      <Card style={{ padding: DS.pad.card }}>
        <SectionLabel style={{ color: 'var(--accent-blue)', marginBottom: DS.mb.sm }}>
          TIMELINE ANALYTICS
        </SectionLabel>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Loading analytics...</p>
      </Card>
    );
  }

  if (error || !summary) {
    return (
      <Card style={{ padding: DS.pad.card }}>
        <SectionLabel style={{ color: 'var(--accent-blue)', marginBottom: DS.mb.sm }}>
          TIMELINE ANALYTICS
        </SectionLabel>
        <InlineMessage>
          {error || 'No timeline data available for this patient.'}
        </InlineMessage>
      </Card>
    );
  }

  const safePhaseShifts = Array.isArray(summary.phase_shifts) ? summary.phase_shifts : [];
  const safeFlareEpisodes = Array.isArray(summary.flare_episodes) ? summary.flare_episodes : [];
  const safeCharts = summary.charts && typeof summary.charts === 'object' ? summary.charts : {};
  const safePrecedenceEdges = precedence && Array.isArray(precedence.edges) ? precedence.edges : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.xl }}>
      <Card style={{ padding: DS.pad.card }}>
        <div className="flex items-center justify-between" style={{ marginBottom: DS.mb.md }}>
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
          <InlineMessage variant="error" style={{ marginBottom: DS.mb.sm }}>{exportError}</InlineMessage>
        )}

        <div className="grid grid-cols-2 md:grid-cols-5" style={{ gap: DS.gap.md, marginBottom: DS.mb.lg }}>
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
              {safePhaseShifts.length}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Flare Ep.</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--accent-red)' }}>
              {safeFlareEpisodes.length}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Noise Floor</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {asNum(summary.noise_floor, 0)}
            </span>
          </div>
        </div>

        <div className="flex border-b overflow-x-auto" style={{ borderColor: 'var(--border-color)', gap: DS.gap.xs, marginBottom: DS.mb.md }}>
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

        {safeCharts[activeChart] && (
          <img
            src={`data:image/png;base64,${safeCharts[activeChart]}`}
            alt={CHART_LABELS[activeChart]}
            className="w-full rounded"
            style={{ marginBottom: DS.mb.sm }}
          />
        )}
      </Card>

      {safePhaseShifts.length > 0 && (
        <Card style={{ padding: DS.pad.card }}>
          <SectionLabel style={{ color: 'var(--accent-yellow)', marginBottom: DS.mb.sm }}>
            PHASE SHIFTS
          </SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.md }}>
            {safePhaseShifts.map((ps, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <div>
                  <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                    {asLabel(ps.from_phase)} → {asLabel(ps.to_phase)}
                  </span>
                  <span className="text-xs font-mono ml-2" style={{ color: 'var(--text-muted)' }}>
                    {new Date(ps.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <div className="text-xs font-mono" style={{ color: 'var(--text-secondary)', marginLeft: DS.mb.sm }}>
                  S: {asNum(ps.stability_before).toFixed(2)} → {asNum(ps.stability_after).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {safeFlareEpisodes.length > 0 && (
        <Card style={{ padding: DS.pad.card }}>
          <SectionLabel style={{ color: 'var(--accent-red)', marginBottom: DS.mb.sm }}>
            FLARE EPISODES
          </SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.md }}>
            {safeFlareEpisodes.map((fe, idx) => (
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
                <div className="flex items-center" style={{ gap: DS.gap.lg }}>
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-red)' }}>
                    {(asNum(fe.confidence) * 100).toFixed(0)}% confidence
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    peak: {asNum(fe.peak_intensity).toFixed(1)}x
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {safePrecedenceEdges.length > 0 && (
        <Card style={{ padding: DS.pad.card }}>
          <SectionLabel style={{ color: 'var(--accent-blue)', marginBottom: DS.mb.sm }}>
            LAGGED ASSOCIATIONS
          </SectionLabel>
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: DS.mb.sm }}>
            Predictive associations only — not causal claims.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.sm }}>
            {safePrecedenceEdges.slice(0, 10).map((edge, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
                  {asLabel(edge.from_type)} → {asLabel(edge.to_type)}
                </span>
                <div className="flex items-center" style={{ gap: DS.gap.lg }}>
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
                    ~{asNum(edge.median_lag_days)}d lag
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    n={asNum(edge.support_count)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <p className="text-xs font-mono" style={{ color: 'var(--text-muted)', fontStyle: 'italic', padding: '0 0.25rem' }}>
        {summary.disclaimer}
      </p>
    </div>
  );
}
