import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { JournalEditor } from '../components/JournalEditor';
import { JournalEntryList, type JournalEntryResponse } from '../components/JournalEntryList';
import { JournalEntryDetail } from '../components/JournalEntryDetail';
import { JournalAIQuery } from '../components/JournalAIQuery';

export function JournalPage() {
  const { token } = useAuth();
  const [entries, setEntries] = useState<JournalEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<JournalEntryResponse | null>(null);

  const fetchEntries = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');

    try {
      const data = await apiFetch<JournalEntryResponse[]>('/api/journal', {
        headers: authHeaders(token),
      });
      setEntries(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load journal entries');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleEntryCreated = () => {
    fetchEntries();
  };

  const handleEntryDeleted = () => {
    if (selectedEntry) {
      setSelectedEntry(null);
    }
    fetchEntries();
  };

  const handleSelectEntry = (entry: JournalEntryResponse) => {
    setSelectedEntry(prev => prev?.id === entry.id ? null : entry);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          SYMPTOM JOURNAL
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Track symptoms, environmental factors, and lifestyle data. AI-powered analysis available.
        </p>
      </div>

      <div className="space-y-4">
        <JournalEditor onEntryCreated={handleEntryCreated} />

        <JournalAIQuery />

        <div>
          <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--text-secondary)' }}>
            ENTRIES ({entries.length})
          </span>
          <JournalEntryList
            entries={entries}
            loading={loading}
            error={error}
            onEntryDeleted={handleEntryDeleted}
            onSelectEntry={handleSelectEntry}
            selectedEntryId={selectedEntry?.id ?? null}
          />
        </div>

        {selectedEntry && (
          <JournalEntryDetail
            entry={selectedEntry}
            onClose={() => setSelectedEntry(null)}
          />
        )}
      </div>
    </div>
  );
}
