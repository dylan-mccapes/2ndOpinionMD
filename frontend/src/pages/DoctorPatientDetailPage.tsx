import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { AnalyticsPanel } from '../components/AnalyticsPanel';
import { LoadingState } from '../components/ui/LoadingState';
import { Card, DS, SectionLabel, InlineMessage } from '../lib/ui';

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

  const safeJournal = Array.isArray(journal) ? journal : [];
  const asSeverity = (v: unknown): number | null => {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };

  useEffect(() => {
    if (!token || !patientId) return;

    const fetchJournal = async () => {
      setJournalLoading(true);
      setJournalError('');
      try {
        const data = await apiFetch<JournalEntry[]>(`/api/doctor/patients/${patientId}/journal`, {
          headers: authHeaders(token),
        });
        setJournal(Array.isArray(data) ? data : []);
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap['2xl'] }}>
      <div style={{ marginBottom: DS.mb.sm }}>
        <Link
          to="/doctor"
          className="text-xs font-mono no-underline inline-block text-[var(--accent-blue)]"
          style={{ marginBottom: DS.mb.sm }}
        >
          BACK TO PATIENTS
        </Link>
        <h1
          className="text-xl font-mono font-bold text-[var(--accent-blue)]"
          style={{ marginBottom: DS.mb.xs }}
        >
          PATIENT DETAIL
        </h1>
        <p className="text-xs font-mono text-[var(--text-muted)]">
          Read-only view. Patient ID: {patientId}
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.xl }}>
        <Card style={{ padding: DS.pad.card }}>
          <SectionLabel style={{ color: 'var(--accent-green)', marginBottom: DS.mb.md }}>
            TIMELINE STATUS
          </SectionLabel>

          {timelineLoading && (
            <LoadingState />
          )}

          {timelineError && (
            <InlineMessage variant="error">{timelineError}</InlineMessage>
          )}

          {!timelineLoading && !timelineError && timeline && (
            <div className="flex items-center" style={{ gap: DS.gap.lg }}>
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
        </Card>

        <Card style={{ padding: DS.pad.card }}>
          <div className="flex items-center justify-between" style={{ marginBottom: DS.mb.md }}>
            <span className="text-sm font-mono font-bold text-[var(--accent-green)]">
              JOURNAL ENTRIES
            </span>
            <span className="text-xs font-mono text-[var(--text-muted)]">
              {safeJournal.length} entries
            </span>
          </div>

          {journalLoading && (
            <LoadingState />
          )}

          {journalError && (
            <InlineMessage variant="error">{journalError}</InlineMessage>
          )}

          {!journalLoading && !journalError && safeJournal.length === 0 && (
            <p className="text-xs font-mono text-[var(--text-muted)]">
              No journal entries found for this patient.
            </p>
          )}

          {!journalLoading && safeJournal.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.md }}>
              {safeJournal.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded bg-[var(--bg-tertiary)]"
                  style={{ padding: DS.pad.inner }}
                >
                  <div className="flex items-center justify-between" style={{ marginBottom: DS.mb.xs }}>
                    <span className="text-sm font-mono font-bold text-[var(--text-primary)]">
                      {entry.title}
                    </span>
                    <div className="flex items-center" style={{ gap: DS.gap.md }}>
                      {asSeverity(entry.severity) !== null && (
                        <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--accent-yellow)' }}>
                          SEV {asSeverity(entry.severity)}/10
                        </span>
                      )}
                      <span className="text-xs font-mono text-[var(--text-muted)]">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <p
                    className="text-xs font-mono text-[var(--text-secondary)] whitespace-pre-wrap"
                    style={{ marginTop: DS.mb.xs, lineHeight: 1.55 }}
                  >
                    {String(entry.content || '').length > 300
                      ? `${String(entry.content || '').slice(0, 300)}...`
                      : String(entry.content || '')}
                  </p>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs font-mono text-[var(--text-muted)]" style={{ marginTop: DS.mb.md }}>
            Read-only. Journal entries cannot be edited from the doctor portal.
          </p>
        </Card>

        {timeline?.has_timeline && token && patientId && (
          <AnalyticsPanel patientId={patientId} token={token} />
        )}
      </div>
    </div>
  );
}
