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

interface BackendTimelineResponse {
  initialDiagnosis?: { date?: string; diagnoses?: unknown[] };
  journalEntries?: Array<{
    id?: string;
    date?: string;
    created_at?: string;
    symptoms?: { symptom?: string; severity?: number }[];
    stress_level?: number | null;
    sleep_quality?: number | null;
  }>;
}

interface JournalTimelineProps {
  reportId: string;
}

function mapBackendToTimeline(raw: BackendTimelineResponse): { entries: TimelineEntry[] } {
  const journalEntries = raw.journalEntries ?? [];
  const entries: TimelineEntry[] = journalEntries.map((e) => {
    const dateVal = e.date ?? e.created_at;
    const dateStr =
      typeof dateVal === 'string'
        ? dateVal
        : dateVal != null
        ? new Date(dateVal as Date).toISOString()
        : new Date().toISOString();
    return {
      date: dateStr,
      symptoms: Array.isArray(e.symptoms)
        ? e.symptoms.map((s) => ({ symptom: s.symptom ?? '', severity: s.severity ?? 5 }))
        : [],
      stress_level: typeof e.stress_level === 'number' ? e.stress_level : null,
      sleep_quality: typeof e.sleep_quality === 'number' ? e.sleep_quality : null,
      zone: null,
    };
  });
  return { entries };
}

const CARD: React.CSSProperties = {
  padding: '1.25rem 1.5rem',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-secondary)',
};

export function JournalTimeline({ reportId }: JournalTimelineProps) {
  const { token } = useAuth();
  const [data, setData] = useState<{ entries: TimelineEntry[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchTimeline = useCallback(async () => {
    if (!token || !reportId) return;
    setLoading(true);
    setError('');

    try {
      const result = await apiFetch<BackendTimelineResponse>(
        `/api/journal/timeline/${reportId}`,
        { headers: authHeaders(token) },
      );
      setData(mapBackendToTimeline(result));
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
      <div style={CARD}>
        <p className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>
          Loading timeline…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={CARD}>
        <p className="text-sm font-sans" style={{ color: 'var(--accent-red)' }}>{error}</p>
      </div>
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <div style={CARD}>
        <p className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>
          No timeline data available for this report.
        </p>
      </div>
    );
  }

  return (
    <div style={CARD}>
      {/* Header */}
      <div style={{ marginBottom: '1rem' }}>
        <span className="text-xs font-sans font-medium uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          Timeline
        </span>
        <span className="text-xs font-mono" style={{ color: 'var(--accent-green)', marginLeft: '0.5rem' }}>
          ({data.entries.length})
        </span>
      </div>

      {/* Vertical track */}
      <div style={{ position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            left: '0.4rem',
            top: 0,
            bottom: 0,
            width: '1px',
            backgroundColor: 'var(--border-color)',
          }}
        />

        <div className="space-y-3">
          {data.entries.map((entry, i) => (
            <div key={i} style={{ position: 'relative', paddingLeft: '1.5rem' }}>
              {/* Zone dot */}
              <div
                style={{
                  position: 'absolute',
                  left: '0.125rem',
                  top: '0.25rem',
                  width: '0.625rem',
                  height: '0.625rem',
                  borderRadius: '9999px',
                  backgroundColor: zoneColor(entry.zone),
                }}
              />

              {/* Date + zone label */}
              <div
                className="flex items-center flex-wrap"
                style={{ gap: '0.5rem', marginBottom: '0.25rem' }}
              >
                <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
                  {new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                {entry.zone !== null && (
                  <span className="text-xs font-mono" style={{ color: zoneColor(entry.zone) }}>
                    {zoneLabel(entry.zone)}
                  </span>
                )}
              </div>

              {/* Symptom chips */}
              {entry.symptoms.length > 0 && (
                <div
                  className="flex flex-wrap"
                  style={{ gap: '0.25rem', marginBottom: '0.25rem' }}
                >
                  {entry.symptoms.map((s, j) => (
                    <span
                      key={j}
                      className="text-xs font-sans rounded"
                      style={{
                        padding: '0.1rem 0.4rem',
                        color: severityColor(s.severity),
                        backgroundColor: 'var(--bg-tertiary)',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      {s.symptom} · {s.severity}
                    </span>
                  ))}
                </div>
              )}

              {/* Score row */}
              <div className="flex" style={{ gap: '0.75rem' }}>
                {entry.stress_level !== null && (
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    stress {entry.stress_level}/10
                  </span>
                )}
                {entry.sleep_quality !== null && (
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    sleep {entry.sleep_quality}/10
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
