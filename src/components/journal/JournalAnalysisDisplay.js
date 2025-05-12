import React from 'react';
import { ZONES, STAX_LEVELS } from '../../utils/ethosOfHealth';
import '../../styles/Journal.css';

const JournalAnalysisDisplay = ({ analysis }) => {
  if (!analysis) return null;
  
  const getStaxColor = (level) => {
    switch (level) {
      case 1: return 'stax-1';
      case 2: return 'stax-2';
      case 3: return 'stax-3';
      case 4: return 'stax-4';
      default: return 'stax-1';
    }
  };
  
  const getZoneColor = (zone) => {
    switch (zone) {
      case 1: return 'zone-1';
      case 2: return 'zone-2';
      case 3: return 'zone-3';
      case 4: return 'zone-4';
      case 5: return 'zone-5';
      default: return 'zone-1';
    }
  };
  
  return (
    <div className="journal-analysis">
      <h3>AI Analysis</h3>
      
      {/* Summary section */}
      <div className="analysis-summary">
        <p>Thank you for your journal entry. Your information has been recorded and analyzed.</p>
        {analysis.summary && <p>{analysis.summary}</p>}
      </div>
      
      {/* Analysis section */}
      <div className="analysis-results">
        <h4>Analysis Results:</h4>
        <p>{analysis.analysis || "No analysis available."}</p>
      </div>
      
      {/* Categorized data - only show if specifically requested */}
      {(window.location.search.includes('showDetails=true') || localStorage.getItem('showJournalDetails') === 'true') && (
        <div className="analysis-categories">
          {/* Symptoms section */}
          <div className="analysis-section">
            <h4>Identified Symptoms:</h4>
            {analysis.symptoms && analysis.symptoms.length > 0 ? (
              <ul>
                {analysis.symptoms.map((symptom, index) => (
                  <li key={index}>{symptom}</li>
                ))}
              </ul>
            ) : (
              <p className="no-data">No symptoms identified.</p>
            )}
          </div>
          
          {/* Environmental factors section */}
          <div className="analysis-section">
            <h4>Environmental Factors:</h4>
            {analysis.environmental_factors && analysis.environmental_factors.length > 0 ? (
              <ul>
                {analysis.environmental_factors.map((factor, index) => (
                  <li key={index}>{factor}</li>
                ))}
              </ul>
            ) : (
              <p className="no-data">No environmental factors identified.</p>
            )}
          </div>
          
          {/* Life stressors section */}
          <div className="analysis-section">
            <h4>Life Stressors:</h4>
            {analysis.life_stressors && analysis.life_stressors.length > 0 ? (
              <ul>
                {analysis.life_stressors.map((stressor, index) => (
                  <li key={index}>{stressor}</li>
                ))}
              </ul>
            ) : (
              <p className="no-data">No life stressors identified.</p>
            )}
          </div>
        </div>
      )}
      
      {/* Diagnoses section with updated confidence scores */}
      {analysis.diagnoses && analysis.diagnoses.length > 0 && (
        <div className="analysis-section diagnoses-section">
          <h4>Updated Diagnoses:</h4>
          <ul className="diagnoses-list">
            {analysis.diagnoses.map((diagnosis, index) => (
              <li key={index} className={`diagnosis-item ${diagnosis.status || ''}`}>
                <div className="diagnosis-header">
                  <span className="diagnosis-name">{diagnosis.name}</span>
                  <div className="confidence-container">
                    <span className="confidence-label">Confidence:</span>
                    <div className="confidence-bar-container">
                      <div 
                        className="confidence-bar" 
                        style={{width: `${diagnosis.confidence}%`, backgroundColor: diagnosis.confidence > 70 ? '#28a745' : diagnosis.confidence > 40 ? '#ffc107' : '#dc3545'}}
                      ></div>
                    </div>
                    <span className="confidence-value">{diagnosis.confidence}%</span>
                  </div>
                </div>
                
                <div className="diagnosis-terrain">
                  {diagnosis.staxLevel && (
                    <div className="terrain-indicator">
                      <span className={`stax-badge ${getStaxColor(diagnosis.staxLevel)}`}>
                        STAX {diagnosis.staxLevel}
                      </span>
                      <span className="terrain-description">
                        {STAX_LEVELS[diagnosis.staxLevel] || `Complexity level ${diagnosis.staxLevel}`}
                      </span>
                    </div>
                  )}
                  
                  {diagnosis.zone && (
                    <div className="terrain-indicator">
                      <span className={`zone-badge ${getZoneColor(diagnosis.zone)}`}>
                        Zone {diagnosis.zone}
                      </span>
                      <span className="terrain-description">
                        {ZONES[diagnosis.zone] || `Stability level ${diagnosis.zone}`}
                      </span>
                    </div>
                  )}
                </div>
                
                {diagnosis.status && (
                  <div className="diagnosis-status-container">
                    <span className={`status-badge status-${diagnosis.status}`}>
                      {diagnosis.status === 'new' ? 'New Diagnosis' : 
                       diagnosis.status === 'confirmed' ? 'Confirmed' : 
                       diagnosis.status === 'eliminated' ? 'Eliminated' : 
                       diagnosis.status.charAt(0).toUpperCase() + diagnosis.status.slice(1)}
                    </span>
                    {diagnosis.statusReason && (
                      <span className="status-reason">{diagnosis.statusReason}</span>
                    )}
                  </div>
                )}
                
                {diagnosis.tags && diagnosis.tags.length > 0 && (
                  <div className="diagnosis-tags">
                    {diagnosis.tags.map((tag, i) => (
                      <span key={i} className="tag">{tag}</span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Journaling recommendation section */}
      {analysis.journalingRecommendation && (
        <div className="analysis-section recommendation-section">
          <h4>Journaling Recommendation:</h4>
          <div className="recommendation-content">
            {analysis.journalingRecommendation.promptType && (
              <div className="prompt-type">
                <span className="prompt-label">Recommended Approach:</span>
                <span className="prompt-value">{analysis.journalingRecommendation.promptType}</span>
              </div>
            )}
            {analysis.journalingRecommendation.suggestedPrompt && (
              <div className="suggested-prompt">
                <p className="prompt-suggestion">{analysis.journalingRecommendation.suggestedPrompt}</p>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="important-note">
        <p>This analysis is for informational purposes only and is not a medical diagnosis. Please consult with a healthcare professional for proper evaluation and diagnosis.</p>
      </div>
    </div>
  );
};

export default JournalAnalysisDisplay;
