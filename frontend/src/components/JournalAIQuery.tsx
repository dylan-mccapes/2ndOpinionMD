import { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface AIQueryResponse {
  query: string;
  response: string;
  entries_count?: number;
  entries_analyzed?: number;
}

export function JournalAIQuery() {
  const { token } = useAuth();
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<AIQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !query.trim()) return;
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const data = await apiFetch<AIQueryResponse>('/api/journal/query-ai', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() }),
      });
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to query AI');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="p-4 rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <span className="text-sm font-mono font-bold block mb-3" style={{ color: 'var(--accent-blue)' }}>
        AI JOURNAL QUERY
      </span>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 p-2 rounded border text-sm font-mono"
            style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
            placeholder="Ask about your journal entries... (e.g. 'What triggers my flares?')"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="px-4 py-2 rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: 'var(--accent-blue)', color: '#000' }}
          >
            {loading ? '...' : 'ASK'}
          </button>
        </div>
      </form>

      {error && (
        <div
          className="mt-3 p-3 rounded text-sm font-mono"
          style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
        >
          {error}
        </div>
      )}

      {result && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              Analyzed {(result.entries_count ?? result.entries_analyzed ?? 0)} entries
            </span>
          </div>
          <div
            className="p-3 rounded text-xs font-mono whitespace-pre-wrap"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', borderLeft: '2px solid var(--accent-blue)' }}
          >
            {result.response}
          </div>
        </div>
      )}
    </div>
  );
}
