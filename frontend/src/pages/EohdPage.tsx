import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
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

export function EohdPage() {
  const { token, isAuthenticated } = useAuth();
  const { status, loading: statusLoading } = useTimelineStatus();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [plan, setPlan] = useState<RouterPlanResponse | null>(null);
  const [flareReport, setFlareReport] = useState<FlareReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [flareLoading, setFlareLoading] = useState(false);
  const [error, setError] = useState('');
  const [flareError, setFlareError] = useState('');

  const hasTimeline = status?.has_timeline ?? false;
  const timelineId = status?.timeline_id ?? null;

  if (statusLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto">
        <p className="text-sm font-sans" style={{ color: 'var(--text-muted)' }}>
          Please log in to access EoHD.
        </p>
      </div>
    );
  }

  if (!hasTimeline) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-xl font-mono font-bold mb-2" style={{ color: 'var(--accent-yellow)' }}>
            EoHD MODE
          </h1>
          <p className="text-sm font-sans" style={{ color: 'var(--text-muted)' }}>
            Timeline-aware EoH Detective reasoning.
          </p>
        </div>
        <div
          className="p-6 rounded-lg border text-center"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-yellow)' }}
        >
          <p className="text-sm font-mono mb-2" style={{ color: 'var(--accent-yellow)' }}>
            TIMELINE REQUIRED
          </p>
          <p className="text-sm font-sans mb-4" style={{ color: 'var(--text-secondary)' }}>
            Upload your patient timeline PDF to unlock EoHD investigations.
          </p>
          <button
            type="button"
            onClick={() => navigate('/timeline/upload')}
            className="px-6 py-2 rounded text-sm font-mono font-bold cursor-pointer"
            style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
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
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to generate plan');
      }
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
      if (err instanceof ApiError) {
        setFlareError(`API ${err.status}: ${err.body}`);
      } else {
        setFlareError(err instanceof Error ? err.message : 'Failed to load flare report');
      }
    } finally {
      setFlareLoading(false);
    }
  };

  const questionTypeColor = (qt: string): string => {
    switch (qt) {
      case 'A': return 'var(--accent-red)';
      case 'B': return 'var(--accent-yellow)';
      case 'C': return 'var(--accent-blue)';
      case 'D': return 'var(--accent-green)';
      case 'E': return 'var(--text-muted)';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-xl font-mono font-bold mb-2" style={{ color: 'var(--accent-green)' }}>
          EoHD MODE
        </h1>
        <p className="text-sm font-sans" style={{ color: 'var(--text-muted)' }}>
          Timeline-aware EoH Detective reasoning. {status?.event_count} events loaded.
        </p>
      </div>

      <div className="space-y-6">
        <div
          className="p-5 rounded-lg border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-4" style={{ color: 'var(--accent-green)' }}>
            EoH ROUTER QUERY
          </span>
          <form onSubmit={handlePlanQuery} className="space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 p-2 rounded-lg border text-sm font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                placeholder="Ask a clinical question about the timeline..."
              />
              <button
                type="submit"
                disabled={!query.trim() || loading}
                className="px-4 py-2 rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
              >
                {loading ? '...' : 'PLAN'}
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-3 p-3 rounded-lg text-sm font-mono" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}>
              {error}
            </div>
          )}

          {plan && (
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
                  QUESTION TYPE:
                </span>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded" style={{ color: questionTypeColor(plan.question_type), backgroundColor: 'var(--bg-tertiary)' }}>
                  {plan.question_type}
                </span>
                <span className="text-xs font-sans" style={{ color: 'var(--text-muted)' }}>
                  {plan.question_type_explanation}
                </span>
              </div>

              {plan.module_plan.length > 0 && (
                <div>
                  <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                    EXECUTION PLAN:
                  </span>
                  <div className="space-y-2">
                    {plan.module_plan.map((step) => (
                      <div key={step.step} className="pl-3" style={{ borderLeft: '2px solid var(--accent-green)' }}>
                        <span className="text-xs font-mono font-bold" style={{ color: 'var(--accent-green)' }}>
                          STEP {step.step}:
                        </span>
                        <span className="text-xs font-mono ml-1" style={{ color: 'var(--text-primary)' }}>
                          {step.goal}
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {step.modules.map((mod) => (
                            <span key={mod} className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-blue)' }}>
                              {mod}
                            </span>
                          ))}
                        </div>
                        <p className="text-xs font-sans leading-relaxed mt-1" style={{ color: 'var(--text-muted)' }}>
                          {step.why}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {plan.doc_retrieval_plan.length > 0 && (
                <div>
                  <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                    DATA RETRIEVAL:
                  </span>
                  {plan.doc_retrieval_plan.map((item, i) => (
                    <div key={i} className="text-xs font-sans leading-relaxed mb-1" style={{ color: 'var(--text-muted)' }}>
                      <span style={{ color: 'var(--accent-blue)' }}>{item.module}</span>: {item.purpose}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div
          className="p-5 rounded-lg border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-red)' }}>
              FLARE REPORT
            </span>
            <button
              type="button"
              onClick={handleFlareReport}
              disabled={flareLoading}
              className="px-3 py-1 rounded text-xs font-mono font-bold cursor-pointer disabled:opacity-50"
              style={{ backgroundColor: 'var(--accent-red)', color: '#000' }}
            >
              {flareLoading ? '...' : 'GENERATE'}
            </button>
          </div>

          {flareError && (
            <div className="p-3 rounded-lg text-sm font-mono" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}>
              {flareError}
            </div>
          )}

          {flareReport && (
            <div className="space-y-3">
              <div
                className="p-3 rounded-lg text-sm font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', borderLeft: '3px solid var(--accent-red)' }}
              >
                {flareReport.flare_forecast}
              </div>

              <div className="text-xs font-sans leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                {flareReport.timeline_summary}
              </div>

              {Object.keys(flareReport.probabilistic_differential).length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                      DIAGNOSTIC LANDSCAPE:
                    </span>
                    <div className="space-y-1">
                      {Object.entries(flareReport.probabilistic_differential)
                        .sort(([, a], [, b]) => b - a)
                        .map(([dx, prob]) => (
                          <div key={dx} className="flex items-center gap-2">
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{dx}</span>
                                <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>{(prob * 100).toFixed(1)}%</span>
                              </div>
                              <div className="w-full h-2 rounded mt-1" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                                <div
                                  className="h-2 rounded transition-all duration-300"
                                  style={{
                                    width: `${prob * 100}%`,
                                    backgroundColor: prob > 0.5 ? 'var(--accent-red)' :
                                                     prob > 0.25 ? 'var(--accent-yellow)' :
                                                     'var(--accent-blue)',
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </>
              )}

              {flareReport.precursor_signals.length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                      PRECURSOR SIGNALS:
                    </span>
                    {flareReport.precursor_signals.map((sig, i) => (
                      <div key={i} className="text-xs font-sans leading-relaxed mb-1 pl-2" style={{ borderLeft: '2px solid var(--accent-yellow)', color: 'var(--text-primary)' }}>
                        {sig.signal} — {sig.description}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {flareReport.risk_drivers.length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                      RISK DRIVERS:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {flareReport.risk_drivers.map((d, i) => (
                        <span key={i} className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}>
                          {d.driver} ({(d.weight * 100).toFixed(0)}%)
                        </span>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {flareReport.contradictions.length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--accent-yellow)' }}>
                      CONTRADICTIONS:
                    </span>
                    {flareReport.contradictions.map((c, i) => (
                      <p key={i} className="text-xs font-sans leading-relaxed mb-1" style={{ color: 'var(--accent-yellow)' }}>
                        {c}
                      </p>
                    ))}
                  </div>
                </>
              )}

              {flareReport.guidance_for_clinician.length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                      CLINICIAN GUIDANCE:
                    </span>
                    {flareReport.guidance_for_clinician.map((g, i) => (
                      <p key={i} className="text-xs font-sans leading-relaxed mb-1" style={{ color: 'var(--text-muted)' }}>
                        {g}
                      </p>
                    ))}
                  </div>
                </>
              )}

              {flareReport.safety_warnings && flareReport.safety_warnings.length > 0 && (
                <>
                  <div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
                  <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                    <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--accent-red)' }}>
                      SAFETY WARNINGS:
                    </span>
                    {flareReport.safety_warnings.map((w, i) => (
                      <p key={i} className="text-xs font-sans leading-relaxed" style={{ color: 'var(--accent-red)' }}>
                        {w}
                      </p>
                    ))}
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
