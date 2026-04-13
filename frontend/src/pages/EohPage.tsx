import { useState, useCallback } from 'react';
import { StreamingDisplay, type StreamStatus } from '../components/StreamingDisplay';
import { TransparencyPanel } from '../components/TransparencyPanel';
import { useStatusBar } from '../context/StatusBarContext';

export function EohPage() {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [streamKey, setStreamKey] = useState(0);
  const [statusBarStatus, setStatusBarStatus] = useState<StreamStatus>('idle');
  const statusBar = useStatusBar();
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
    const mapped = status === 'connecting' || status === 'running' || status === 'evidence' || status === 'reasoning' || status === 'streaming'
      ? 'running' as const
      : status === 'complete' ? 'complete' as const
      : status === 'error' ? 'error' as const
      : 'idle' as const;
    statusBar.setStatus(mapped, message);
  }, [statusBar]);

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
      <div className="mb-8">
        <h1
          className="text-xl font-mono font-bold mb-2"
          style={{ color: 'var(--accent-green)' }}
        >
          EoH MODE
        </h1>
        <p
          className="text-sm font-sans"
          style={{ color: 'var(--text-muted)' }}
        >
          Single Ethos-of-Health reasoning cycle. Hypothesis set + evidence
          weighting. SSE streaming.
        </p>
      </div>

      <div
        className="p-5 rounded-lg border mb-6"
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
          className="w-full p-3 rounded-lg border text-sm font-mono resize-y"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
            minHeight: '80px',
          }}
          disabled={isRunning}
        />
        <div className="flex justify-end mt-4">
          <button
            onClick={handleSubmit}
            disabled={!query.trim() || isRunning}
            className="px-4 py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: 'var(--accent-green)',
              color: '#000',
            }}
          >
            {isRunning ? 'RUNNING...' : 'RUN EoH'}
          </button>
        </div>
      </div>

      <div className="mb-6">
        <TransparencyPanel
          externalCallMade={externalCallMade}
          callTimestamp={callTimestamp}
        />
      </div>

      {submitted && (
        <StreamingDisplay
          key={streamKey}
          endpoint="/api/rag/eoh_stream"
          params={{
            q: query,
            limit: 10,
            with_llm: 1,
            llm_mode: 'chunk',
          }}
          mode="eoh"
          active={true}
          onStatusChange={handleStatusChange}
          onExternalCall={handleExternalCall}
        />
      )}
    </div>
  );
}
