import { useState, useEffect } from 'react';
import { apiFetch, authHeaders } from '../lib/api';

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
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-green)' }}>
          HEALTH INSIGHTS
        </span>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Loading analytics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--accent-green)' }}>
          HEALTH INSIGHTS
        </span>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {error || 'Analytics not available yet. Upload your timeline to enable insights.'}
        </p>
      </div>
    );
  }

  const latestStability = data.windows.length > 0
    ? data.windows[data.windows.length - 1].stability_score
    : null;

  const stabilityLabel = latestStability !== null
    ? latestStability >= 0.7 ? 'STABLE' : latestStability >= 0.4 ? 'TRANSITIONING' : 'VARIABLE'
    : 'UNKNOWN';

  const stabilityColor = latestStability !== null
    ? latestStability >= 0.7 ? 'var(--accent-green)' : latestStability >= 0.4 ? 'var(--accent-yellow)' : 'var(--accent-red)'
    : 'var(--text-muted)';

  return (
    <div className="space-y-4">
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-3" style={{ color: 'var(--accent-green)' }}>
          HEALTH INSIGHTS
        </span>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Events</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {data.total_events}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Span</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {data.span_days}d
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Status</span>
            <span className="text-sm font-mono font-bold" style={{ color: stabilityColor }}>
              {stabilityLabel}
            </span>
          </div>
          <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono block" style={{ color: 'var(--text-muted)' }}>Phase Shifts</span>
            <span className="text-lg font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
              {data.phase_shifts.length}
            </span>
          </div>
        </div>

        {data.charts.stability_band && (
          <div className="mb-3">
            <span className="text-xs font-mono block mb-1" style={{ color: 'var(--text-secondary)' }}>
              YOUR STABILITY OVER TIME
            </span>
            <img
              src={`data:image/png;base64,${data.charts.stability_band}`}
              alt="Stability band timeline"
              className="w-full rounded"
            />
          </div>
        )}

        {data.charts.terrain_trajectory && (
          <div className="mb-3">
            <span className="text-xs font-mono block mb-1" style={{ color: 'var(--text-secondary)' }}>
              YOUR HEALTH MAP
            </span>
            <img
              src={`data:image/png;base64,${data.charts.terrain_trajectory}`}
              alt="Health terrain trajectory"
              className="w-full rounded"
            />
          </div>
        )}

        {data.flare_episodes.length > 0 && (
          <div className="mt-3 p-3 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--accent-yellow)' }}>
              QUESTIONS FOR YOUR DOCTOR
            </span>
            <ul className="text-xs font-mono space-y-1" style={{ color: 'var(--text-secondary)' }}>
              <li>Can you review the {data.flare_episodes.length} periods of higher activity with me?</li>
              <li>What patterns do you see in my timeline that I should be aware of?</li>
              <li>Are there any adjustments to my care plan based on these trends?</li>
            </ul>
          </div>
        )}

        <p className="text-xs font-mono mt-3" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
          {data.disclaimer}
        </p>
      </div>
    </div>
  );
}
