import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { PatientNav } from '../lib/ui';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { TimelineChartCard } from '../components/TimelineChartCard';
import { AnalyticsPanel } from '../components/AnalyticsPanel';
import { LoadingState } from '../components/ui/LoadingState';

interface TimelineStatus {
  has_timeline: boolean;
  timeline_id: string | null;
  event_count: number;
  last_updated: string | null;
}

interface TimelineEvent {
  ts: string;
  event_type: string;
  source: string;
  structured?: unknown;
  text?: string | null;
  meta?: Record<string, unknown>;
}

function typeColor(type: string): string {
  const t = type.toLowerCase();
  if (t.includes('medication') || t.includes('rx')) return 'var(--accent-blue)';
  if (t.includes('lab') || t.includes('result'))    return 'var(--accent-yellow)';
  if (t.includes('diagnosis') || t.includes('dx'))  return 'var(--accent-red)';
  if (t.includes('visit') || t.includes('encounter')) return 'var(--accent-green)';
  return 'var(--text-muted)';
}

function TimelineTrack({ events }: { events: TimelineEvent[] }) {
  const sorted = [...events].sort(
    (a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime(),
  );

  return (
    <div className="relative pl-6">
      <div
        className="absolute left-2 top-0 bottom-0 w-px"
        style={{ backgroundColor: 'var(--border-color)' }}
      />
      <div className="space-y-3">
        {sorted.map((ev, idx) => (
          <div key={`${ev.ts}-${idx}`} className="relative">
            <div
              className="absolute -left-[18px] top-1.5 w-2 h-2 rounded-full border"
              style={{
                backgroundColor: 'var(--bg-primary)',
                borderColor: typeColor(ev.event_type),
              }}
            />
            <div
              className="p-3 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)' }}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span
                  className="text-xs font-mono font-bold"
                  style={{ color: typeColor(ev.event_type) }}
                >
                  {(ev.event_type || 'unknown').toUpperCase()}
                </span>
                <span
                  className="text-xs font-mono flex-shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {new Date(ev.ts).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                  })}
                </span>
              </div>
              {ev.text && (
                <p
                  className="text-xs font-sans leading-relaxed"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {ev.text}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface TimelineResponse {
  patient_id: string;
  events: TimelineEvent[];
  total_events: number;
}

interface DoctorPatient {
  id: string;
  email: string;
  full_name: string | null;
  has_timeline: boolean;
}

async function fetchTimeline(
  token: string,
  timelineId: string,
): Promise<TimelineResponse> {
  return apiFetch<TimelineResponse>(`/api/timeline/${timelineId}?limit=200`, {
    headers: authHeaders(token),
  });
}

export function TimelinePage() {
  const { token, user } = useAuth();
  const isDoctor = user?.user_type === 'doctor';

  const [patientTimelineStatus, setPatientTimelineStatus] = useState<TimelineStatus | null>(null);
  const [patientTimeline, setPatientTimeline] = useState<TimelineResponse | null>(null);
  const [patientError, setPatientError] = useState('');
  const [patientLoading, setPatientLoading] = useState(true);

  const [doctorPatients, setDoctorPatients] = useState<DoctorPatient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [selectedTimelineId, setSelectedTimelineId] = useState<string | null>(null);
  const [doctorTimeline, setDoctorTimeline] = useState<TimelineResponse | null>(null);
  const [doctorError, setDoctorError] = useState('');
  const [doctorLoading, setDoctorLoading] = useState(true);

  const selectedPatient = useMemo(
    () => doctorPatients.find((p) => p.id === selectedPatientId) ?? null,
    [doctorPatients, selectedPatientId],
  );

  useEffect(() => {
    if (!token || isDoctor) return;

    const run = async () => {
      setPatientLoading(true);
      setPatientError('');
      setPatientTimelineStatus(null);
      setPatientTimeline(null);
      try {
        const status = await apiFetch<TimelineStatus>('/api/timeline/status', {
          headers: authHeaders(token),
        });
        setPatientTimelineStatus(status);
        if (status.timeline_id && status.has_timeline) {
          const timeline = await fetchTimeline(token, status.timeline_id);
          setPatientTimeline(timeline);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setPatientTimelineStatus({ has_timeline: false, timeline_id: null, event_count: 0, last_updated: null });
        } else {
          setPatientError(err instanceof Error ? err.message : 'Failed to load timeline');
        }
      } finally {
        setPatientLoading(false);
      }
    };

    run();
  }, [token, isDoctor]);

  useEffect(() => {
    if (!token || !isDoctor) return;

    const run = async () => {
      setDoctorLoading(true);
      setDoctorError('');
      setDoctorTimeline(null);
      try {
        const patients = await apiFetch<DoctorPatient[]>('/api/doctor/patients', {
          headers: authHeaders(token),
        });
        setDoctorPatients(patients);
      } catch (err) {
        setDoctorError(err instanceof Error ? err.message : 'Failed to load patients');
      } finally {
        setDoctorLoading(false);
      }
    };

    run();
  }, [token, isDoctor]);

  useEffect(() => {
    if (!token || !isDoctor || !selectedPatientId) return;

    const run = async () => {
      setDoctorError('');
      setDoctorTimeline(null);
      setSelectedTimelineId(null);
      try {
        const status = await apiFetch<TimelineStatus>(`/api/doctor/patients/${selectedPatientId}/timeline-status`, {
          headers: authHeaders(token),
        });
        if (!status.timeline_id || !status.has_timeline) {
          return;
        }
        setSelectedTimelineId(status.timeline_id);
        const timeline = await fetchTimeline(token, status.timeline_id);
        setDoctorTimeline(timeline);
      } catch (err) {
        setDoctorError(err instanceof Error ? err.message : 'Failed to load selected patient timeline');
      }
    };

    run();
  }, [token, isDoctor, selectedPatientId]);

  if (!token) {
    return null;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-mono font-bold mb-2 text-[var(--accent-green)]">
          TIMELINE
        </h1>
        <p className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>
          View event timeline and generate analytics charts.
        </p>
      </div>

      <PatientNav />

      {!isDoctor && (
        <>
          <div
            className="rounded border"
            style={{ padding: '1.25rem 1.5rem', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
          >
            <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
              <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-green)' }}>PATIENT TIMELINE</span>
              <Link to="/timeline/upload" className="text-xs font-mono no-underline" style={{ color: 'var(--accent-green)' }}>
                UPLOAD / REPLACE
              </Link>
            </div>

            {patientLoading && <LoadingState label="Loading timeline..." />}
            {patientError && <p className="text-xs font-mono" style={{ color: 'var(--accent-red)' }}>{patientError}</p>}

            {!patientLoading && !patientError && (!patientTimelineStatus || !patientTimelineStatus.has_timeline) && (
              <div className="rounded" style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)' }}>
                <p className="text-xs font-sans leading-relaxed" style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                  No timeline data yet. Upload a timeline PDF to enable charts and timeline browsing.
                </p>
                <Link
                  to="/timeline/upload"
                  className="inline-block rounded text-xs font-mono font-bold no-underline"
                  style={{ padding: '0.375rem 0.75rem', backgroundColor: 'var(--accent-green)', color: '#000' }}
                >
                  GO TO UPLOAD
                </Link>
              </div>
            )}

            {!patientLoading && patientTimeline && patientTimeline.events.length > 0 && (
              <div style={{ maxHeight: '32rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
                <TimelineTrack events={patientTimeline.events} />
              </div>
            )}
          </div>

          {patientTimelineStatus?.timeline_id && patientTimelineStatus.has_timeline && (
            <TimelineChartCard patientId={patientTimelineStatus.timeline_id} token={token} />
          )}
        </>
      )}

      {isDoctor && (
        <>
          <div
            className="rounded border"
            style={{ padding: '1.25rem 1.5rem', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
          >
            <span
              className="text-sm font-mono font-bold block"
              style={{ color: 'var(--accent-blue)', marginBottom: '0.75rem' }}
            >
              DOCTOR TIMELINE VIEW
            </span>
            {doctorLoading ? (
              <LoadingState label="Loading patients..." />
            ) : (
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full rounded text-sm font-mono border"
                style={{
                  padding: '0.5rem 0.75rem',
                  backgroundColor: 'var(--bg-primary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value="">— Select patient —</option>
                {doctorPatients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {(p.full_name ?? p.email)}{p.has_timeline ? '' : ' (no timeline)'}
                  </option>
                ))}
              </select>
            )}
            {doctorError && (
              <p className="text-xs font-mono" style={{ color: 'var(--accent-red)', marginTop: '0.5rem' }}>{doctorError}</p>
            )}
          </div>

          {selectedPatientId && !selectedTimelineId && !doctorError && (
            <div
              className="rounded border text-xs font-sans"
              style={{ padding: '1rem', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-muted)' }}
            >
              Selected patient has no ingested timeline yet.
            </div>
          )}

          {selectedTimelineId && doctorTimeline && (
            <>
              <div
                className="rounded border"
                style={{ padding: '1.25rem 1.5rem', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
              >
                <div className="flex items-center justify-between" style={{ marginBottom: '0.75rem' }}>
                  <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-blue)' }}>
                    TIMELINE EVENTS {selectedPatient ? `— ${selectedPatient.full_name ?? selectedPatient.email}` : ''}
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    {doctorTimeline.total_events} events
                  </span>
                </div>
                <div style={{ maxHeight: '32rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
                  <TimelineTrack events={doctorTimeline.events} />
                </div>
              </div>
              <AnalyticsPanel patientId={selectedTimelineId} token={token} />
            </>
          )}
        </>
      )}
    </div>
  );
}
