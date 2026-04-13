import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { DS, PatientNav, SectionLabel, Divider, LeftTrack, Badge } from '../lib/ui';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface ModulePlanStep {
  step: number;
  goal: string;
  modules: string[];
  why: string;
}

interface DocRetrievalItem {
  module: string;
  handles: { kind: string; name: string }[];
  purpose: string;
}

interface RouterPlanResponse {
  question_type: string;
  question_type_explanation: string;
  module_plan: ModulePlanStep[];
  doc_retrieval_plan: DocRetrievalItem[];
}

interface FlareReportResponse {
  patient_id: string;
  window_days: number;
  flare_forecast: string;
  probabilistic_differential: Record<string, number>;
  precursor_signals: { signal: string; weight: number; description: string }[];
  contradictions: string[];
  risk_drivers: { driver: string; weight: number }[];
  timeline_summary: string;
  guidance_for_clinician: string[];
  safety_warnings?: string[];
}

function questionTypeColor(qt: string): string {
  switch (qt) {
    case 'A': return DS.color.red;
    case 'B': return DS.color.yellow;
    case 'C': return DS.color.blue;
    case 'D': return DS.color.green;
    default:  return DS.color.textSecondary;
  }
}

const CARD: React.CSSProperties = {
  backgroundColor: DS.color.bgSecondary,
  border: DS.border,
  borderRadius: DS.radius,
  padding: DS.pad.card,
};

