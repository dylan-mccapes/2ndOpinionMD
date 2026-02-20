import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface TimelineEntry {
  date: string;
  symptoms: { symptom: string; severity: number }[];
  stress_level: number | null;
  sleep_quality: number | null;
  zone: number | null;
}

interface TimelineData {
  report_id: string;
  entries: TimelineEntry[];
  summary: string | null;
}

interface JournalTimelineProps {
  reportId: string;
}

export function JournalTimeline({ reportId }: JournalTimelineProps) {
  const { token } = useAuth();
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchTimeline = useCallback(async () => {
    if (!token || !reportId) return;
    setLoading(true);
    setError('');

    try {
      const result = await apiFetch<TimelineData>(`/api/journal/timeline/${reportId}`, {
        headers: authHeaders(token),
      });
      setData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load timeline');
      }
    } finally {
      setLoading(false);
    }
  }, [token, reportId]);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  const severityColor = (sev: number): string => {
    if (sev <= 3) return 'var(--accent-green)';
    if (sev <= 6) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  const zoneLabel = (zone: number | null): string => {
    if (zone === null) return 'UNKNOWN';
    if (zone === 1) return 'ZONE 1 — STABLE';
    if (zone === 2) return 'ZONE 2 — MILD';
    if (zone === 3) return 'ZONE 3 — MODERATE';
    if (zone === 4) return 'ZONE 4 — SEVERE';
    if (zone === 5) return 'ZONE 5 — CRITICAL';
    return `ZONE ${zone}`;
  };

  const zoneColor = (zone: number | null): string => {
    if (zone === null) return 'var(--text-muted)';
    if (zone <= 2) return 'var(--accent-green)';
    if (zone === 3) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  if (loading) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          Loading timeline...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <p className="text-sm font-mono" style={{ color: 'var(--accent-red)' }}>{error}</p>
      </div>
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          No timeline data available for this report.
        </p>
      </div>
    );
  }

  return (
    <div
      className="p-4 rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div className="mb-3">
        <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
          TIMELINE
        </span>
        <span className="text-xs font-mono ml-2" style={{ color: 'var(--text-muted)' }}>
          {data.entries.length} entries
        </span>
      </div>

      {data.summary && (
        <p
          className="text-xs font-mono mb-3 p-2 rounded"
          style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
        >
          {data.summary}
        </p>
      )}

      <div className="relative">
        <div
          className="absolute left-2 top-0 bottom-0 w-px"
          style={{ backgroundColor: 'var(--border-color)' }}
        />

        <div className="space-y-3">
          {data.entries.map((entry, i) => (
            <div key={i} className="relative pl-6">
              <div
                className="absolute left-1 top-1 w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: zoneColor(entry.zone) }}
              />

              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
                  {new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                {entry.zone !== null && (
                  <span className="text-xs font-mono" style={{ color: zoneColor(entry.zone) }}>
                    {zoneLabel(entry.zone)}
                  </span>
                )}
              </div>

              {entry.symptoms.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-1">
                  {entry.symptoms.map((s, j) => (
                    <span
                      key={j}
                      className="text-xs font-mono px-1 rounded"
                      style={{ color: severityColor(s.severity) }}
                    >
                      {s.symptom}({s.severity})
                    </span>
                  ))}
                </div>
              )}

              <div className="flex gap-3">
                {entry.stress_level !== null && (
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    stress:{entry.stress_level}
                  </span>
                )}
                {entry.sleep_quality !== null && (
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    sleep:{entry.sleep_quality}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
