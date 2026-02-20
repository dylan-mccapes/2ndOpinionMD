import { useState } from 'react';

export function EohPage() {
  const [query, setQuery] = useState('');

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          EoH MODE
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Single Ethos-of-Health reasoning cycle. Hypothesis set + evidence
          weighting. SSE streaming.
        </p>
      </div>

      <div
        className="p-4 rounded border mb-4"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <label
          className="block text-xs font-mono mb-2"
          style={{ color: 'var(--text-secondary)' }}
        >
          CLINICAL CONTEXT (symptoms + age + sex + history)
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. 34F, bilateral joint pain, morning stiffness >1hr, fatigue, ANA+, family hx SLE"
          className="w-full p-3 rounded border text-sm font-mono resize-y"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
            minHeight: '80px',
          }}
        />
        <div className="flex justify-end mt-3">
          <button
            disabled={!query.trim()}
            className="px-4 py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: 'var(--accent-green)',
              color: '#000',
            }}
          >
            RUN EoH
          </button>
        </div>
      </div>

      <div
        className="p-4 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <p
          className="text-xs font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          EoH reasoning display will render here. Awaiting Phase 2
          implementation.
        </p>
      </div>
    </div>
  );
}
