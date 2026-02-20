import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
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
    <div className="max-w-5xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-mono font-bold mb-1 text-[var(--accent-green)]">
          TIMELINE
        </h1>
        <p className="text-xs font-mono text-[var(--text-muted)]">
          View event timeline and generate analytics charts.
        </p>
      </div>

      {!isDoctor && (
        <>
          <div className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-mono font-bold text-[var(--accent-green)]">PATIENT TIMELINE</span>
              <Link to="/timeline/upload" className="text-xs font-mono no-underline text-[var(--accent-green)]">
                UPLOAD / REPLACE
              </Link>
            </div>

            {patientLoading && <LoadingState label="Loading timeline..." />}
            {patientError && <p className="text-xs font-mono text-[var(--accent-red)]">{patientError}</p>}

            {!patientLoading && !patientError && (!patientTimelineStatus || !patientTimelineStatus.has_timeline) && (
              <div className="p-3 rounded bg-[var(--bg-tertiary)]">
                <p className="text-xs font-mono mb-2 text-[var(--text-muted)]">
                  No timeline data yet. Upload a timeline PDF to enable charts and timeline browsing.
                </p>
                <Link
                  to="/timeline/upload"
                  className="inline-block px-3 py-1.5 rounded text-xs font-mono font-bold no-underline bg-[var(--accent-green)] text-black"
                >
                  GO TO UPLOAD
                </Link>
              </div>
            )}

            {!patientLoading && patientTimeline && patientTimeline.events.length > 0 && (
              <div className="max-h-80 overflow-y-auto space-y-2">
                {patientTimeline.events.slice().reverse().map((ev, idx) => (
                  <div key={`${ev.ts}-${idx}`} className="p-2 rounded bg-[var(--bg-tertiary)]">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-mono font-bold text-[var(--text-primary)]">
                        {(ev.event_type || 'unknown').toUpperCase()}
                      </span>
                      <span className="text-xs font-mono text-[var(--text-muted)]">
                        {new Date(ev.ts).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs font-mono text-[var(--text-secondary)]">
                      {ev.text || `Source: ${ev.source}`}
                    </p>
                  </div>
                ))}
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
          <div className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]">
            <span className="text-sm font-mono font-bold block mb-2 text-[var(--accent-blue)]">
              DOCTOR TIMELINE VIEW
            </span>
            {doctorLoading ? (
              <LoadingState label="Loading patients..." />
            ) : (
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full px-3 py-2 rounded text-sm font-mono border bg-[var(--bg-primary)] border-[var(--border-color)] text-[var(--text-primary)]"
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
              <p className="text-xs font-mono mt-2 text-[var(--accent-red)]">{doctorError}</p>
            )}
          </div>

          {selectedPatientId && !selectedTimelineId && !doctorError && (
            <div className="p-3 rounded border text-xs font-mono bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-muted)]">
              Selected patient has no ingested timeline yet.
            </div>
          )}

          {selectedTimelineId && doctorTimeline && (
            <>
              <div className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono font-bold text-[var(--accent-blue)]">
                    TIMELINE EVENTS {selectedPatient ? `— ${selectedPatient.full_name ?? selectedPatient.email}` : ''}
                  </span>
                  <span className="text-xs font-mono text-[var(--text-muted)]">
                    {doctorTimeline.total_events} events
                  </span>
                </div>
                <div className="max-h-80 overflow-y-auto space-y-2">
                  {doctorTimeline.events.slice().reverse().map((ev, idx) => (
                    <div key={`${ev.ts}-${idx}`} className="p-2 rounded bg-[var(--bg-tertiary)]">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-mono font-bold text-[var(--text-primary)]">
                          {(ev.event_type || 'unknown').toUpperCase()}
                        </span>
                        <span className="text-xs font-mono text-[var(--text-muted)]">
                          {new Date(ev.ts).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs font-mono text-[var(--text-secondary)]">
                        {ev.text || `Source: ${ev.source}`}
                      </p>
                    </div>
                  ))}
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
