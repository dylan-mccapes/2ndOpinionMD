import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { JournalEditor } from '../components/JournalEditor';
import { JournalEntryList, type JournalEntryResponse } from '../components/JournalEntryList';
import { JournalEntryDetail } from '../components/JournalEntryDetail';
import { JournalAIQuery } from '../components/JournalAIQuery';
import { JournalTimeline } from '../components/JournalTimeline';

/** Normalize API response to handle both camelCase and snake_case from backend */
function normalizeJournalEntry(raw: Record<string, unknown>): JournalEntryResponse {
  const symptomsRaw = (raw.symptoms ?? []) as Array<{ symptom?: string; severity?: number }>;
  const envFactorsRaw = (raw.environmental_factors ?? raw.environmentalFactors ?? []) as unknown[];
  const num = (v: unknown): number | null =>
    typeof v === 'number' && !Number.isNaN(v) ? v : null;
  const envFactors = Array.isArray(envFactorsRaw)
    ? envFactorsRaw.map((f) =>
        typeof f === 'string'
          ? { factor_type: f, description: '' }
          : typeof f === 'object' && f && 'factor_type' in f
            ? { factor_type: String((f as { factor_type?: unknown }).factor_type ?? ''), description: String((f as { description?: unknown }).description ?? '') }
            : typeof f === 'object' && f && 'description' in f
              ? { factor_type: '', description: String((f as { description?: unknown }).description ?? '') }
              : { factor_type: '', description: '' }
      )
    : [];
  return {
    id: String(raw.id ?? ''),
    user_id: String(raw.user_id ?? raw.userId ?? ''),
    date: String(raw.date ?? ''),
    symptoms: Array.isArray(symptomsRaw) ? symptomsRaw.map((s) => ({ symptom: String(s?.symptom ?? ''), severity: typeof s?.severity === 'number' ? s.severity : 0 })) : [],
    environmental_factors: envFactors,
    stress_level: num(raw.stress_level ?? raw.stressLevel),
    diet_notes: (raw.diet_notes ?? raw.dietNotes) as string | null,
    sleep_quality: num(raw.sleep_quality ?? raw.sleepQuality),
    notes: (raw.notes ?? null) as string | null,
    analysis: (raw.analysis ?? null) as string | null,
    pattern_observations: (raw.pattern_observations ?? raw.patternObservations ?? []) as string[],
    ai_analysis: (raw.ai_analysis ?? raw.aiAnalysis ?? null) as unknown,
    created_at: String(raw.created_at ?? raw.createdAt ?? ''),
  };
}

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
      const data = await apiFetch<Record<string, unknown>[]>('/api/journal', {
        headers: authHeaders(token),
      });
      setEntries(Array.isArray(data) ? data.map(normalizeJournalEntry) : []);
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

        <JournalTimeline reportId="default" />

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
