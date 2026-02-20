import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

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
  pattern_observations: string[];
  ai_analysis: string | null;
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

export function JournalEntryList({ entries, loading, error, onEntryDeleted, onSelectEntry, selectedEntryId }: JournalEntryListProps) {
  const { token } = useAuth();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState('');

  const handleDelete = async (entryId: string) => {
    if (!token) return;
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

  const severityColor = (sev: number): string => {
    if (sev <= 3) return 'var(--accent-green)';
    if (sev <= 6) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  if (loading) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          Loading journal entries...
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

  if (entries.length === 0) {
    return (
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          No journal entries yet. Create your first entry above.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {deleteError && (
        <div
          className="p-3 rounded text-sm font-mono"
          style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
        >
          {deleteError}
        </div>
      )}

      {entries.map((entry) => (
        <div
          key={entry.id}
          className="p-3 rounded border cursor-pointer"
          style={{
            backgroundColor: selectedEntryId === entry.id ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            borderColor: selectedEntryId === entry.id ? 'var(--accent-green)' : 'var(--border-color)',
          }}
          onClick={() => onSelectEntry(entry)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
                  {new Date(entry.date).toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
                </span>
                {entry.stress_level !== null && (
                  <span className="text-xs font-mono" style={{ color: severityColor(entry.stress_level) }}>
                    STRESS: {entry.stress_level}/10
                  </span>
                )}
                {entry.sleep_quality !== null && (
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-blue)' }}>
                    SLEEP: {entry.sleep_quality}/10
                  </span>
                )}
              </div>

              {entry.symptoms.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-1">
                  {entry.symptoms.map((s, i) => (
                    <span
                      key={i}
                      className="text-xs font-mono px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: 'var(--bg-tertiary)', color: severityColor(s.severity) }}
                    >
                      {s.symptom} ({s.severity})
                    </span>
                  ))}
                </div>
              )}

              {entry.notes && (
                <p
                  className="text-xs font-mono truncate"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {entry.notes}
                </p>
              )}

              {entry.ai_analysis && (
                <span className="text-xs font-mono" style={{ color: 'var(--accent-blue)' }}>
                  [AI ANALYSIS AVAILABLE]
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); handleDelete(entry.id); }}
              disabled={deletingId === entry.id}
              className="text-xs font-mono px-1 cursor-pointer disabled:opacity-50 shrink-0"
              style={{ background: 'none', border: 'none', color: 'var(--accent-red)' }}
            >
              {deletingId === entry.id ? '...' : '[DEL]'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
