import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { DS, Badge, StatusDot } from '../lib/ui';

interface JournalEntryResponse {
  id: string;
  user_id: string;
  date: string;
  symptoms: { symptom: string; severity: number }[];
  environmental_factors: { factor_type: string; description: string }[];
  stress_level: number | null;
  diet_notes: string | null;
  sleep_quality: number | null;
  notes: string | null;
  analysis: string | null;
  pattern_observations: string[] | string | unknown;
  ai_analysis: unknown;
  created_at: string;
}

interface JournalEntryListProps {
  entries: JournalEntryResponse[];
  loading: boolean;
  error: string;
  onEntryDeleted: () => void;
  onSelectEntry: (entry: JournalEntryResponse) => void;
  selectedEntryId: string | null;
}

export type { JournalEntryResponse };

function severityColor(sev: number): string {
  if (sev <= 3) return DS.color.green;
  if (sev <= 6) return DS.color.yellow;
  return DS.color.red;
}

export function JournalEntryList({
  entries,
  loading,
  error,
  onEntryDeleted,
  onSelectEntry,
  selectedEntryId,
}: JournalEntryListProps) {
  const { token } = useAuth();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState('');

  const handleDelete = async (entryId: string) => {
    if (!token) return;
    if (!window.confirm('Delete this journal entry? This cannot be undone.')) return;
    setDeleteError('');
    setDeletingId(entryId);
    try {
      await apiFetch(`/api/journal/${entryId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      });
      onEntryDeleted();
    } catch (err) {
      if (err instanceof ApiError) {
        setDeleteError(`API ${err.status}: ${err.body}`);
      } else {
        setDeleteError(err instanceof Error ? err.message : 'Failed to delete entry');
      }
    } finally {
      setDeletingId(null);
    }
  };

  const stateBox = {
    padding: DS.pad.card,
    borderRadius: DS.radius,
    border: DS.border,
    backgroundColor: DS.color.bgSecondary,
  };

  if (loading) {
    return (
      <div style={stateBox}>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>Loading entries…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div style={stateBox}>
        <p className="text-sm font-sans" style={{ color: DS.color.red }}>{error}</p>
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <div style={stateBox}>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
          No entries yet. Create your first entry above.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {deleteError && (
        <div
          className="rounded text-sm font-sans"
          style={{ padding: DS.pad.inner, backgroundColor: DS.color.bgTertiary, color: DS.color.red }}
        >
          {deleteError}
        </div>
      )}

      {entries.map((entry) => {
        const selected  = selectedEntryId === entry.id;
        const symptoms  = entry.symptoms ?? [];
        const hasAi =
          entry.ai_analysis != null &&
          (typeof entry.ai_analysis === 'object' ||
            (typeof entry.ai_analysis === 'string' &&
              (entry.ai_analysis as string).trim()));

        return (
          <div
            key={entry.id}
            className="rounded border cursor-pointer"
            style={{
              backgroundColor: selected ? DS.color.bgTertiary : DS.color.bgSecondary,
              borderColor: DS.color.border,
              borderLeft: selected
                ? `3px solid ${DS.color.green}`
                : '3px solid transparent',
            }}
            onClick={() => onSelectEntry(entry)}
          >
            <div style={{ padding: DS.pad.sm }}>

              {/* Date + badges + DEL */}
              <div
                className="flex items-center justify-between flex-wrap"
                style={{ gap: DS.gap.lg, marginBottom: DS.mb.sm }}
              >
                <div className="flex items-center flex-wrap" style={{ gap: DS.gap.md }}>
                  <span className="text-sm font-sans font-medium" style={{ color: DS.color.textPrimary }}>
                    {new Date(entry.date).toLocaleDateString('en-US', {
                      weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
                    })}
                  </span>

                  {typeof entry.stress_level === 'number' && (
                    <Badge color={severityColor(entry.stress_level)}>
                      stress {entry.stress_level}/10
                    </Badge>
                  )}
                  {typeof entry.sleep_quality === 'number' && (
                    <Badge color={DS.color.blue}>
                      sleep {entry.sleep_quality}/10
                    </Badge>
                  )}
                  {hasAi && (
                    <StatusDot variant="idle" color={DS.color.blue} label="AI" />
                  )}
                </div>

                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(entry.id); }}
                  disabled={deletingId === entry.id}
                  className="text-xs font-mono rounded cursor-pointer disabled:opacity-50 shrink-0"
                  style={{
                    padding: `${DS.gap.md} ${DS.gap.lg}`,
                    background: 'none',
                    border: DS.border,
                    color: DS.color.textMuted,
                  }}
                >
                  {deletingId === entry.id ? '…' : 'DEL'}
                </button>
              </div>

              {/* Symptom chips */}
              {symptoms.length > 0 && (
                <div className="flex flex-wrap" style={{ gap: DS.gap.sm, marginBottom: DS.mb.sm }}>
                  {symptoms.map((s, i) => (
                    <Badge key={i} color={severityColor(s.severity)}>
                      {s.symptom} · {s.severity}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Notes preview */}
              {entry.notes && (
                <p className="text-xs font-sans truncate" style={{ color: DS.color.textMuted }}>
                  {entry.notes}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
