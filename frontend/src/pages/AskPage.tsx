import { useState, useCallback } from 'react';
import { StreamingDisplay, type StreamStatus } from '../components/StreamingDisplay';
import { TransparencyPanel } from '../components/TransparencyPanel';

export function AskPage() {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [streamKey, setStreamKey] = useState(0);
  const [statusBarStatus, setStatusBarStatus] = useState<StreamStatus>('idle');
  const [, setStatusBarMessage] = useState('');
  const [externalCallMade, setExternalCallMade] = useState(false);
  const [callTimestamp, setCallTimestamp] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!query.trim()) return;
    setExternalCallMade(false);
    setCallTimestamp(null);
    setStreamKey((k) => k + 1);
    setSubmitted(true);
  };

  const handleStatusChange = useCallback((status: StreamStatus, message?: string) => {
    setStatusBarStatus(status);
    if (message) setStatusBarMessage(message);
  }, []);

  const handleExternalCall = useCallback(() => {
    setExternalCallMade(true);
    setCallTimestamp(new Date().toISOString());
  }, []);

  const isRunning =
    statusBarStatus === 'connecting' ||
    statusBarStatus === 'running' ||
    statusBarStatus === 'evidence' ||
    statusBarStatus === 'reasoning' ||
    statusBarStatus === 'streaming';

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          ASK MODE
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Read-only clinical Q&A. Stateless. SSE streaming.
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
          CLINICAL QUERY
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. What are differential diagnoses for bilateral joint pain?"
          className="w-full p-3 rounded border text-sm font-mono resize-y"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
            minHeight: '80px',
          }}
          disabled={isRunning}
        />
        <div className="flex justify-end mt-3">
          <button
            onClick={handleSubmit}
            disabled={!query.trim() || isRunning}
            className="px-4 py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: 'var(--accent-green)',
              color: '#000',
            }}
          >
            {isRunning ? 'RUNNING...' : 'SUBMIT QUERY'}
          </button>
        </div>
      </div>

      <div className="mb-4">
        <TransparencyPanel
          externalCallMade={externalCallMade}
          callTimestamp={callTimestamp}
        />
      </div>

      {submitted && (
        <StreamingDisplay
          key={streamKey}
          endpoint="/api/rag/ask_stream"
          params={{
            q: query,
            limit: 12,
            with_llm: 1,
            llm_mode: 'chunk',
          }}
          mode="ask"
          active={true}
          onStatusChange={handleStatusChange}
          onExternalCall={handleExternalCall}
        />
      )}
    </div>
  );
}
