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
import { apiUrl } from '../lib/api';
import { downloadBlob } from '../lib/download';
import { Button } from './ui/Button';

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
  /** POST = JSON body (backend privacy refactor); GET = query params (EventSource) */
  method?: 'GET' | 'POST';
  onStatusChange?: (status: StreamStatus, message?: string) => void;
  onExternalCall?: () => void;
}

function statusColor(s: StreamStatus): string {
  switch (s) {
    case 'connecting':
    case 'running':   return 'var(--accent-cyan)';
    case 'evidence':  return 'var(--accent-blue)';
    case 'reasoning':
    case 'streaming': return 'var(--accent-yellow)';
    case 'complete':  return 'var(--accent-green)';
    case 'error':     return 'var(--accent-red)';
    default:          return 'var(--text-muted)';
  }
}

function processSseEvent(
  data: Record<string, unknown>,
  handlers: {
    updateStatus: (s: StreamStatus, msg?: string) => void;
    setRetrieval: (r: RetrievalInfo | null) => void;
    setCompletion: (c: CompletionInfo | null) => void;
    setConfidence: (c: number | null) => void;
    setLimitations: (l: string[]) => void;
    answerRef: { current: string };
    setAnswer: (a: string) => void;
  },
) {
  const event = data.event as string | undefined;
  const { updateStatus, setRetrieval, setCompletion, setConfidence, setLimitations, answerRef, setAnswer } = handlers;

  if (event === 'phase_start') {
    updateStatus('running', 'RUNNING');
  } else if (event === 'event_router_summary') {
    const sources = (data.effective_sources as string[]) ?? [];
    const n = sources.length;
    const info: RetrievalInfo = {
      sources_considered: n,
      sources_used: n,
      confidence: 'medium',
    };
    setRetrieval(info);
    updateStatus(
      'evidence',
      `Evidence: ${n} sources, confidence: ${info.confidence}`,
    );
  } else if (event === 'retrieval_summary') {
    const info: RetrievalInfo = {
      sources_considered: (data.sources_considered as number) ?? 0,
      sources_used: (data.sources_used as number) ?? 0,
      confidence: (data.confidence as string) ?? 'medium',
    };
    setRetrieval(info);
    updateStatus(
      'evidence',
      `Evidence: ${info.sources_used}/${info.sources_considered} sources, confidence: ${info.confidence}`,
    );
  } else if (event === 'reasoning_progress' || event === 'status') {
    const step = (data.step ?? (data.status as string)) ?? '';
    if (step) updateStatus('reasoning', String(step));
  } else if (event === 'llm_chunk' || event === 'llm_delta') {
    const content = (data.content ?? data.text ?? '') as string;
    answerRef.current += content;
    setAnswer(answerRef.current);
    updateStatus('streaming');
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
  } else if (event === 'completion' || event === 'done' || event === 'end') {
    const meta = data.meta as Record<string, unknown> | undefined;
    const tokens_used = (data.tokens_used ?? meta?.tokens_used ?? 0) as number;
    const duration_ms = (data.duration_ms ?? meta?.duration_ms ?? 0) as number;
    const n_ctx = (meta?.n_ctx_total as number) ?? 0;
    const info: CompletionInfo = {
      tokens_used: tokens_used || (n_ctx as number),
      duration_ms,
    };
    setCompletion(info);
    updateStatus(
      'complete',
      duration_ms
        ? `Complete — ${tokens_used || ''} tokens, ${duration_ms}ms`
        : `Complete — ${n_ctx} context rows`,
    );
  }
}

