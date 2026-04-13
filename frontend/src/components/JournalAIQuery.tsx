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
      className="rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      {/* Header */}
      <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)' }}>
        <p
          className="text-xs font-sans font-medium uppercase tracking-widest"
          style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}
        >
          AI Journal Query
        </p>
        <p className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>
          Ask questions across all your journal entries
        </p>
      </div>

      {/* Input + results */}
      <div style={{ padding: '1.25rem 1.5rem' }}>
        <form onSubmit={handleSubmit}>
          <div className="flex" style={{ gap: '0.75rem' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 rounded border text-sm font-sans"
              style={{
                padding: '0.75rem 1rem',
                backgroundColor: 'var(--bg-tertiary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
              placeholder="What triggers my flares? When do I sleep best?"
            />
            <button
              type="submit"
              disabled={!query.trim() || loading}
              className="rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              style={{
                padding: '0.75rem 1.25rem',
                backgroundColor: 'var(--accent-blue)',
                color: '#000',
              }}
            >
              {loading ? '…' : 'ASK'}
            </button>
          </div>
        </form>

        {error && (
          <div
            className="rounded text-sm font-sans"
            style={{
              marginTop: '1rem',
              padding: '1rem',
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--accent-red)',
            }}
          >
            {error}
          </div>
        )}

        {result && (
          <div style={{ marginTop: '1rem' }}>
            {(result.entries_count ?? result.entries_analyzed ?? 0) > 0 && (
              <p
                className="text-xs font-sans"
                style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }}
              >
                Analyzed {result.entries_count ?? result.entries_analyzed} entries
              </p>
            )}
            <div
              className="rounded text-sm font-sans leading-relaxed whitespace-pre-wrap"
              style={{
                padding: '1rem',
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                borderLeft: '3px solid var(--accent-blue)',
              }}
            >
              {result.response}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
