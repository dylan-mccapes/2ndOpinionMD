import { useState, useEffect, useRef } from 'react';
import {
  startReceipt,
  addReceiptEvent,
  finalizeReceipt,
  getReceipt,
  exportReceiptJSON,
  exportReceiptHTML,
} from '../lib/receiptCache';
import { apiFetch, ApiError } from '../lib/api';
import { downloadBlob } from '../lib/download';
import { Button } from './ui/Button';

interface CodeItem {
  code: string;
  description: string;
  system: string;
  confidence: number;
  accepted: boolean;
}

interface CodingCategory {
  label: string;
  key: string;
  items: CodeItem[];
}

interface CodingResponse {
  probable_dx?: CodeItem[];
  differential_dx?: CodeItem[];
  procedures?: CodeItem[];
  labs?: CodeItem[];
  medications?: CodeItem[];
  [key: string]: unknown;
}

export type CodingStatus = 'idle' | 'loading' | 'complete' | 'error';

interface CodingReviewProps {
  note: string;
  context?: string;
  active: boolean;
  onStatusChange?: (status: CodingStatus, message?: string) => void;
  onExternalCall?: () => void;
}

function parseItems(raw: unknown): CodeItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item: Record<string, unknown>) => ({
    code: (item.code ?? item.icd_code ?? item.snomed_code ?? item.loinc_code ?? item.rxcui ?? '') as string,
    description: (item.description ?? item.name ?? item.display ?? '') as string,
    system: (item.system ?? item.coding_system ?? '') as string,
    confidence: (item.confidence ?? item.score ?? 0) as number,
    accepted: false,
  }));
}