export function StreamingDisplay({
  endpoint,
  params,
  mode,
  active,
  method = 'POST',
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
  const abortRef = useRef<AbortController | null>(null);
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

    updateStatus('connecting', 'Connecting...');
    onExternalCall?.();

    const baseUrl = apiUrl(endpoint);

    const handlers = {
      updateStatus,
      setRetrieval,
      setCompletion,
      setConfidence,
      setLimitations,
      answerRef,
      setAnswer,
    };

    const handleSseData = (data: Record<string, unknown>) => {
      addReceiptEvent('event', mode, { sse_event: data });
      processSseEvent(data, handlers);
    };

    if (method === 'POST') {
      const ac = new AbortController();
      abortRef.current = ac;

      fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(params),
        signal: ac.signal,
      })
        .then(async (res) => {
          if (!res.ok) {
            addReceiptEvent('error', mode, { action: 'connection_error', status: res.status });
            finalizeReceipt();
            setError(`Connection error: ${res.status}`);
            updateStatus('error', `Connection error: ${res.status}`);
            return;
          }
          addReceiptEvent('event', mode, { action: 'connection_opened' });

          const reader = res.body?.getReader();
          if (!reader) {
            setError('No response body');
            updateStatus('error', 'No response body');
            finalizeReceipt();
            return;
          }

          const decoder = new TextDecoder();
          let buffer = '';
          let currentEvent = '';
          let currentData = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split(/\r?\n/);
            buffer = lines.pop() ?? '';
            for (const line of lines) {
              if (line.startsWith('event: ')) {
                currentEvent = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                currentData = line.slice(6).trim();
              } else if (line.trim() === '' && currentData) {
                try {
                  const payload = JSON.parse(currentData) as Record<string, unknown>;
                  const data = { ...payload, event: currentEvent || payload.event };
                  handleSseData(data);
                  if (data.event === 'completion' || data.event === 'done' || data.event === 'end') {
                    finalizeReceipt();
                    return;
                  }
                } catch {
                  addReceiptEvent('event', mode, { raw: currentData });
                }
                currentEvent = '';
                currentData = '';
              }
            }
          }
          finalizeReceipt();
        })
        .catch((err) => {
          if (err?.name === 'AbortError') return;
          addReceiptEvent('error', mode, { action: 'connection_error' });
          finalizeReceipt();
          setError('Connection error');
          updateStatus('error', 'Connection error');
        });

      return () => {
        ac.abort();
        abortRef.current = null;
      };
    }

    const url = new URL(baseUrl, window.location.origin);
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }
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
      handleSseData(data);
      if (data.event === 'completion' || data.event === 'done') {
        const info: CompletionInfo = {
          tokens_used: (data.tokens_used ?? 0) as number,
          duration_ms: (data.duration_ms ?? 0) as number,
        };
        setCompletion(info);
        finalizeReceipt();
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
    downloadBlob(
      exportReceiptJSON(),
      `receipt-${mode}-${Date.now()}.json`,
      'application/json',
    );
  }

  function handleExportHTML() {
    downloadBlob(
      exportReceiptHTML(),
      `receipt-${mode}-${Date.now()}.html`,
      'text/html',
    );
  }

  if (status === 'idle') {
    return null;
  }

  return (
    <div className="space-y-4">
      <div
        className="px-5 py-3 rounded border text-sm font-mono bg-[var(--bg-secondary)] flex items-center gap-2"
        style={{
          borderColor: statusColor(status),
          color: statusColor(status),
        }}
      >
        {(status === 'connecting' || status === 'running' || status === 'reasoning' || status === 'streaming') && (
          <span
            className="inline-block w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0"
            style={{ backgroundColor: statusColor(status) }}
          />
        )}
        {statusText}
      </div>

      {retrieval && (
        <div
          className="px-5 py-3 rounded border text-xs font-mono bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-secondary)]"
        >
          Sources: {retrieval.sources_used}/{retrieval.sources_considered} |
          Retrieval confidence: {retrieval.confidence}
        </div>
      )}

      {error && (
        <div
          className="p-5 rounded border bg-[var(--bg-secondary)] border-[var(--accent-red)] text-[var(--accent-red)]"
        >
          <p className="text-sm font-mono font-bold mb-1">ERROR</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {answer && (
        <div className="animate-fade-in">
          <div
            className="p-5 rounded border prose prose-sm max-w-none bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)]"
          >
            <div className="relative">
              <Markdown>{answer}</Markdown>
              {status === 'streaming' && (
                <span
                  className="inline-block animate-blink text-[var(--accent-green)] select-none"
                  aria-hidden="true"
                >
                  ▌
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {limitations.length > 0 && (
        <div
          className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--accent-yellow)]"
        >
          <p className="text-xs font-mono font-bold mb-2 text-[var(--accent-yellow)]">
            LIMITATIONS
          </p>
          <ul className="space-y-1">
            {limitations.map((lim, i) => (
              <li key={i} className="text-xs font-mono text-[var(--text-secondary)]">
                — {lim}
              </li>
            ))}
          </ul>
        </div>
      )}

      {confidence !== null && status === 'complete' && (
        <div
          className="px-5 py-3 rounded border text-xs font-mono bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-secondary)]"
        >
          Confidence: {Math.round(confidence * 100)}%
          {completion &&
            ` | ${completion.tokens_used} tokens | ${completion.duration_ms}ms`}
        </div>
      )}

      {(status === 'complete' || status === 'error') && (
        <div className="flex items-center gap-3 flex-wrap">
          <Button onClick={() => setShowReceipts(!showReceipts)} variant="secondary" size="md">
            {showReceipts ? 'HIDE RECEIPTS' : 'SHOW RECEIPTS'}
          </Button>
          <Button onClick={handleExportJSON} variant="secondary" size="md">
            EXPORT JSON
          </Button>
          <Button onClick={handleExportHTML} variant="secondary" size="md">
            EXPORT HTML
          </Button>
        </div>
      )}

      {showReceipts && (
        <div
          className="p-5 rounded border overflow-auto bg-[var(--bg-tertiary)] border-[var(--border-color)] max-h-96"
        >
          <pre className="text-xs font-mono whitespace-pre-wrap text-[var(--text-secondary)]">
            {JSON.stringify(getReceipt(), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
