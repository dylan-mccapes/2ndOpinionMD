import React from 'react';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import '../../styles/Journal.css';

const JournalAnalysisDisplay = ({ analysis, timelineData }) => {
  const parsed = parseJournalAnalysis(analysis);

  if (!parsed) {
    return (
      <div className="journal-analysis">
        <h3>AI Analysis</h3>
        <p>AI analysis not available for this entry.</p>
      </div>
    );
  }

  return (
    <div className="journal-analysis">
      <h3>AI Analysis</h3>

      {/* Summary paragraph */}
      {parsed.analysis && (
        <div className="analysis-results">
          <p>{parsed.analysis}</p>
        </div>
      )}

      {/* Detected symptoms */}
      {!!parsed.symptoms?.length && (
        <section className="detected-symptoms-section">
          <h4>Detected Symptoms</h4>
          <ul className="symptoms-list">
            {parsed.symptoms.map((symptom, i) => (
              <li key={i} className="symptom-item">
                {typeof symptom === 'string' ? symptom : symptom?.name || symptom}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Suggested diagnoses */}
      {!!parsed.diagnoses?.length && (
        <section className="diagnoses-section">
          <h4>Suggested Diagnoses</h4>
          <ul className="diagnosis-list">
            {parsed.diagnoses.map((d, i) => (
              <li key={i}>
                <strong>{d.name}</strong>
                {d.confidence != null ? ` (${d.confidence}%)` : ''}
                {!!d.tags?.length && (
                  <span className="tags">
                    {d.tags.slice(0, 3).map((t, j) => (
                      <span key={j} className="tag">{t}</span>
                    ))}
                    {d.tags.length > 3 && <span className="tag">+{d.tags.length - 3}</span>}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Follow-up questions */}
      {!!parsed.followUpQuestions?.length && (
        <section className="follow-up-questions-section">
          <h4>Follow-up Questions</h4>
          <ul className="questions-list">
            {parsed.followUpQuestions.map((q, i) => <li key={i}>{q}</li>)}
          </ul>
        </section>
      )}

      {/* Tracking suggestions */}
      {!!parsed.trackingSuggestions?.length && (
        <section className="tracking-suggestions-section">
          <h4>Tracking Suggestions</h4>
          <ul className="suggestions-list">
            {parsed.trackingSuggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </section>
      )}

      {/* Journaling recommendation */}
      {(parsed.journalingRecommendation?.promptType || parsed.journalingRecommendation?.suggestedPrompt) && (
        <section className="journaling-recommendation-section">
          <h4>Journaling Recommendation</h4>
          {parsed.journalingRecommendation?.promptType && (
            <p><strong>Prompt Type:</strong> {parsed.journalingRecommendation.promptType}</p>
          )}
          {parsed.journalingRecommendation?.suggestedPrompt && (
            <p>{parsed.journalingRecommendation.suggestedPrompt}</p>
          )}
        </section>
      )}

      {/* Pattern observations */}
      {parsed.patternObservations && (
        <section className="pattern-observations-section">
          <h4>Pattern Observations</h4>
          <p>{parsed.patternObservations}</p>
        </section>
      )}
    </div>
  );
};

export default JournalAnalysisDisplay;
