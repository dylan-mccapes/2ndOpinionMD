import React from 'react';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import DiagnosisTable from './DiagnosisTable';
import DebugBlock from '../common/DebugBlock';
import '../../styles/Journal.css';
import './JournalAnalysisDisplay.css';

const JournalAnalysisDisplay = ({ analysis, rawAnalysis }) => {
  if (!analysis) return null;
  const parsed = parseJournalAnalysis(analysis);
  if (!parsed) return null;

  const ts = parsed.timestamp ? new Date(parsed.timestamp) : null;
  const tsText = ts ? ts.toLocaleString(undefined, {
    year:'numeric', month:'short', day:'numeric',
    hour:'numeric', minute:'2-digit', second:'2-digit'
  }) : null;

  return (
    <div className="ai-analysis">
      <header className="ai-analysis-header">
        <h3>AI Analysis</h3>
        {tsText && <div className="timestamp">{tsText}</div>}
      </header>

      {parsed.analysis && (
        <section className="summary">
          <h4>Summary</h4>
          <p>{parsed.analysis}</p>
        </section>
      )}

      {parsed.symptoms?.length > 0 && (
        <section className="detected-symptoms">
          <h4>Detected Symptoms</h4>
          <div className="pill-row">
            {parsed.symptoms.map((s, i) => <span key={i} className="symptom-tag">{s}</span>)}
          </div>
        </section>
      )}

      {parsed.environmental_factors?.length > 0 && (
        <section className="env-factors">
          <h4>Environmental Factors</h4>
          <div className="pill-row">
            {parsed.environmental_factors.map((s, i) => <span key={i} className="symptom-tag">{s}</span>)}
          </div>
        </section>
      )}

      {parsed.life_stressors?.length > 0 && (
        <section className="life-stressors">
          <h4>Life Stressors</h4>
          <div className="pill-row">
            {parsed.life_stressors.map((s, i) => <span key={i} className="symptom-tag">{s}</span>)}
          </div>
        </section>
      )}

      <DiagnosisTable diagnoses={parsed.diagnoses} />

      {parsed.journalingRecommendation?.suggestedPrompt && (
        <section className="journaling-rec">
          <h4>Journaling Recommendation</h4>
          <div className="rec-row">
            {parsed.journalingRecommendation.promptType && (
              <span className="badge">{parsed.journalingRecommendation.promptType}</span>
            )}
            <span className="suggested-prompt">{parsed.journalingRecommendation.suggestedPrompt}</span>
            <button
              type="button"
              className="copy-btn"
              onClick={() => navigator.clipboard.writeText(parsed.journalingRecommendation.suggestedPrompt)}
            >Copy</button>
          </div>
        </section>
      )}

      {parsed.followUpQuestions?.length > 0 && (
        <section className="follow-up-questions-section">
          <h4>Follow-up Questions</h4>
          <ul className="questions-list">
            {parsed.followUpQuestions.map((q, i) => <li key={i}>{q}</li>)}
          </ul>
        </section>
      )}

      {parsed.trackingSuggestions?.length > 0 && (
        <section className="tracking-suggestions-section">
          <h4>Tracking Suggestions</h4>
          <ul className="suggestions-list">
            {parsed.trackingSuggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </section>
      )}

      {parsed.patternObservations && (
        <section className="pattern-observations">
          <h4>Pattern Observations</h4>
          <p>{parsed.patternObservations}</p>
        </section>
      )}

      {process.env.NODE_ENV !== 'production' && (
        <div className="debug-stack">
          <DebugBlock title="Raw JSON (from OpenAI)" payload={rawAnalysis} filename="openai_raw.json" />
          <DebugBlock title="Parsed JSON" payload={parsed} filename="analysis_parsed.json" />
        </div>
      )}
    </div>
  );
};

export default JournalAnalysisDisplay;
