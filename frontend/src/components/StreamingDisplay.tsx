import { useEffect, useRef, useState } from 'react';
import Markdown from 'react-markdown';
import {
  startReceipt,
  addReceiptEvent,
  finalizeReceipt,
  getReceipt,
  exportReceiptJSON,
  exportReceiptHTML,
} from '../lib/receiptCache';

export type StreamStatus =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'evidence'
  | 'reasoning'
  | 'streaming'
  | 'complete'
  | 'error';

interface RetrievalInfo {
  sources_considered: number;
  sources_used: number;
  confidence: string;
}

interface CompletionInfo {
  tokens_used: number;
  duration_ms: number;
}

interface StreamingDisplayProps {
  endpoint: string;
  params: Record<string, string | number>;
  mode: string;
  active: boolean;
  onStatusChange?: (status: StreamStatus, message?: string) => void;
  onExternalCall?: () => void;
}

export function StreamingDisplay({
  endpoint,
  params,
  mode,
  active,
  onStatusChange,
  onExternalCall,
}: StreamingDisplayProps) {
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [statusText, setStatusText] = useState('');
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState<number | null>(null);
  const [limitations, setLimitations] = useState<string[]>([]);
  const [retrieval, setRetrieval] = useState<RetrievalInfo | null>(null);
  const [completion, setCompletion] = useState<CompletionInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showReceipts, setShowReceipts] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const answerRef = useRef('');

  function updateStatus(s: StreamStatus, msg?: string) {
    setStatus(s);
    if (msg) setStatusText(msg);
    onStatusChange?.(s, msg);
  }

  useEffect(() => {
    if (!active) return;

    setAnswer('');
    answerRef.current = '';
    setConfidence(null);
    setLimitations([]);
    setRetrieval(null);
    setCompletion(null);
    setError(null);
    setShowReceipts(false);

    startReceipt(mode);
    addReceiptEvent('event', mode, { action: 'query_submitted', params });

    const API_BASE = import.meta.env.VITE_API_BASE ?? '';
    const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }

    updateStatus('connecting', 'Connecting...');
    onExternalCall?.();

    const es = new EventSource(url.toString());
    eventSourceRef.current = es;

    es.onopen = () => {
      addReceiptEvent('event', mode, { action: 'connection_opened' });
    };

    es.onmessage = (ev) => {
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(ev.data);
      } catch {
        addReceiptEvent('event', mode, { raw: ev.data });
        return;
      }

      addReceiptEvent('event', mode, { sse_event: data });

      const event = data.event as string | undefined;

      if (event === 'phase_start') {
        updateStatus('running', 'RUNNING');
      } else if (event === 'retrieval_summary') {
        const info: RetrievalInfo = {
          sources_considered: data.sources_considered as number,
          sources_used: data.sources_used as number,
          confidence: data.confidence as string,
        };
        setRetrieval(info);
        updateStatus(
          'evidence',
          `Evidence: ${info.sources_used}/${info.sources_considered} sources, confidence: ${info.confidence}`,
        );
      } else if (event === 'reasoning_progress') {
        updateStatus('reasoning', data.step as string);
      } else if (event === 'llm_chunk' || event === 'llm_delta') {
        const content = (data.content ?? data.text ?? '') as string;
        answerRef.current += content;
        setAnswer(answerRef.current);
        if (status !== 'streaming') {
          updateStatus('streaming');
        }
      } else if (event === 'llm_done' || event === 'final_answer') {
        if (data.text) {
          answerRef.current = data.text as string;
          setAnswer(answerRef.current);
        }
        if (data.confidence != null) {
          setConfidence(data.confidence as number);
        }
        if (Array.isArray(data.limitations)) {
          setLimitations(data.limitations as string[]);
        }
        updateStatus(
          'complete',
          `Complete — Confidence: ${data.confidence != null ? `${Math.round((data.confidence as number) * 100)}%` : 'N/A'}`,
        );
      } else if (event === 'completion' || event === 'done') {
        const info: CompletionInfo = {
          tokens_used: (data.tokens_used ?? 0) as number,
          duration_ms: (data.duration_ms ?? 0) as number,
        };
        setCompletion(info);
        finalizeReceipt();
        updateStatus(
          'complete',
          `Complete — ${info.tokens_used} tokens, ${info.duration_ms}ms`,
        );
        es.close();
      }
    };

    es.onerror = () => {
      addReceiptEvent('error', mode, { action: 'connection_error' });
      finalizeReceipt();
      setError('Connection error');
      updateStatus('error', 'Connection error');
      es.close();
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  function handleExportJSON() {
    const blob = new Blob([exportReceiptJSON()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `receipt-${mode}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function handleExportHTML() {
    const blob = new Blob([exportReceiptHTML()], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `receipt-${mode}-${Date.now()}.html`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (status === 'idle') {
    return null;
  }

  return (
    <div className="space-y-4">
      <div
        className="px-4 py-2 rounded border text-sm font-mono"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor:
            status === 'error'
              ? 'var(--accent-red)'
              : status === 'complete'
                ? 'var(--accent-green)'
                : 'var(--accent-yellow)',
          color:
            status === 'error'
              ? 'var(--accent-red)'
              : status === 'complete'
                ? 'var(--accent-green)'
                : 'var(--accent-yellow)',
        }}
      >
        {statusText}
      </div>

      {retrieval && (
        <div
          className="px-4 py-2 rounded border text-xs font-mono"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-secondary)',
          }}
        >
          Sources: {retrieval.sources_used}/{retrieval.sources_considered} |
          Retrieval confidence: {retrieval.confidence}
        </div>
      )}

      {error && (
        <div
          className="p-4 rounded border"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--accent-red)',
            color: 'var(--accent-red)',
          }}
        >
          <p className="text-sm font-mono font-bold mb-1">ERROR</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {answer && (
        <div
          className="p-4 rounded border prose prose-sm max-w-none"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
          }}
        >
          <Markdown>{answer}</Markdown>
        </div>
      )}

      {limitations.length > 0 && (
        <div
          className="p-3 rounded border"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--accent-yellow)',
          }}
        >
          <p
            className="text-xs font-mono font-bold mb-2"
            style={{ color: 'var(--accent-yellow)' }}
          >
            LIMITATIONS
          </p>
          <ul className="space-y-1">
            {limitations.map((lim, i) => (
              <li
                key={i}
                className="text-xs font-mono"
                style={{ color: 'var(--text-secondary)' }}
              >
                — {lim}
              </li>
            ))}
          </ul>
        </div>
      )}

      {confidence !== null && status === 'complete' && (
        <div
          className="px-4 py-2 rounded border text-xs font-mono"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-secondary)',
          }}
        >
          Confidence: {Math.round(confidence * 100)}%
          {completion &&
            ` | ${completion.tokens_used} tokens | ${completion.duration_ms}ms`}
        </div>
      )}

      {(status === 'complete' || status === 'error') && (
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowReceipts(!showReceipts)}
            className="text-xs font-mono px-3 py-1 rounded cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            {showReceipts ? 'HIDE RECEIPTS' : 'SHOW RECEIPTS'}
          </button>
          <button
            onClick={handleExportJSON}
            className="text-xs font-mono px-3 py-1 rounded cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            EXPORT JSON
          </button>
          <button
            onClick={handleExportHTML}
            className="text-xs font-mono px-3 py-1 rounded cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            EXPORT HTML
          </button>
        </div>
      )}

      {showReceipts && (
        <div
          className="p-4 rounded border overflow-auto"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderColor: 'var(--border-color)',
            maxHeight: '400px',
          }}
        >
          <pre
            className="text-xs font-mono whitespace-pre-wrap"
            style={{ color: 'var(--text-secondary)' }}
          >
            {JSON.stringify(getReceipt(), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
