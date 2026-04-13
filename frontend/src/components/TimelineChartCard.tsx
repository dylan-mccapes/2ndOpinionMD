import { useState, useEffect } from 'react';
import { apiFetch, authHeaders } from '../lib/api';
import { DS, SectionLabel, Divider, LeftTrack } from '../lib/ui';

interface ChartData {
  stability_band: string;
  terrain_trajectory: string;
}

interface WindowMetric {
  window_start: string;
  window_end: string;
  stability_score: number;
  event_count: number;
}

interface AnalyticsSummaryResponse {
  patient_id: string;
  total_events: number;
  span_days: number;
  windows: WindowMetric[];
  phase_shifts: { timestamp: string; from_phase: string; to_phase: string }[];
  flare_episodes: { start: string; end: string; confidence: number }[];
  noise_floor: number;
  charts: ChartData & Record<string, string>;
  disclaimer: string;
}

interface TimelineChartCardProps {
  patientId: string;
  token: string;
}

const cardBase = {
  backgroundColor: DS.color.bgSecondary,
  border: DS.border,
  borderRadius: DS.radius,
  padding: DS.pad.card,
};

export function TimelineChartCard({ patientId, token }: TimelineChartCardProps) {
  const [data, setData] = useState<AnalyticsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!patientId || !token) return;
    const fetchAnalytics = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await apiFetch<AnalyticsSummaryResponse>(
          `/api/timeline/${patientId}/analytics/summary?window_days=7`,
          { headers: authHeaders(token) },
        );
        setData(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [patientId, token]);

  if (loading) {
    return (
      <div style={cardBase}>
        <SectionLabel>Health Insights</SectionLabel>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>Loading analytics…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={cardBase}>
        <SectionLabel>Health Insights</SectionLabel>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
          {error || 'Analytics not available. Upload your timeline to enable insights.'}
        </p>
      </div>
    );
  }

  const windows       = data.windows       ?? [];
  const phaseShifts   = data.phase_shifts   ?? [];
  const flareEpisodes = data.flare_episodes ?? [];

  const latestStability = windows.length > 0
    ? windows[windows.length - 1].stability_score
    : null;

  const stabilityLabel = latestStability !== null
    ? latestStability >= 0.7 ? 'STABLE'
    : latestStability >= 0.4 ? 'TRANSITIONING'
    : 'VARIABLE'
    : 'UNKNOWN';

  const stabilityColor = latestStability !== null
    ? latestStability >= 0.7 ? DS.color.green
    : latestStability >= 0.4 ? DS.color.yellow
    : DS.color.red
    : DS.color.textMuted;

  const spanYears = data.span_days > 365
    ? `${(data.span_days / 365).toFixed(1)} yr`
    : `${data.span_days}d`;

  return (
    <div style={cardBase}>

      {/* ── Section label ── */}
      <SectionLabel>Health Insights</SectionLabel>

      {/* ── Stat tiles ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: DS.gap.lg,
          marginBottom: DS.mb.xl,
        }}
      >
        <StatTile label="Events">
          <span className="text-xl font-mono font-bold" style={{ color: DS.color.textPrimary }}>
            {data.total_events}
          </span>
        </StatTile>

        <StatTile label="Span">
          <span className="text-xl font-mono font-bold" style={{ color: DS.color.textPrimary }}>
            {spanYears}
          </span>
        </StatTile>

        <StatTile label="Stability">
          <div className="flex items-center" style={{ gap: DS.gap.md }}>
            <span
              style={{
                display: 'inline-block',
                width: '0.5rem',
                height: '0.5rem',
                borderRadius: '9999px',
                backgroundColor: stabilityColor,
                flexShrink: 0,
              }}
            />
            <span className="text-sm font-mono font-bold" style={{ color: stabilityColor }}>
              {stabilityLabel}
            </span>
          </div>
        </StatTile>

        <StatTile label="Phase Shifts">
          <span className="text-xl font-mono font-bold" style={{ color: DS.color.textPrimary }}>
            {phaseShifts.length}
          </span>
        </StatTile>
      </div>

      {/* ── Chart images ── */}
      {data.charts.stability_band && (
        <div style={{ marginBottom: DS.mb.lg }}>
          <p className="text-xs font-sans" style={{ color: DS.color.textSecondary, marginBottom: DS.mb.sm }}>
            Stability over time
          </p>
          <img
            src={`data:image/png;base64,${data.charts.stability_band}`}
            alt="Stability band timeline"
            className="w-full rounded"
          />
        </div>
      )}

      {data.charts.terrain_trajectory && (
        <div style={{ marginBottom: DS.mb.lg }}>
          <p className="text-xs font-sans" style={{ color: DS.color.textSecondary, marginBottom: DS.mb.sm }}>
            Health terrain trajectory
          </p>
          <img
            src={`data:image/png;base64,${data.charts.terrain_trajectory}`}
            alt="Health terrain trajectory"
            className="w-full rounded"
          />
        </div>
      )}

      {/* ── Clinical prompts ── */}
      {flareEpisodes.length > 0 && (
        <div style={{ marginBottom: DS.mb.lg }}>
          <LeftTrack color="blue">
            <p
              className="text-xs font-sans font-medium"
              style={{ color: DS.color.blue, marginBottom: DS.mb.md }}
            >
              Questions to bring to your next appointment
            </p>
            <ul className="space-y-2" style={{ color: DS.color.textSecondary }}>
              <li className="text-sm font-sans leading-relaxed">
                My timeline shows {flareEpisodes.length} period{flareEpisodes.length > 1 ? 's' : ''} of elevated
                activity — can we review what was happening during those windows?
              </li>
              <li className="text-sm font-sans leading-relaxed">
                My current stability trend is{' '}
                <span style={{ color: stabilityColor }}>{stabilityLabel.toLowerCase()}</span> — does that match
                your clinical impression?
              </li>
              <li className="text-sm font-sans leading-relaxed">
                Are there patterns in my data that suggest any changes to my current care plan?
              </li>
            </ul>
          </LeftTrack>
        </div>
      )}

      {/* ── Disclaimer ── */}
      {data.disclaimer && (
        <>
          <Divider />
          <p
            className="text-xs font-sans leading-relaxed"
            style={{
              color: DS.color.textMuted,
              fontStyle: 'italic',
              paddingTop: DS.mb.lg,
            }}
          >
            {data.disclaimer}
          </p>
        </>
      )}

    </div>
  );
}

// ── Local helper ─────────────────────────────────────────────────────────────

function StatTile({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      className="rounded"
      style={{ padding: DS.pad.inner, backgroundColor: DS.color.bgTertiary }}
    >
      <span
        className="text-xs font-sans block"
        style={{ color: DS.color.textMuted, marginBottom: DS.mb.xs }}
      >
        {label}
      </span>
      {children}
    </div>
  );
}
