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
      <h3>Journal Analysis</h3>
      
      {analysis.symptoms && analysis.symptoms.length > 0 && (
        <div className="analysis-section">
          <h4>Identified Symptoms:</h4>
          <ul>
            {analysis.symptoms.map((symptom, index) => (
              <li key={index}>{symptom}</li>
            ))}
          </ul>
        </div>
      )}
      
      {analysis.environmental_factors && analysis.environmental_factors.length > 0 && (
        <div className="analysis-section">
          <h4>Environmental Factors:</h4>
          <ul>
            {analysis.environmental_factors.map((factor, index) => (
              <li key={index}>{factor}</li>
            ))}
          </ul>
        </div>
      )}
      
      {analysis.life_stressors && analysis.life_stressors.length > 0 && (
        <div className="analysis-section">
          <h4>Life Stressors:</h4>
          <ul>
            {analysis.life_stressors.map((stressor, index) => (
              <li key={index}>{stressor}</li>
            ))}
          </ul>
        </div>
      )}
      
      {analysis.diagnoses && analysis.diagnoses.length > 0 && (
        <div className="analysis-section">
          <h4>Diagnoses:</h4>
          <ul className="diagnoses-list">
            {analysis.diagnoses.map((diagnosis, index) => (
              <li key={index} className={`diagnosis-item ${diagnosis.status}`}>
                <div className="diagnosis-header">
                  <span className="diagnosis-name">{diagnosis.name}</span>
                  <span className="diagnosis-confidence">{diagnosis.confidence}%</span>
                </div>
                <div className="diagnosis-terrain">
                  {diagnosis.staxLevel && (
                    <span className={`stax-badge ${getStaxColor(diagnosis.staxLevel)}`}>
                      STAX {diagnosis.staxLevel}
                    </span>
                  )}
                  {diagnosis.zone && (
                    <span className={`zone-badge ${getZoneColor(diagnosis.zone)}`}>
                      Zone {diagnosis.zone}
                    </span>
                  )}
                  {diagnosis.status && (
                    <span className={`status-badge status-${diagnosis.status}`}>
                      {diagnosis.status.charAt(0).toUpperCase() + diagnosis.status.slice(1)}
                    </span>
                  )}
                </div>
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
    </div>
  );
};

export default JournalAnalysisDisplay;
