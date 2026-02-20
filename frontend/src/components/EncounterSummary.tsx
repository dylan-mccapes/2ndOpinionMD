import { useState, useCallback } from 'react';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import type { SuggestedCode } from './CodeSuggestions';

interface EncounterSummaryProps {
  transcript: string;
  acceptedCodes: SuggestedCode[];
  patientId: string | null;
  token: string;
  enabled: boolean;
}

interface EncounterNote {
  chief_complaint?: string;
  history_of_present_illness?: string;
  review_of_systems?: string;
  assessment?: string;
  plan?: string[];
  accepted_codes_summary?: Array<{ system: string; code: string; title: string }>;
  suggested_labs?: string[];
  suggested_imaging?: string[];
  follow_up?: string;
  markdown?: string;
}

interface NoteResponse {
  note: EncounterNote;
  model: string;
  patient_id: string | null;
  encounter_date: string;
  timestamp: string;
  doctor_id: string;
  doctor_name: string;
}

type ExportFormat = 'json' | 'csv' | 'journal';

export function EncounterSummary({
  transcript,
  acceptedCodes,
  patientId,
  token,
  enabled,
}: EncounterSummaryProps) {
  const [note, setNote] = useState<EncounterNote | null>(null);
  const [meta, setMeta] = useState<{ encounter_date: string; doctor_name: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [exported, setExported] = useState<ExportFormat | null>(null);
  const [journalSaving, setJournalSaving] = useState(false);
  const [journalSaved, setJournalSaved] = useState(false);

  const generateNote = useCallback(async () => {
    if (!transcript.trim()) return;
    setLoading(true);
    setError('');
    setNote(null);
    setExported(null);
    setJournalSaved(false);

    try {
      const res = await apiFetch<NoteResponse>('/api/portal/encounter_note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          transcript,
          accepted_codes: acceptedCodes.map((c) => ({
            system: c.system,
            code: c.code,
            description: c.description,
            confidence: c.confidence,
          })),
          patient_id: patientId,
        }),
      });

      setNote(res.note);
      setMeta({ encounter_date: res.encounter_date, doctor_name: res.doctor_name });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `API ${err.status}: ${err.body}`
          : err instanceof Error
            ? err.message
            : 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [transcript, acceptedCodes, patientId, token]);

  const handleExportJSON = useCallback(() => {
    if (!note) return;
    const blob = new Blob([JSON.stringify(note, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `encounter-note-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    setExported('json');
  }, [note]);

  const handleExportCSV = useCallback(() => {
    if (!note) return;
    const rows: string[] = ['field,value'];
    if (note.chief_complaint) rows.push(`"Chief Complaint","${note.chief_complaint.replace(/"/g, '""')}"`);
    if (note.history_of_present_illness) rows.push(`"HPI","${note.history_of_present_illness.replace(/"/g, '""')}"`);
    if (note.assessment) rows.push(`"Assessment","${note.assessment.replace(/"/g, '""')}"`);
    if (note.plan) {
      for (const p of note.plan) {
        rows.push(`"Plan","${p.replace(/"/g, '""')}"`);
      }
    }
    if (note.follow_up) rows.push(`"Follow-up","${note.follow_up.replace(/"/g, '""')}"`);
    if (note.accepted_codes_summary) {
      for (const c of note.accepted_codes_summary) {
        rows.push(`"Code","[${c.system}] ${c.code} — ${c.title}"`);
      }
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `encounter-note-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    setExported('csv');
  }, [note]);

  const handleSaveToJournal = useCallback(async () => {
    if (!note || !patientId) return;
    setJournalSaving(true);

    try {
      const content = note.markdown || [
        `## Chief Complaint\n${note.chief_complaint || 'N/A'}`,
        `## History of Present Illness\n${note.history_of_present_illness || 'N/A'}`,
        `## Assessment\n${note.assessment || 'N/A'}`,
        `## Plan\n${(note.plan || []).map((p) => `- ${p}`).join('\n') || 'N/A'}`,
        `## Follow-up\n${note.follow_up || 'N/A'}`,
      ].join('\n\n');

      await apiFetch('/api/journal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          title: `Encounter Note — ${meta?.encounter_date || new Date().toISOString().slice(0, 10)}`,
          content,
          category: 'encounter_note',
          patient_id: patientId,
        }),
      });

      setJournalSaved(true);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `API ${err.status}: ${err.body}`
          : err instanceof Error
            ? err.message
            : 'Unknown error';
      setError(`Journal save failed: ${msg}`);
    } finally {
      setJournalSaving(false);
    }
  }, [note, patientId, token, meta]);

  if (!enabled) return null;

  return (
    <div
      className="rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <span className="text-xs font-mono font-bold" style={{ color: 'var(--accent-yellow)' }}>
          ENCOUNTER SUMMARY
        </span>
        {meta && (
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {meta.encounter_date} — {meta.doctor_name}
          </span>
        )}
      </div>

      <div className="p-4">
        {!note && !loading && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={generateNote}
              disabled={!transcript.trim() || loading}
              className="px-4 py-2 rounded text-sm font-mono font-bold disabled:opacity-50"
              style={{ backgroundColor: 'var(--accent-blue)', color: '#fff' }}
            >
              GENERATE ENCOUNTER NOTE
            </button>
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              {acceptedCodes.length} accepted code{acceptedCodes.length !== 1 ? 's' : ''} will be included
            </span>
          </div>
        )}

        {loading && (
          <p className="text-sm font-mono" style={{ color: 'var(--accent-yellow)' }}>
            Generating encounter note...
          </p>
        )}

        {error && (
          <div
            className="p-3 rounded border mb-3"
            style={{ borderColor: 'var(--accent-red)', backgroundColor: 'var(--bg-tertiary)' }}
          >
            <p className="text-xs font-mono" style={{ color: 'var(--accent-red)' }}>
              {error}
            </p>
          </div>
        )}

        {note && (
          <div className="space-y-4">
            {note.chief_complaint && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  CHIEF COMPLAINT
                </h4>
                <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                  {note.chief_complaint}
                </p>
              </div>
            )}

            {note.history_of_present_illness && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  HISTORY OF PRESENT ILLNESS
                </h4>
                <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                  {note.history_of_present_illness}
                </p>
              </div>
            )}

            {note.review_of_systems && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  REVIEW OF SYSTEMS
                </h4>
                <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                  {note.review_of_systems}
                </p>
              </div>
            )}

            {note.assessment && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  ASSESSMENT
                </h4>
                <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                  {note.assessment}
                </p>
              </div>
            )}

            {note.plan && note.plan.length > 0 && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  PLAN
                </h4>
                <ul className="space-y-1">
                  {note.plan.map((p, i) => (
                    <li key={i} className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                      — {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {note.accepted_codes_summary && note.accepted_codes_summary.length > 0 && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  CODES
                </h4>
                <div className="space-y-1">
                  {note.accepted_codes_summary.map((c, i) => (
                    <p key={i} className="text-xs font-mono" style={{ color: 'var(--accent-blue)' }}>
                      [{c.system}] {c.code} — {c.title}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {note.follow_up && (
              <div>
                <h4
                  className="text-xs font-mono font-bold tracking-wide mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  FOLLOW-UP
                </h4>
                <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                  {note.follow_up}
                </p>
              </div>
            )}

            <div className="flex items-center gap-2 pt-3 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <button
                type="button"
                onClick={handleExportJSON}
                className="px-3 py-1.5 rounded text-xs font-mono font-bold"
                style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
              >
                EXPORT JSON
              </button>
              <button
                type="button"
                onClick={handleExportCSV}
                className="px-3 py-1.5 rounded text-xs font-mono font-bold"
                style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
              >
                EXPORT CSV
              </button>
              {patientId && (
                <button
                  type="button"
                  onClick={handleSaveToJournal}
                  disabled={journalSaving || journalSaved}
                  className="px-3 py-1.5 rounded text-xs font-mono font-bold disabled:opacity-50"
                  style={{
                    backgroundColor: journalSaved ? 'var(--bg-tertiary)' : 'var(--accent-blue)',
                    color: journalSaved ? 'var(--text-secondary)' : '#fff',
                    border: journalSaved ? '1px solid var(--border-color)' : 'none',
                  }}
                >
                  {journalSaving ? 'SAVING...' : journalSaved ? 'SAVED TO JOURNAL' : 'SAVE TO JOURNAL'}
                </button>
              )}
              <button
                type="button"
                onClick={generateNote}
                disabled={loading}
                className="px-3 py-1.5 rounded text-xs font-mono font-bold"
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-color)',
                }}
              >
                REGENERATE
              </button>
              {exported && (
                <span className="text-xs font-mono" style={{ color: 'var(--accent-green)' }}>
                  Exported as {exported.toUpperCase()}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
