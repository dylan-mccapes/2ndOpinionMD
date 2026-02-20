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
    setSymptoms(prev => [...prev, { symptom: symptomName.trim(), severity: clamp1to10(symptomSeverity) }]);
    setSymptomName('');
    setSymptomSeverity(5);
  };

  const removeSymptom = (idx: number) => {
    setSymptoms(prev => prev.filter((_, i) => i !== idx));
  };

  const addEnvFactor = () => {
    if (!envType.trim() || !envDesc.trim()) return;
    setEnvFactors(prev => [...prev, { factor_type: envType.trim(), description: envDesc.trim() }]);
    setEnvType('');
    setEnvDesc('');
  };

  const removeEnvFactor = (idx: number) => {
    setEnvFactors(prev => prev.filter((_, i) => i !== idx));
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
    if (symptoms.length > 0) body.symptoms = symptoms.map(s => ({ ...s, severity: clamp1to10(s.severity) }));
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

  const hasContent = notes.trim() || symptoms.length > 0 || envFactors.length > 0 || stressLevel !== '' || dietNotes.trim() || sleepQuality !== '';

  return (
    <div
      className="p-4 rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left cursor-pointer"
        style={{ background: 'none', border: 'none', color: 'var(--text-primary)' }}
      >
        <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
          NEW JOURNAL ENTRY
        </span>
        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {expanded ? '[ COLLAPSE ]' : '[ EXPAND ]'}
        </span>
      </button>

      {expanded && (
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {error && (
            <div
              className="p-3 rounded text-sm font-mono"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
            >
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
              NOTES
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              className="w-full p-2 rounded border text-sm font-mono resize-y"
              style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              placeholder="Describe how you feel today, any observations, symptoms..."
            />
          </div>

          <div>
            <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
              SYMPTOMS ({symptoms.length})
            </label>
            {symptoms.map((s, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono flex-1" style={{ color: 'var(--text-primary)' }}>
                  {s.symptom} — severity {s.severity}/10
                </span>
                <button
                  type="button"
                  onClick={() => removeSymptom(i)}
                  className="text-xs font-mono px-1 cursor-pointer"
                  style={{ background: 'none', border: 'none', color: 'var(--accent-red)' }}
                >
                  [X]
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={symptomName}
                onChange={(e) => setSymptomName(e.target.value)}
                className="flex-1 p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                placeholder="Symptom name"
              />
              <label className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>SEV:</label>
              <input
                type="number"
                min={1}
                max={10}
                value={symptomSeverity}
                onChange={(e) => setSymptomSeverity(clamp1to10(Number(e.target.value) || 1))}
                className="w-14 p-1.5 rounded border text-xs font-mono text-center"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              />
              <button
                type="button"
                onClick={addSymptom}
                disabled={!symptomName.trim()}
                className="px-2 py-1 rounded text-xs font-mono cursor-pointer disabled:opacity-50"
                style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-green)', border: '1px solid var(--border-color)' }}
              >
                ADD
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
              ENVIRONMENTAL FACTORS ({envFactors.length})
            </label>
            {envFactors.map((f, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono flex-1" style={{ color: 'var(--text-primary)' }}>
                  {f.factor_type}: {f.description}
                </span>
                <button
                  type="button"
                  onClick={() => removeEnvFactor(i)}
                  className="text-xs font-mono px-1 cursor-pointer"
                  style={{ background: 'none', border: 'none', color: 'var(--accent-red)' }}
                >
                  [X]
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={envType}
                onChange={(e) => setEnvType(e.target.value)}
                className="w-28 p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                placeholder="Type (e.g. weather)"
              />
              <input
                type="text"
                value={envDesc}
                onChange={(e) => setEnvDesc(e.target.value)}
                className="flex-1 p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                placeholder="Description"
              />
              <button
                type="button"
                onClick={addEnvFactor}
                disabled={!envType.trim() || !envDesc.trim()}
                className="px-2 py-1 rounded text-xs font-mono cursor-pointer disabled:opacity-50"
                style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-green)', border: '1px solid var(--border-color)' }}
              >
                ADD
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
                STRESS LEVEL (1-10)
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={stressLevel}
                onChange={(e) => setStressLevel(e.target.value === '' ? '' : clamp1to10(Number(e.target.value)))}
                className="w-full p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
                SLEEP QUALITY (1-10)
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={sleepQuality}
                onChange={(e) => setSleepQuality(e.target.value === '' ? '' : clamp1to10(Number(e.target.value)))}
                className="w-full p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
              />
            </div>
            <div>
              <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
                DIET NOTES
              </label>
              <input
                type="text"
                value={dietNotes}
                onChange={(e) => setDietNotes(e.target.value)}
                className="w-full p-1.5 rounded border text-xs font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                placeholder="e.g. gluten-free, fasting"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={!hasContent || submitting}
            className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
          >
            {submitting ? 'SAVING ENTRY...' : 'SAVE JOURNAL ENTRY'}
          </button>
        </form>
      )}
    </div>
  );
}
