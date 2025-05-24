import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { downloadPdfReport } from '../../utils/pdfGenerator';
import { ZONES, STAX_LEVELS } from '../../utils/ethosOfHealth';
import './AIResponseDisplay.css';

const AIResponseDisplay = ({ diagnosticResults }) => {
  const [showEthosInfo, setShowEthosInfo] = useState(false);
  
  if (!diagnosticResults || diagnosticResults.length === 0) {
    return null;
  }

  const diagnoses = Array.isArray(diagnosticResults) 
    ? diagnosticResults 
    : (diagnosticResults.diagnoses || []);
    
  const toggleEthosInfo = () => {
    setShowEthosInfo(!showEthosInfo);
  };

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
    <div className="ai-response-container">
      <div className="response-header">
        <h2>Potential Diagnoses</h2>
        <button 
          type="button" 
          className="info-button"
          onClick={toggleEthosInfo}
        >
          ℹ️ About Ethos of Health
        </button>
      </div>
      
      {showEthosInfo && (
        <div className="ethos-info-box">
          <h3>Ethos of Health Analysis</h3>
          <p>Our diagnostic system evaluates your health using the 2OPMD Diagnostic Terrain System:</p>
          <ul>
            <li><strong>STAX Levels (1-4):</strong> Measure the complexity and layering of conditions</li>
            <li><strong>Zones (1-5):</strong> Indicate stability and symptom frequency</li>
            <li><strong>Tags:</strong> Provide additional context about your diagnostic terrain</li>
          </ul>
          <p>Higher STAX levels indicate more complex conditions, while higher Zone numbers indicate less stability.</p>
          <button 
            type="button" 
            className="close-info-button"
            onClick={toggleEthosInfo}
          >
            Close
          </button>
        </div>
      )}
      
      <div className="diagnoses-list">
        {diagnoses.map((diagnosis, index) => (
          <div key={index} className="diagnosis-card">
            <div className="diagnosis-header">
              <h3>{diagnosis.name}</h3>
              <div className="diagnosis-badges">
                <div className="confidence-badge" style={{ 
                  backgroundColor: getConfidenceColor(diagnosis.confidence)
                }}>
                  {diagnosis.confidence}% confidence
                </div>
                
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
              </div>
            </div>
            
            {diagnosis.status && diagnosis.status !== 'initial' && (
              <div className={`diagnosis-status ${diagnosis.status}`}>
                {diagnosis.status === 'new' ? 'New Diagnosis' : 
                 diagnosis.status === 'confirmed' ? 'Confirmed' : 
                 diagnosis.status === 'eliminated' ? 'Eliminated' : ''}
              </div>
            )}
            
            {diagnosis.tags && diagnosis.tags.length > 0 && (
              <div className="diagnosis-tags">
                {diagnosis.tags.map((tag, i) => (
                  <span key={i} className="tag">{tag}</span>
                ))}
              </div>
            )}
            
            {(diagnosis.staxLevel || diagnosis.zone) && (
              <div className="diagnostic-terrain">
                <h4>Diagnostic Terrain</h4>
                <div className="terrain-indicators">
                  {diagnosis.staxLevel && (
                    <div className="terrain-indicator">
                      <span className={`stax-badge ${getStaxColor(diagnosis.staxLevel)}`}>
                        STAX {diagnosis.staxLevel}
                      </span>
                      <p className="terrain-description">
                        {STAX_LEVELS[diagnosis.staxLevel] || `STAX Level ${diagnosis.staxLevel}: Complexity level ${diagnosis.staxLevel}`}
                      </p>
                    </div>
                  )}
                  {diagnosis.zone && (
                    <div className="terrain-indicator">
                      <span className={`zone-badge ${getZoneColor(diagnosis.zone)}`}>
                        Zone {diagnosis.zone}
                      </span>
                      <p className="terrain-description">
                        {ZONES[diagnosis.zone] || `Zone ${diagnosis.zone}: Stability level ${diagnosis.zone}`}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <div className="diagnosis-details">
              {diagnosis.explanation && (
                <div className="detail-section">
                  <h4>Explanation</h4>
                  <p>{diagnosis.explanation}</p>
                </div>
              )}
              
              {diagnosis.symptoms && diagnosis.symptoms.length > 0 && (
                <div className="detail-section">
                  <h4>Common Symptoms</h4>
                  <ul>
                    {diagnosis.symptoms.map((symptom, idx) => (
                      <li key={idx}>{formatSymptomName(symptom)}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {diagnosis.redFlags && diagnosis.redFlags.length > 0 && (
                <div className="detail-section">
                  <h4>Red Flags</h4>
                  <ul className="red-flags">
                    {diagnosis.redFlags.map((flag, idx) => (
                      <li key={idx}>{flag}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {diagnosis.labSuggestions && diagnosis.labSuggestions.length > 0 && (
                <div className="detail-section">
                  <h4>Suggested Tests</h4>
                  <ul className="lab-suggestions">
                    {diagnosis.labSuggestions.map((test, idx) => (
                      <li key={idx}>{test}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <div className="disclaimer">
        <h3>Important Disclaimer</h3>
        <p>This report is for informational purposes only and is not a medical diagnosis. 
           This tool is designed to help you track and journal your symptoms to share with your healthcare provider.
           Please consult with a healthcare professional for proper evaluation and diagnosis. 
           The confidence percentages are based on symptom matching and are not clinical assessments.</p>
        <button onClick={() => downloadPdfReport(diagnoses)} className="btn btn-primary download-btn">
          Download PDF Report
        </button>
      </div>
    </div>
  );
};

const getConfidenceColor = (confidence) => {
  if (confidence >= 80) return '#28a745'; // Green
  if (confidence >= 60) return '#ffc107'; // Yellow
  return '#dc3545'; // Red
};

const formatSymptomName = (symptom) => {
  return symptom
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

AIResponseDisplay.propTypes = {
  diagnosticResults: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      confidence: PropTypes.number.isRequired,
      symptoms: PropTypes.arrayOf(PropTypes.string),
      redFlags: PropTypes.arrayOf(PropTypes.string),
      labSuggestions: PropTypes.arrayOf(PropTypes.string),
      staxLevel: PropTypes.number,
      zone: PropTypes.number,
      tags: PropTypes.arrayOf(PropTypes.string),
      status: PropTypes.string,
      explanation: PropTypes.string
    })
  )
};

export default AIResponseDisplay;
