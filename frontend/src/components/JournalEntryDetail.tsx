import { useState } from 'react';
import { DS, SectionLabel, Divider, LeftTrack, Badge } from '../lib/ui';
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
      return val.split(/\n/).filter(Boolean).map((s) => s.trim());
    }
  }
  return [];
}

interface AiAnalysisParsed {
  summary: string;
  extras: { key: string; value: string }[];
}

function parseAiAnalysis(val: unknown): AiAnalysisParsed | null {
  if (!val) return null;
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (!trimmed) return null;
    return { summary: trimmed, extras: [] };
  }
  if (typeof val === 'object' && val !== null) {
    const o = val as Record<string, unknown>;
    const summary =
      typeof o.analysis === 'string' ? o.analysis
      : typeof o.summary  === 'string' ? o.summary
      : typeof o.response === 'string' ? o.response
      : '';
    const SKIP = new Set(['analysis', 'summary', 'response']);
    const extras: { key: string; value: string }[] = Object.entries(o)
      .filter(([k]) => !SKIP.has(k))
      .map(([k, v]) => ({
        key: k.replace(/_/g, ' '),
        value: Array.isArray(v)
          ? (v as unknown[]).join(', ')
          : typeof v === 'object' ? JSON.stringify(v) : String(v ?? ''),
      }))
      .filter(({ value }) => value);
    if (!summary && extras.length === 0) return null;
    return { summary, extras };
  }
  return null;
}

function severityColor(sev: number): string {
  if (sev <= 3) return DS.color.green;
  if (sev <= 6) return DS.color.yellow;
  return DS.color.red;
}

