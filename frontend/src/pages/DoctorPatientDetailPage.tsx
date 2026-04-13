import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { AnalyticsPanel } from '../components/AnalyticsPanel';
import { LoadingState } from '../components/ui/LoadingState';

interface JournalEntry {
  id: string;
  title: string;
  content: string;
  severity: number | null;
  created_at: string;
}

interface PatientTimelineStatus {
  has_timeline: boolean;
  timeline_id: string | null;
  event_count: number;
  last_updated: string | null;
}

export function DoctorPatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { token } = useAuth();

  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [timeline, setTimeline] = useState<PatientTimelineStatus | null>(null);
  const [journalLoading, setJournalLoading] = useState(true);
  const [timelineLoading, setTimelineLoading] = useState(true);
  const [journalError, setJournalError] = useState('');
  const [timelineError, setTimelineError] = useState('');

  useEffect(() => {
    if (!token || !patientId) return;

    const fetchJournal = async () => {
      setJournalLoading(true);
      setJournalError('');
      try {
        const data = await apiFetch<JournalEntry[]>(`/api/doctor/patients/${patientId}/journal`, {
          headers: authHeaders(token),
        });
        setJournal(data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setJournal([]);
        } else if (err instanceof ApiError) {
          setJournalError(`API ${err.status}: ${err.body}`);
        } else {
          setJournalError(err instanceof Error ? err.message : 'Failed to load journal');
        }
      } finally {
        setJournalLoading(false);
      }
    };

    const fetchTimeline = async () => {
      setTimelineLoading(true);
      setTimelineError('');
      try {
        const data = await apiFetch<PatientTimelineStatus>(`/api/doctor/patients/${patientId}/timeline-status`, {
          headers: authHeaders(token),
        });
        setTimeline(data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setTimeline({ has_timeline: false, timeline_id: null, event_count: 0, last_updated: null });
        } else if (err instanceof ApiError) {
          setTimelineError(`API ${err.status}: ${err.body}`);
        } else {
          setTimelineError(err instanceof Error ? err.message : 'Failed to load timeline');
        }
      } finally {
        setTimelineLoading(false);
      }
    };

    fetchJournal();
    fetchTimeline();
  }, [token, patientId]);

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/doctor"
          className="text-xs font-mono no-underline mb-2 inline-block text-[var(--accent-blue)]"
        >
          BACK TO PATIENTS
        </Link>
        <h1
          className="text-xl font-mono font-bold mb-1 text-[var(--accent-blue)]"
        >
          PATIENT DETAIL
        </h1>
        <p className="text-xs font-mono text-[var(--text-muted)]">
          Read-only view. Patient ID: {patientId}
        </p>
      </div>

      <div className="space-y-4">
        <div
          className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]"
        >
          <span className="text-sm font-mono font-bold block mb-3 text-[var(--accent-green)]">
            TIMELINE STATUS
          </span>

          {timelineLoading && (
            <LoadingState />
          )}

          {timelineError && (
            <div className="p-3 rounded text-sm font-mono bg-[var(--bg-tertiary)] text-[var(--accent-red)]">
              {timelineError}
            </div>
          )}

          {!timelineLoading && !timelineError && timeline && (
            <div className="flex items-center gap-3">
              <span
                className="text-xs font-mono px-2 py-0.5 rounded"
                style={{
                  color: timeline.has_timeline ? 'var(--accent-green)' : 'var(--accent-yellow)',
                  backgroundColor: 'var(--bg-tertiary)',
                }}
              >
                {timeline.has_timeline ? `READY (${timeline.event_count} events)` : 'NO TIMELINE'}
              </span>
              {timeline.last_updated && (
                <span className="text-xs font-mono text-[var(--text-muted)]">
                  Updated: {new Date(timeline.last_updated).toLocaleDateString()}
                </span>
              )}
            </div>
          )}
        </div>

        <div
          className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-mono font-bold text-[var(--accent-green)]">
              JOURNAL ENTRIES
            </span>
            <span className="text-xs font-mono text-[var(--text-muted)]">
              {journal.length} entries
            </span>
          </div>

          {journalLoading && (
            <LoadingState />
          )}

          {journalError && (
            <div className="p-3 rounded text-sm font-mono bg-[var(--bg-tertiary)] text-[var(--accent-red)]">
              {journalError}
            </div>
          )}

          {!journalLoading && !journalError && journal.length === 0 && (
            <p className="text-xs font-mono text-[var(--text-muted)]">
              No journal entries found for this patient.
            </p>
          )}

          {!journalLoading && journal.length > 0 && (
            <div className="space-y-2">
              {journal.map((entry) => (
                <div
                  key={entry.id}
                  className="p-3 rounded bg-[var(--bg-tertiary)]"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-mono font-bold text-[var(--text-primary)]">
                      {entry.title}
                    </span>
                    <div className="flex items-center gap-2">
                      {entry.severity !== null && (
                        <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--accent-yellow)' }}>
                          SEV {entry.severity}/10
                        </span>
                      )}
                      <span className="text-xs font-mono text-[var(--text-muted)]">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <p
                    className="text-xs font-mono mt-1 text-[var(--text-secondary)] whitespace-pre-wrap"
                  >
                    {entry.content.length > 300 ? `${entry.content.slice(0, 300)}...` : entry.content}
                  </p>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs font-mono mt-3 text-[var(--text-muted)]">
            Read-only. Journal entries cannot be edited from the doctor portal.
          </p>
        </div>

        {timeline?.has_timeline && token && patientId && (
          <AnalyticsPanel patientId={patientId} token={token} />
        )}
      </div>
    </div>
  );
}
