import type { JournalEntryResponse } from './JournalEntryList';

interface JournalEntryDetailProps {
  entry: JournalEntryResponse;
  onClose: () => void;
}

function toPatternObservationsList(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val.map(String);
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      return Array.isArray(parsed) ? parsed.map(String) : [val];
    } catch {
      return val.split(/\n/).filter(Boolean).map(s => s.trim());
    }
  }
  return [];
}

function formatAiAnalysis(val: unknown): string {
  if (!val) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'object' && val !== null) {
    const o = val as Record<string, unknown>;
    if (typeof o.analysis === 'string') return o.analysis;
    return JSON.stringify(val, null, 2);
  }
  return String(val);
}

export function JournalEntryDetail({ entry, onClose }: JournalEntryDetailProps) {
  const severityColor = (sev: number): string => {
    if (sev <= 3) return 'var(--accent-green)';
    if (sev <= 6) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  return (
    <div
      className="p-4 rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-green)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
          ENTRY DETAIL
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-xs font-mono cursor-pointer"
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}
        >
          [CLOSE]
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>DATE: </span>
          <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
            {new Date(entry.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
        </div>

        {(entry.symptoms ?? []).length > 0 && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
              SYMPTOMS:
            </span>
            <div className="flex flex-wrap gap-1">
              {(entry.symptoms ?? []).map((s, i) => (
                <span
                  key={i}
                  className="text-xs font-mono px-2 py-1 rounded"
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: severityColor(s.severity) }}
                >
                  {s.symptom} — severity {s.severity}/10
                </span>
              ))}
            </div>
          </div>
        )}

        {(entry.environmental_factors ?? []).length > 0 && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
              ENVIRONMENTAL FACTORS:
            </span>
            <div className="flex flex-wrap gap-1">
              {(entry.environmental_factors ?? []).map((f, i) => (
                <span
                  key={i}
                  className="text-xs font-mono px-2 py-1 rounded"
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
                >
                  {[f.factor_type, f.description].filter(Boolean).join(': ')}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {typeof entry.stress_level === 'number' && (
            <div>
              <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>STRESS: </span>
              <span className="text-xs font-mono" style={{ color: severityColor(entry.stress_level) }}>
                {entry.stress_level}/10
              </span>
            </div>
          )}
          {typeof entry.sleep_quality === 'number' && (
            <div>
              <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>SLEEP: </span>
              <span className="text-xs font-mono" style={{ color: 'var(--accent-blue)' }}>
                {entry.sleep_quality}/10
              </span>
            </div>
          )}
          {entry.diet_notes && (
            <div>
              <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>DIET: </span>
              <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
                {entry.diet_notes}
              </span>
            </div>
          )}
        </div>

        {entry.notes && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
              NOTES:
            </span>
            <p
              className="text-xs font-mono whitespace-pre-wrap p-2 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
            >
              {entry.notes}
            </p>
          </div>
        )}

        {entry.analysis && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
              ANALYSIS:
            </span>
            <p
              className="text-xs font-mono whitespace-pre-wrap p-2 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
            >
              {entry.analysis}
            </p>
          </div>
        )}

        {toPatternObservationsList(entry.pattern_observations).length > 0 && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
              PATTERN OBSERVATIONS:
            </span>
            <ul className="space-y-1">
              {toPatternObservationsList(entry.pattern_observations).map((obs, i) => (
                <li
                  key={i}
                  className="text-xs font-mono pl-2"
                  style={{ color: 'var(--accent-yellow)', borderLeft: '2px solid var(--accent-yellow)' }}
                >
                  {obs}
                </li>
              ))}
            </ul>
          </div>
        )}

        {formatAiAnalysis(entry.ai_analysis) && (
          <div>
            <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--accent-blue)' }}>
              AI ANALYSIS:
            </span>
            <p
              className="text-xs font-mono whitespace-pre-wrap p-2 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', borderLeft: '2px solid var(--accent-blue)' }}
            >
              {formatAiAnalysis(entry.ai_analysis)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
