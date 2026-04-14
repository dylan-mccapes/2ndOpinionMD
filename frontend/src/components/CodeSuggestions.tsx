import { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { DS } from '../lib/ui';

export interface SuggestedCode {
  code: string;
  description: string;
  system: string;
  confidence: number;
  accepted: boolean;
  category: string;
}

interface CodeSuggestionsProps {
  transcript: string;
  token: string;
  enabled: boolean;
  onCodesChange?: (codes: SuggestedCode[]) => void;
}

interface CodingCategory {
  label: string;
  key: string;
}

const CATEGORIES: CodingCategory[] = [
  { key: 'probable_dx', label: 'PROBABLE DIAGNOSES' },
  { key: 'differential_dx', label: 'DIFFERENTIAL DIAGNOSES' },
  { key: 'procedures', label: 'PROCEDURES' },
  { key: 'labs', label: 'LABS' },
  { key: 'medications', label: 'MEDICATIONS' },
];

const RECODE_INTERVAL_MS = 60_000;

export function CodeSuggestions({ transcript, token, enabled, onCodesChange }: CodeSuggestionsProps) {
  const [codes, setCodes] = useState<SuggestedCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastCoded, setLastCoded] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTranscriptRef = useRef('');

  const fetchCodes = useCallback(async (text: string) => {
    if (!text.trim() || !token) return;
    setLoading(true);
    setError('');

    try {
      const res = await apiFetch<Record<string, unknown>>('/api/rag/coding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ note: text, limit: 60 }),
      });

      const newCodes: SuggestedCode[] = [];
      for (const cat of CATEGORIES) {
        const items = res[cat.key];
        if (Array.isArray(items)) {
          for (const item of items) {
            const rec = item as Record<string, unknown>;
            newCodes.push({
              code: (rec.code ?? '') as string,
              description: (rec.title ?? rec.description ?? rec.name ?? '') as string,
              system: (rec.system ?? '') as string,
              confidence: (rec.confidence ?? rec.score ?? 0.7) as number,
              accepted: false,
              category: cat.key,
            });
          }
        }
      }

      setCodes((prev) => {
        const acceptedSet = new Set(
          prev.filter((c) => c.accepted).map((c) => `${c.system}::${c.code}`),
        );
        return newCodes.map((c) => ({
          ...c,
          accepted: acceptedSet.has(`${c.system}::${c.code}`),
        }));
      });
      setLastCoded(new Date().toLocaleTimeString());
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `API ${err.status}: ${err.body}`
          : err instanceof Error
            ? err.message
            : 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!enabled || !transcript.trim()) return;

    if (transcript !== lastTranscriptRef.current && transcript.length > 50) {
      lastTranscriptRef.current = transcript;
      fetchCodes(transcript);
    }

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (transcript.trim().length > 50) {
        fetchCodes(transcript);
      }
    }, RECODE_INTERVAL_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [transcript, enabled, fetchCodes]);

  useEffect(() => {
    onCodesChange?.(codes);
  }, [codes, onCodesChange]);

  const toggleCode = (index: number) => {
    setCodes((prev) =>
      prev.map((c, i) => (i === index ? { ...c, accepted: !c.accepted } : c)),
    );
  };

  const acceptedCount = codes.filter((c) => c.accepted).length;

  if (codes.length === 0 && !loading && !error) {
    return null;
  }

  const groupedCodes = CATEGORIES.map((cat) => ({
    ...cat,
    items: codes
      .map((c, idx) => ({ ...c, globalIndex: idx }))
      .filter((c) => c.category === cat.key),
  })).filter((g) => g.items.length > 0);

  return (
    <div
      className="rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <span className="text-xs font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
          CODE SUGGESTIONS
        </span>
        <div className="flex items-center gap-3">
          {lastCoded && (
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              Last coded: {lastCoded}
            </span>
          )}
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {acceptedCount} accepted
          </span>
          {loading && (
            <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
              Coding...
            </span>
          )}
        </div>
      </div>

      <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: DS.gap.xl }}>
        {error && (
          <div
            className="p-3 rounded border"
            style={{ borderColor: 'var(--accent-red)', backgroundColor: 'var(--bg-tertiary)' }}
          >
            <p className="text-xs font-mono" style={{ color: 'var(--accent-red)' }}>
              {error}
            </p>
          </div>
        )}

        {groupedCodes.map((group, idx) => (
          <div
            key={group.key}
            style={{
              ...DS.track.cyan,
              paddingLeft: '0.9rem',
              paddingTop: idx === 0 ? '0.35rem' : '1.5rem',
              paddingBottom: '1rem',
              borderTop: idx === 0 ? undefined : '1px solid var(--border-color)',
            }}
          >
            <h4
              className="text-xs font-mono font-bold tracking-wide"
              style={{ color: 'var(--text-secondary)', marginBottom: '0.85rem' }}
            >
              {group.label}
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: DS.gap.md }}>
              {group.items.map((item) => (
                <div
                  key={`${item.system}-${item.code}-${item.globalIndex}`}
                  className="flex items-center rounded border cursor-pointer"
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderColor: item.accepted ? 'var(--accent-green)' : 'var(--border-color)',
                    padding: '0.75rem 0.8rem',
                    gap: '0.8rem',
                  }}
                  onClick={() => toggleCode(item.globalIndex)}
                >
                  <div
                    className="flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center text-xs"
                    style={{
                      borderColor: item.accepted ? 'var(--accent-green)' : 'var(--border-color)',
                      backgroundColor: item.accepted ? 'var(--accent-green)' : 'transparent',
                      color: item.accepted ? '#000' : 'transparent',
                    }}
                  >
                    {item.accepted ? '✓' : ''}
                  </div>
                  <span
                    className="text-xs font-mono font-bold flex-shrink-0"
                    style={{ color: 'var(--accent-blue)' }}
                  >
                    {item.code}
                  </span>
                  <span
                    className="text-xs font-mono px-1 py-0.5 rounded flex-shrink-0"
                    style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}
                  >
                    {item.system}
                  </span>
                  <span
                    className="text-xs font-mono flex-1 truncate"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {item.description}
                  </span>
                  <span
                    className="text-xs font-mono flex-shrink-0"
                    style={{
                      textAlign: 'right',
                      minWidth: '3.2rem',
                      marginLeft: '0.5rem',
                      paddingRight: '0.2rem',
                      color:
                        item.confidence >= 0.8
                          ? 'var(--accent-green)'
                          : item.confidence >= 0.5
                            ? 'var(--accent-yellow)'
                            : 'var(--accent-red)',
                    }}
                  >
                    {Math.round(item.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {loading && codes.length === 0 && (
          <p className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
            Analyzing transcript for clinical codes...
          </p>
        )}
      </div>
    </div>
  );
}