export function EohdPage() {
  const { token, isAuthenticated } = useAuth();
  const { status, loading: statusLoading } = useTimelineStatus();
  const navigate = useNavigate();

  const [query, setQuery]             = useState('');
  const [plan, setPlan]               = useState<RouterPlanResponse | null>(null);
  const [flareReport, setFlareReport] = useState<FlareReportResponse | null>(null);
  const [loading, setLoading]         = useState(false);
  const [flareLoading, setFlareLoading] = useState(false);
  const [error, setError]             = useState('');
  const [flareError, setFlareError]   = useState('');

  const hasTimeline = status?.has_timeline ?? false;
  const timelineId  = status?.timeline_id  ?? null;

  if (statusLoading) {
    return (
      <div className="space-y-6">
        <p className="text-xs font-sans" style={{ color: DS.color.textMuted }}>Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="space-y-6">
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
          Please log in to access Detective mode.
        </p>
      </div>
    );
  }

  if (!hasTimeline) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-xl font-mono font-bold" style={{ color: DS.color.yellow, marginBottom: DS.mb.xs }}>
            DETECTIVE
          </h1>
          <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
            Timeline-aware EoH Detective reasoning.
          </p>
        </div>

        <PatientNav />

        <div className="rounded border" style={{ ...CARD, borderColor: DS.color.yellow, textAlign: 'center' }}>
          <p className="text-sm font-mono font-bold" style={{ color: DS.color.yellow, marginBottom: DS.mb.sm }}>
            TIMELINE REQUIRED
          </p>
          <p className="text-sm font-sans" style={{ color: DS.color.textSecondary, marginBottom: DS.mb.lg }}>
            Upload your patient timeline PDF to unlock Detective investigations.
          </p>
          <button
            type="button"
            onClick={() => navigate('/timeline/upload')}
            className="rounded text-sm font-mono font-bold cursor-pointer"
            style={{ padding: '0.625rem 1.25rem', backgroundColor: DS.color.green, color: '#000' }}
          >
            UPLOAD TIMELINE
          </button>
        </div>
      </div>
    );
  }

  const handlePlanQuery = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !query.trim()) return;
    setError('');
    setLoading(true);
    setPlan(null);
    try {
      const data = await apiFetch<RouterPlanResponse>('/api/eoh/router_plan', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: query.trim(),
          patient_state_summary: timelineId ? { timeline_patient_id: timelineId } : undefined,
        }),
      });
      setPlan(data);
    } catch (err) {
      setError(err instanceof ApiError ? `API ${err.status}: ${err.body}` : err instanceof Error ? err.message : 'Failed to generate plan');
    } finally {
      setLoading(false);
    }
  };

  const handleFlareReport = async () => {
    if (!token || !timelineId) return;
    setFlareError('');
    setFlareLoading(true);
    setFlareReport(null);
    try {
      const data = await apiFetch<FlareReportResponse>(`/api/eoh/flarereport/${timelineId}`, {
        headers: authHeaders(token),
      });
      setFlareReport(data);
    } catch (err) {
      setFlareError(err instanceof ApiError ? `API ${err.status}: ${err.body}` : err instanceof Error ? err.message : 'Failed to load flare report');
    } finally {
      setFlareLoading(false);
    }
  };

  return (
    <div className="space-y-8">

      {/* ── Page header ── */}
      <div>
        <h1 className="text-xl font-mono font-bold" style={{ color: DS.color.green, marginBottom: DS.mb.xs }}>
          DETECTIVE
        </h1>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
          Timeline-aware EoH Detective reasoning. {status?.event_count} events loaded.
        </p>
      </div>

      <PatientNav />

      <div className="space-y-8">

        {/* ── Router Query ── */}
        <div style={CARD}>
          <SectionLabel>EoH Router Query</SectionLabel>

          <form onSubmit={handlePlanQuery}>
            <div className="flex" style={{ gap: DS.gap.lg }}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 rounded border text-sm font-sans"
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: DS.color.bgTertiary,
                  borderColor: DS.color.border,
                  color: DS.color.textPrimary,
                }}
                placeholder="Ask a clinical question about the timeline…"
              />
              <button
                type="submit"
                disabled={!query.trim() || loading}
                className="rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                style={{ padding: '0.75rem 1.25rem', backgroundColor: DS.color.green, color: '#000' }}
              >
                {loading ? '…' : 'PLAN'}
              </button>
            </div>
          </form>

          {error && (
            <div
              className="rounded text-sm font-sans"
              style={{ marginTop: DS.mb.md, padding: DS.pad.inner, backgroundColor: DS.color.bgTertiary, color: DS.color.red }}
            >
              {error}
            </div>
          )}

          {plan && (
            <div style={{ marginTop: DS.mb.lg }}>
              {/* Question type */}
              <div className="flex items-center flex-wrap" style={{ gap: DS.gap.md, marginBottom: DS.mb.md }}>
                <span className="text-xs font-sans font-medium" style={{ color: DS.color.textMuted }}>
                  Question type
                </span>
                <Badge color={questionTypeColor(plan.question_type)} style={{ fontFamily: 'var(--font-mono)' }}>
                  {plan.question_type}
                </Badge>
                <span className="text-xs font-sans" style={{ color: DS.color.textMuted }}>
                  {plan.question_type_explanation}
                </span>
              </div>

              {/* Module plan */}
              {plan.module_plan.length > 0 && (
                <div style={{ marginBottom: DS.mb.md }}>
                  <SectionLabel>Execution Plan</SectionLabel>
                  <div className="space-y-3">
                    {plan.module_plan.map((step) => (
                      <LeftTrack key={step.step} color="green">
                        <div className="flex items-baseline" style={{ gap: DS.gap.md, marginBottom: DS.mb.xs }}>
                          <span className="text-xs font-mono font-bold" style={{ color: DS.color.green }}>
                            STEP {step.step}
                          </span>
                          <span className="text-xs font-sans" style={{ color: DS.color.textPrimary }}>
                            {step.goal}
                          </span>
                        </div>
                        <div className="flex flex-wrap" style={{ gap: DS.gap.sm, marginBottom: DS.mb.xs }}>
                          {step.modules.map((mod) => (
                            <Badge key={mod} color={DS.color.blue}>{mod}</Badge>
                          ))}
                        </div>
                        <p className="text-xs font-sans leading-relaxed" style={{ color: DS.color.textMuted }}>
                          {step.why}
                        </p>
                      </LeftTrack>
                    ))}
                  </div>
                </div>
              )}

              {/* Doc retrieval */}
              {plan.doc_retrieval_plan.length > 0 && (
                <div>
                  <SectionLabel>Data Retrieval</SectionLabel>
                  <div className="space-y-2">
                    {plan.doc_retrieval_plan.map((item, i) => (
                      <p key={i} className="text-xs font-sans leading-relaxed" style={{ color: DS.color.textMuted }}>
                        <span style={{ color: DS.color.blue }}>{item.module}</span>: {item.purpose}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Flare Report ── */}
        <div style={CARD}>
          <div className="flex items-center justify-between" style={{ marginBottom: DS.mb.lg }}>
            <SectionLabel style={{ marginBottom: 0 }}>Flare Report</SectionLabel>
            <button
              type="button"
              onClick={handleFlareReport}
              disabled={flareLoading}
              className="rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50"
              style={{ padding: '0.5rem 1rem', backgroundColor: DS.color.red, color: '#fff' }}
            >
              {flareLoading ? '…' : 'GENERATE'}
            </button>
          </div>

          {flareError && (
            <div
              className="rounded text-sm font-sans"
              style={{ padding: DS.pad.inner, backgroundColor: DS.color.bgTertiary, color: DS.color.red, marginBottom: DS.mb.md }}
            >
              {flareError}
            </div>
          )}

          {flareReport && (
            <div className="space-y-5">

              {/* Forecast */}
              <LeftTrack color="cyan">
                <p className="text-sm font-sans leading-relaxed" style={{ color: DS.color.textPrimary }}>
                  {flareReport.flare_forecast}
                </p>
              </LeftTrack>

              {/* Timeline summary */}
              {flareReport.timeline_summary && (
                <p className="text-xs font-sans leading-relaxed" style={{ color: DS.color.textMuted }}>
                  {flareReport.timeline_summary}
                </p>
              )}

              {/* Probabilistic differential */}
              {Object.keys(flareReport.probabilistic_differential).length > 0 && (
                <>
                  <Divider />
                  <div>
                    <SectionLabel>Diagnostic Landscape</SectionLabel>
                    <div className="space-y-3">
                      {Object.entries(flareReport.probabilistic_differential)
                        .sort(([, a], [, b]) => b - a)
                        .map(([dx, prob]) => (
                          <div key={dx}>
                            <div className="flex items-center justify-between" style={{ marginBottom: DS.mb.xs }}>
                              <span className="text-xs font-sans" style={{ color: DS.color.textPrimary }}>{dx}</span>
                              <span className="text-xs font-mono" style={{ color: DS.color.yellow }}>{(prob * 100).toFixed(1)}%</span>
                            </div>
                            <div
                              className="rounded-full"
                              style={{ height: '4px', backgroundColor: DS.color.bgTertiary, position: 'relative', overflow: 'hidden' }}
                            >
                              <div
                                style={{
                                  position: 'absolute', left: 0, top: 0, bottom: 0,
                                  width: `${prob * 100}%`,
                                  borderRadius: '9999px',
                                  backgroundColor: prob > 0.5 ? DS.color.red : prob > 0.25 ? DS.color.yellow : DS.color.blue,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </>
              )}

              {/* Precursor signals */}
              {flareReport.precursor_signals.length > 0 && (
                <>
                  <Divider />
                  <div>
                    <SectionLabel>Precursor Signals</SectionLabel>
                    <div className="space-y-2">
                      {flareReport.precursor_signals.map((sig, i) => (
                        <p
                          key={i}
                          className="text-xs font-sans leading-relaxed"
                          style={{ color: DS.color.textPrimary, borderLeft: `2px solid ${DS.color.yellow}`, paddingLeft: '0.75rem' }}
                        >
                          <span style={{ color: DS.color.yellow }}>{sig.signal}</span> — {sig.description}
                        </p>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Risk drivers */}
              {flareReport.risk_drivers.length > 0 && (
                <>
                  <Divider />
                  <div>
                    <SectionLabel>Risk Drivers</SectionLabel>
                    <div className="flex flex-wrap" style={{ gap: DS.gap.sm }}>
                      {flareReport.risk_drivers.map((d, i) => (
                        <Badge key={i} color={DS.color.red}>
                          {d.driver} ({(d.weight * 100).toFixed(0)}%)
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Contradictions */}
              {flareReport.contradictions.length > 0 && (
                <>
                  <Divider />
                  <div>
                    <SectionLabel style={{ color: DS.color.yellow }}>Contradictions</SectionLabel>
                    <div className="space-y-2">
                      {flareReport.contradictions.map((c, i) => (
                        <p key={i} className="text-xs font-sans leading-relaxed" style={{ color: DS.color.yellow }}>
                          {c}
                        </p>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Clinician guidance */}
              {flareReport.guidance_for_clinician.length > 0 && (
                <>
                  <Divider />
                  <div>
                    <SectionLabel>Clinician Guidance</SectionLabel>
                    <div className="space-y-2">
                      {flareReport.guidance_for_clinician.map((g, i) => (
                        <p key={i} className="text-xs font-sans leading-relaxed" style={{ color: DS.color.textMuted }}>
                          {g}
                        </p>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Safety warnings */}
              {flareReport.safety_warnings && flareReport.safety_warnings.length > 0 && (
                <>
                  <Divider />
                  <div
                    className="rounded"
                    style={{ padding: DS.pad.inner, backgroundColor: DS.color.bgTertiary, borderLeft: `3px solid ${DS.color.red}` }}
                  >
                    <SectionLabel style={{ color: DS.color.red }}>Safety Warnings</SectionLabel>
                    <div className="space-y-2">
                      {flareReport.safety_warnings.map((w, i) => (
                        <p key={i} className="text-xs font-sans leading-relaxed" style={{ color: DS.color.red }}>
                          {w}
                        </p>
                      ))}
                    </div>
                  </div>
                </>
              )}

            </div>
          )}
        </div>

      </div>
    </div>
  );
}