export function CodingReview({
  note,
  context,
  active,
  onStatusChange,
  onExternalCall,
}: CodingReviewProps) {
  const [status, setStatus] = useState<CodingStatus>('idle');
  const [categories, setCategories] = useState<CodingCategory[]>([]);
  const hasSubmittedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [showReceipts, setShowReceipts] = useState(false);
  const [exportConfirmed, setExportConfirmed] = useState(false);

  function updateStatus(s: CodingStatus, msg?: string) {
    setStatus(s);
    onStatusChange?.(s, msg);
  }

  async function submit() {
    setError(null);
    setCategories([]);
    setShowReceipts(false);
    setExportConfirmed(false);

    startReceipt('coding');
    addReceiptEvent('event', 'coding', { action: 'coding_requested', note, context });

    updateStatus('loading', 'Processing clinical note...');
    onExternalCall?.();

    try {
      const body: Record<string, unknown> = { note, limit: 60 };
      if (context) body.context = context;

      const res = await apiFetch<CodingResponse>('/api/coding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      addReceiptEvent('event', 'coding', { action: 'response_received', response: res });

      const cats: CodingCategory[] = [];
      const mapping: Array<{ key: string; label: string }> = [
        { key: 'probable_dx', label: 'PROBABLE DIAGNOSES' },
        { key: 'differential_dx', label: 'DIFFERENTIAL DIAGNOSES' },
        { key: 'procedures', label: 'PROCEDURES' },
        { key: 'labs', label: 'LABS' },
        { key: 'medications', label: 'MEDICATIONS' },
      ];

      for (const { key, label } of mapping) {
        const items = parseItems(res[key]);
        if (items.length > 0) {
          cats.push({ label, key, items });
        }
      }

      setCategories(cats);
      finalizeReceipt();
      addReceiptEvent('completion', 'coding', {
        action: 'completion',
        categories: cats.length,
        total_codes: cats.reduce((acc, c) => acc + c.items.length, 0),
      });
      updateStatus('complete', 'Coding complete');
    } catch (err) {
      const msg = err instanceof ApiError
        ? `API ${err.status}: ${err.body}`
        : (err instanceof Error ? err.message : 'Unknown error');
      addReceiptEvent('error', 'coding', { action: 'error', message: msg });
      finalizeReceipt();
      setError(msg);
      updateStatus('error', msg);
    }
  }

  function toggleItem(catIndex: number, itemIndex: number) {
    setCategories((prev) =>
      prev.map((cat, ci) =>
        ci === catIndex
          ? {
              ...cat,
              items: cat.items.map((item, ii) =>
                ii === itemIndex ? { ...item, accepted: !item.accepted } : item,
              ),
            }
          : cat,
      ),
    );
  }

  function getAcceptedCodes(): CodeItem[] {
    return categories.flatMap((cat) => cat.items.filter((item) => item.accepted));
  }

  function handleExportJSON() {
    const accepted = getAcceptedCodes();
    downloadBlob(
      JSON.stringify(accepted, null, 2),
      `coding-export-${Date.now()}.json`,
      'application/json',
    );
  }

  function escapeCsvField(val: string): string {
    return `"${String(val ?? '').replace(/"/g, '""')}"`;
  }

  function handleExportCSV() {
    const accepted = getAcceptedCodes();
    const header = 'code,description,system,confidence\n';
    const rows = accepted
      .map(
        (item) =>
          `${escapeCsvField(item.code)},${escapeCsvField(item.description)},${escapeCsvField(item.system)},${item.confidence}`,
      )
      .join('\n');
    downloadBlob(
      header + rows,
      `coding-export-${Date.now()}.csv`,
      'text/csv',
    );
  }

  function handleReceiptExportJSON() {
    downloadBlob(
      exportReceiptJSON(),
      `receipt-coding-${Date.now()}.json`,
      'application/json',
    );
  }

  function handleReceiptExportHTML() {
    downloadBlob(
      exportReceiptHTML(),
      `receipt-coding-${Date.now()}.html`,
      'text/html',
    );
  }

  useEffect(() => {
    if (active && !hasSubmittedRef.current) {
      hasSubmittedRef.current = true;
      submit();
    }
    return () => {
      hasSubmittedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  if (!active && status === 'idle') {
    return null;
  }

  if (active && status === 'idle') {
    return null;
  }

  const acceptedCount = getAcceptedCodes().length;

  return (
    <div className="space-y-4">
      {status === 'loading' && (
        <div
          className="px-4 py-2 rounded border text-sm font-mono bg-[var(--bg-secondary)] border-[var(--accent-yellow)] text-[var(--accent-yellow)]"
        >
          Processing clinical note...
        </div>
      )}

      {error && (
        <div
          className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--accent-red)]"
        >
          <p className="text-sm font-mono font-bold mb-1 text-[var(--accent-red)]">
            ERROR
          </p>
          <p className="text-sm text-[var(--accent-red)]">
            {error}
          </p>
        </div>
      )}

      {categories.map((cat, catIdx) => (
        <div key={cat.key}>
          <h3
            className="text-xs font-mono font-bold tracking-wide mb-2 text-[var(--text-secondary)]"
          >
            {cat.label}
          </h3>
          <div className="space-y-2">
            {cat.items.map((item, itemIdx) => (
              <div
                key={`${cat.key}-${itemIdx}`}
                className="flex items-start gap-3 p-3 rounded border cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: item.accepted
                    ? 'var(--accent-green)'
                    : 'var(--border-color)',
                }}
                onClick={() => toggleItem(catIdx, itemIdx)}
              >
                <div
                  className="flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center text-xs mt-0.5"
                  style={{
                    borderColor: item.accepted
                      ? 'var(--accent-green)'
                      : 'var(--border-color)',
                    backgroundColor: item.accepted
                      ? 'var(--accent-green)'
                      : 'transparent',
                    color: item.accepted ? '#000' : 'transparent',
                  }}
                >
                  {item.accepted ? '✓' : ''}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-sm font-mono font-bold"
                      style={{ color: 'var(--accent-blue)' }}
                    >
                      {item.code}
                    </span>
                    {item.system && (
                      <span
                        className="text-xs font-mono px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'var(--bg-tertiary)',
                          color: 'var(--text-muted)',
                        }}
                      >
                        {item.system}
                      </span>
                    )}
                  </div>
                  <p
                    className="text-sm"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {item.description}
                  </p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <div
                    className="text-xs font-mono"
                    style={{ color: item.confidence >= 0.8 ? 'var(--accent-green)' : item.confidence >= 0.5 ? 'var(--accent-yellow)' : 'var(--accent-red)' }}
                  >
                    {Math.round(item.confidence * 100)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {status === 'complete' && categories.length > 0 && (
        <div
          className="p-4 rounded border bg-[var(--bg-secondary)] border-[var(--border-color)]"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-mono text-[var(--text-secondary)]">
              {acceptedCount} code{acceptedCount !== 1 ? 's' : ''} accepted
            </span>
          </div>

          {!exportConfirmed ? (
            <Button
              onClick={() => setExportConfirmed(true)}
              disabled={acceptedCount === 0}
              variant="accent"
              size="md"
            >
              CONFIRM EXPORT ({acceptedCount})
            </Button>
          ) : (
            <div className="flex items-center gap-3">
              <Button onClick={handleExportJSON} variant="primary">
                EXPORT JSON
              </Button>
              <Button onClick={handleExportCSV} variant="primary">
                EXPORT CSV
              </Button>
              <Button onClick={() => setExportConfirmed(false)} variant="secondary">
                CANCEL
              </Button>
            </div>
          )}
        </div>
      )}

      {(status === 'complete' || status === 'error') && (
        <div className="flex items-center gap-3">
          <Button onClick={() => setShowReceipts(!showReceipts)} variant="secondary">
            {showReceipts ? 'HIDE RECEIPTS' : 'SHOW RECEIPTS'}
          </Button>
          <Button onClick={handleReceiptExportJSON} variant="secondary">
            RECEIPT JSON
          </Button>
          <Button onClick={handleReceiptExportHTML} variant="secondary">
            RECEIPT HTML
          </Button>
        </div>
      )}

      {showReceipts && (
        <div
          className="p-4 rounded border overflow-auto bg-[var(--bg-tertiary)] border-[var(--border-color)] max-h-96"
        >
          <pre className="text-xs font-mono whitespace-pre-wrap text-[var(--text-secondary)]">
            {JSON.stringify(getReceipt(), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
