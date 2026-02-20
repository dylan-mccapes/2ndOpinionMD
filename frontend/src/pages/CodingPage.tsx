import { useState, useCallback } from 'react';
import { CodingReview, type CodingStatus } from '../components/CodingReview';
import { TransparencyPanel } from '../components/TransparencyPanel';
import { useStatusBar } from '../context/StatusBarContext';

export function CodingPage() {
  const [note, setNote] = useState('');
  const [context, setContext] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [reviewKey, setReviewKey] = useState(0);
  const [codingStatus, setCodingStatus] = useState<CodingStatus>('idle');
  const statusBar = useStatusBar();
  const [externalCallMade, setExternalCallMade] = useState(false);
  const [callTimestamp, setCallTimestamp] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!note.trim()) return;
    setExternalCallMade(false);
    setCallTimestamp(null);
    setReviewKey((k) => k + 1);
    setSubmitted(true);
  };

  const handleStatusChange = useCallback((status: CodingStatus, message?: string) => {
    setCodingStatus(status);
    const mapped = status === 'loading' ? 'running' as const
      : status === 'complete' ? 'complete' as const
      : status === 'error' ? 'error' as const
      : 'idle' as const;
    statusBar.setStatus(mapped, message);
  }, [statusBar]);

  const handleExternalCall = useCallback(() => {
    setExternalCallMade(true);
    setCallTimestamp(new Date().toISOString());
  }, []);

  const isLoading = codingStatus === 'loading';

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-blue)' }}
        >
          CODING MODE
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Medical coding and classification. JSON REST.
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
          CLINICAL NOTE
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. 62F presenting with chest pain and dyspnea"
          className="w-full p-3 rounded border text-sm font-mono resize-y"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
            minHeight: '80px',
          }}
          disabled={isLoading}
        />

        <label
          className="block text-xs font-mono mb-2 mt-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          CONTEXT (optional)
        </label>
        <input
          type="text"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="e.g. Emergency department, initial encounter"
          className="w-full p-2 rounded border text-sm font-mono"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
          }}
          disabled={isLoading}
        />

        <div className="flex justify-end mt-3">
          <button
            onClick={handleSubmit}
            disabled={!note.trim() || isLoading}
            className="px-4 py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: 'var(--accent-blue)',
              color: '#fff',
            }}
          >
            {isLoading ? 'PROCESSING...' : 'SUBMIT NOTE'}
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
        <CodingReview
          key={reviewKey}
          note={note}
          context={context || undefined}
          active={true}
          onStatusChange={handleStatusChange}
          onExternalCall={handleExternalCall}
        />
      )}
    </div>
  );
}