export function JournalEntryDetail({ entry, onClose }: JournalEntryDetailProps) {
  const [closeHover, setCloseHover] = useState(false);

  const aiAnalysis = parseAiAnalysis(entry.ai_analysis);
  const patterns   = toPatternObservationsList(entry.pattern_observations);
  const symptoms   = entry.symptoms ?? [];
  const envFactors = entry.environmental_factors ?? [];

  const formattedDate = new Date(entry.date).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const hasScores =
    typeof entry.stress_level === 'number' ||
    typeof entry.sleep_quality === 'number' ||
    !!entry.diet_notes;

  return (
    <div
      className="rounded border animate-fade-in"
      style={{ backgroundColor: DS.color.bgSecondary, borderColor: DS.color.border }}
    >
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between"
        style={{ padding: DS.pad.cardH, borderBottom: DS.border }}
      >
        <div>
          <p
            className="text-xs font-sans font-medium uppercase tracking-widest"
            style={{ color: DS.color.textMuted, marginBottom: DS.mb.xs }}
          >
            Clinical Note
          </p>
          <p className="text-base font-sans font-semibold" style={{ color: DS.color.textPrimary }}>
            {formattedDate}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          onMouseEnter={() => setCloseHover(true)}
          onMouseLeave={() => setCloseHover(false)}
          className="rounded text-xs font-mono font-bold cursor-pointer"
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: closeHover ? DS.color.bgPrimary : DS.color.bgTertiary,
            color: closeHover ? DS.color.green : DS.color.textSecondary,
            border: `1px solid ${closeHover ? DS.color.green : DS.color.border}`,
            transition: 'color 0.15s, border-color 0.15s, background-color 0.15s',
          }}
        >
          CLOSE
        </button>
      </div>

      {/* ── Body ── */}
      <div className="space-y-8" style={{ padding: DS.pad.card }}>

        {/* Scores */}
        {hasScores && (
          <div className="flex flex-wrap" style={{ gap: DS.gap['2xl'] }}>
            {typeof entry.stress_level === 'number' && (
              <div
                className="flex flex-col items-center justify-center rounded"
                style={{ padding: '0.75rem 1.25rem', backgroundColor: DS.color.bgTertiary, minWidth: '6rem' }}
              >
                <span className="text-xs font-sans" style={{ color: DS.color.textMuted, marginBottom: DS.mb.xs }}>
                  Stress
                </span>
                <span className="text-lg font-mono font-bold" style={{ color: severityColor(entry.stress_level) }}>
                  {entry.stress_level}
                  <span className="text-xs font-sans font-normal" style={{ color: DS.color.textMuted }}>/10</span>
                </span>
              </div>
            )}
            {typeof entry.sleep_quality === 'number' && (
              <div
                className="flex flex-col items-center justify-center rounded"
                style={{ padding: '0.75rem 1.25rem', backgroundColor: DS.color.bgTertiary, minWidth: '6rem' }}
              >
                <span className="text-xs font-sans" style={{ color: DS.color.textMuted, marginBottom: DS.mb.xs }}>
                  Sleep
                </span>
                <span className="text-lg font-mono font-bold" style={{ color: DS.color.blue }}>
                  {entry.sleep_quality}
                  <span className="text-xs font-sans font-normal" style={{ color: DS.color.textMuted }}>/10</span>
                </span>
              </div>
            )}
            {entry.diet_notes && (
              <div
                className="flex flex-col justify-center rounded"
                style={{ padding: '0.75rem 1.25rem', backgroundColor: DS.color.bgTertiary }}
              >
                <span className="text-xs font-sans" style={{ color: DS.color.textMuted, marginBottom: DS.mb.xs }}>
                  Diet
                </span>
                <span className="text-sm font-sans" style={{ color: DS.color.textPrimary }}>
                  {entry.diet_notes}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Symptoms */}
        {symptoms.length > 0 && (
          <>
            {hasScores && <Divider />}
            <LeftTrack color="yellow">
              <SectionLabel>Symptoms</SectionLabel>
              <div className="space-y-3">
                {symptoms.map((s, i) => (
                  <div key={i} className="flex items-center justify-between" style={{ gap: DS.gap.xl }}>
                    <span className="text-sm font-sans flex-1" style={{ color: DS.color.textPrimary }}>
                      {s.symptom}
                    </span>
                    <div className="flex items-center shrink-0" style={{ gap: DS.gap.lg }}>
                      {/* Severity bar */}
                      <div
                        className="rounded-full"
                        style={{
                          width: '5rem', height: '4px',
                          backgroundColor: DS.color.bgPrimary,
                          position: 'relative', overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            position: 'absolute', left: 0, top: 0, bottom: 0,
                            width: `${s.severity * 10}%`,
                            backgroundColor: severityColor(s.severity),
                            borderRadius: '9999px',
                          }}
                        />
                      </div>
                      <span
                        className="text-xs font-mono"
                        style={{ color: severityColor(s.severity), width: '2rem', textAlign: 'right' }}
                      >
                        {s.severity}/10
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </LeftTrack>
          </>
        )}

        {/* Environmental factors */}
        {envFactors.length > 0 && (
          <>
            <Divider />
            <div>
              <SectionLabel>Environmental factors</SectionLabel>
              <div className="flex flex-wrap" style={{ gap: DS.gap.md }}>
                {envFactors.map((f, i) => (
                  <Badge key={i}>
                    {[f.factor_type, f.description].filter(Boolean).join(' — ')}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Notes */}
        {entry.notes && (
          <>
            <Divider />
            <LeftTrack color="blue">
              <SectionLabel>Notes</SectionLabel>
              <p className="text-sm font-sans leading-relaxed" style={{ color: DS.color.textPrimary }}>
                {entry.notes}
              </p>
            </LeftTrack>
          </>
        )}

        {/* Pattern observations */}
        {patterns.length > 0 && (
          <>
            <Divider />
            <div>
              <SectionLabel>Pattern observations</SectionLabel>
              <ul className="space-y-3">
                {patterns.map((obs, i) => (
                  <li
                    key={i}
                    className="text-sm font-sans leading-relaxed"
                    style={{
                      color: DS.color.textPrimary,
                      borderLeft: `2px solid ${DS.color.yellow}`,
                      paddingLeft: DS.gap['2xl'],
                      paddingTop: '0.125rem',
                      paddingBottom: '0.125rem',
                    }}
                  >
                    {obs}
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}

        {/* Server analysis */}
        {entry.analysis && (
          <>
            <Divider />
            <LeftTrack color="cyan">
              <SectionLabel>Analysis</SectionLabel>
              <p className="text-sm font-sans leading-relaxed" style={{ color: DS.color.textPrimary }}>
                {entry.analysis}
              </p>
            </LeftTrack>
          </>
        )}

        {/* AI analysis */}
        {aiAnalysis && (
          <>
            <Divider />
            <LeftTrack color="blue">
              <SectionLabel>AI Analysis</SectionLabel>
              {aiAnalysis.summary && (
                <p
                  className="text-sm font-sans leading-relaxed"
                  style={{
                    color: DS.color.textPrimary,
                    marginBottom: aiAnalysis.extras.length ? DS.mb.xl : 0,
                  }}
                >
                  {aiAnalysis.summary}
                </p>
              )}
              {aiAnalysis.extras.length > 0 && (
                <div
                  className="rounded space-y-3"
                  style={{ padding: DS.pad.sm, backgroundColor: DS.color.bgTertiary }}
                >
                  {aiAnalysis.extras.map(({ key, value }) => (
                    <div key={key} className="flex" style={{ gap: DS.gap.xl }}>
                      <span
                        className="text-xs font-sans font-medium capitalize shrink-0"
                        style={{ color: DS.color.textMuted, width: '7rem' }}
                      >
                        {key}
                      </span>
                      <span className="text-xs font-sans" style={{ color: DS.color.textSecondary }}>
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </LeftTrack>
          </>
        )}

      </div>
    </div>
  );
}
