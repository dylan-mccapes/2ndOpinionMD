import { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface SymptomInput {
  symptom: string;
  severity: number;
}

interface JournalEntryCreate {
  symptoms?: SymptomInput[];
  environmental_factors?: { factor_type: string; description: string }[];
  stress_level?: number;
  diet_notes?: string;
  sleep_quality?: number;
  notes?: string;
}

interface JournalEditorProps {
  onEntryCreated: () => void;
}

function severityColor(sev: number): string {
  if (sev <= 3) return 'var(--accent-green)';
  if (sev <= 6) return 'var(--accent-yellow)';
  return 'var(--accent-red)';
}

export function JournalEditor({ onEntryCreated }: JournalEditorProps) {
  const { token } = useAuth();
  const [notes, setNotes] = useState('');
  const [symptoms, setSymptoms] = useState<SymptomInput[]>([]);
  const [symptomName, setSymptomName] = useState('');
  const [symptomSeverity, setSymptomSeverity] = useState(5);
  const [envFactors, setEnvFactors] = useState<{ factor_type: string; description: string }[]>([]);
  const [envType, setEnvType] = useState('');
  const [envDesc, setEnvDesc] = useState('');
  const [stressLevel, setStressLevel] = useState<number | ''>('');
  const [dietNotes, setDietNotes] = useState('');
  const [sleepQuality, setSleepQuality] = useState<number | ''>('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);

  const clamp1to10 = (n: number): number => Math.min(10, Math.max(1, Math.round(n)));

  const addSymptom = () => {
    if (!symptomName.trim()) return;
    setSymptoms((prev) => [...prev, { symptom: symptomName.trim(), severity: clamp1to10(symptomSeverity) }]);
    setSymptomName('');
    setSymptomSeverity(5);
  };

  const addEnvFactor = () => {
    if (!envType.trim() || !envDesc.trim()) return;
    setEnvFactors((prev) => [...prev, { factor_type: envType.trim(), description: envDesc.trim() }]);
    setEnvType('');
    setEnvDesc('');
  };

  const resetForm = () => {
    setNotes('');
    setSymptoms([]);
    setSymptomName('');
    setSymptomSeverity(5);
    setEnvFactors([]);
    setEnvType('');
    setEnvDesc('');
    setStressLevel('');
    setDietNotes('');
    setSleepQuality('');
    setError('');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError('');
    setSubmitting(true);

    const body: JournalEntryCreate = {};
    if (notes.trim()) body.notes = notes.trim();
    if (symptoms.length > 0) body.symptoms = symptoms.map((s) => ({ ...s, severity: clamp1to10(s.severity) }));
    if (envFactors.length > 0) body.environmental_factors = envFactors;
    if (stressLevel !== '') body.stress_level = clamp1to10(Number(stressLevel));
    if (dietNotes.trim()) body.diet_notes = dietNotes.trim();
    if (sleepQuality !== '') body.sleep_quality = clamp1to10(Number(sleepQuality));

    try {
      await apiFetch('/api/journal', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      resetForm();
      setExpanded(false);
      onEntryCreated();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to create entry');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const hasContent =
    notes.trim() || symptoms.length > 0 || envFactors.length > 0 ||
    stressLevel !== '' || dietNotes.trim() || sleepQuality !== '';

  return (
    <div
      className="rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      {/* Collapse toggle */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-5 text-left cursor-pointer transition-colors"
        style={{ background: 'none', border: 'none' }}
      >
        <div>
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
            NEW ENTRY
          </span>
          <p className="text-xs font-sans mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Log symptoms, scores, and observations
          </p>
        </div>
        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {expanded ? '[ COLLAPSE ]' : '[ EXPAND ]'}
        </span>
      </button>

      {expanded && (
        <div style={{ borderTop: '1px solid var(--border-color)' }}>
          <form onSubmit={handleSubmit} className="px-6 py-6 space-y-6">
            {error && (
              <div className="p-4 rounded text-sm font-sans" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}>
                {error}
              </div>
            )}

            {/* Notes */}
            <div>
              <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                className="w-full px-4 py-3 rounded border text-sm font-sans resize-y"
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
                placeholder="How are you feeling today? Any notable symptoms or observations…"
              />
            </div>

            {/* Symptoms */}
            <div>
              <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Symptoms {symptoms.length > 0 && <span style={{ color: 'var(--accent-green)' }}>({symptoms.length})</span>}
              </label>
              {symptoms.length > 0 && (
                <div className="space-y-1.5 mb-3">
                  {symptoms.map((s, i) => (
                    <div key={i} className="flex items-center justify-between px-3 py-2 rounded" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-sans" style={{ color: 'var(--text-primary)' }}>{s.symptom}</span>
                        <span className="text-xs font-mono" style={{ color: severityColor(s.severity) }}>{s.severity}/10</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSymptoms((prev) => prev.filter((_, idx) => idx !== i))}
                        className="text-xs font-mono cursor-pointer"
                        style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={symptomName}
                  onChange={(e) => setSymptomName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSymptom())}
                  className="flex-1 px-4 py-2.5 rounded border text-sm font-sans"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="Symptom name"
                />
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>Sev.</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={symptomSeverity}
                    onChange={(e) => setSymptomSeverity(clamp1to10(Number(e.target.value) || 1))}
                    className="w-14 px-2 py-2.5 rounded border text-sm font-mono text-center"
                    style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  />
                </div>
                <button
                  type="button"
                  onClick={addSymptom}
                  disabled={!symptomName.trim()}
                  className="px-4 py-2.5 rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50"
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-green)', border: '1px solid var(--border-color)' }}
                >
                  ADD
                </button>
              </div>
            </div>

            {/* Scores row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                  Stress level
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  placeholder="1 – 10"
                  value={stressLevel}
                  onChange={(e) => setStressLevel(e.target.value === '' ? '' : clamp1to10(Number(e.target.value)))}
                  className="w-full px-4 py-2.5 rounded border text-sm font-mono"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                />
              </div>
              <div>
                <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                  Sleep quality
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  placeholder="1 – 10"
                  value={sleepQuality}
                  onChange={(e) => setSleepQuality(e.target.value === '' ? '' : clamp1to10(Number(e.target.value)))}
                  className="w-full px-4 py-2.5 rounded border text-sm font-mono"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                />
              </div>
              <div>
                <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                  Diet notes
                </label>
                <input
                  type="text"
                  value={dietNotes}
                  onChange={(e) => setDietNotes(e.target.value)}
                  className="w-full px-4 py-2.5 rounded border text-sm font-sans"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="e.g. gluten-free"
                />
              </div>
            </div>

            {/* Environmental factors */}
            <div>
              <label className="block text-xs font-sans font-medium uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Environmental factors {envFactors.length > 0 && <span style={{ color: 'var(--accent-green)' }}>({envFactors.length})</span>}
              </label>
              {envFactors.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {envFactors.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded" style={{ backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}>
                      <span className="text-xs font-sans" style={{ color: 'var(--text-secondary)' }}>
                        {f.factor_type}: {f.description}
                      </span>
                      <button
                        type="button"
                        onClick={() => setEnvFactors((prev) => prev.filter((_, idx) => idx !== i))}
                        className="text-xs cursor-pointer"
                        style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={envType}
                  onChange={(e) => setEnvType(e.target.value)}
                  className="w-32 px-4 py-2.5 rounded border text-sm font-sans"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="Type"
                />
                <input
                  type="text"
                  value={envDesc}
                  onChange={(e) => setEnvDesc(e.target.value)}
                  className="flex-1 px-4 py-2.5 rounded border text-sm font-sans"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="Description"
                />
                <button
                  type="button"
                  onClick={addEnvFactor}
                  disabled={!envType.trim() || !envDesc.trim()}
                  className="px-4 py-2.5 rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50"
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-green)', border: '1px solid var(--border-color)' }}
                >
                  ADD
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={!hasContent || submitting}
              className="w-full py-3 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
            >
              {submitting ? 'SAVING…' : 'SAVE ENTRY'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
