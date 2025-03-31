import React from 'react';
import PropTypes from 'prop-types';
import { downloadPdfReport } from '../../utils/pdfGenerator';
import './AIResponseDisplay.css';

const AIResponseDisplay = ({ diagnosticResults }) => {
  if (!diagnosticResults || diagnosticResults.length === 0) {
    return null;
  }

  return (
    <div className="ai-response-container">
      <h2>Potential Diagnoses</h2>
      <div className="diagnoses-list">
        {diagnosticResults.map((diagnosis, index) => (
          <div key={index} className="diagnosis-card">
            <div className="diagnosis-header">
              <h3>{diagnosis.name}</h3>
              <div className="confidence-badge" style={{ 
                backgroundColor: getConfidenceColor(diagnosis.confidence)
              }}>
                {diagnosis.confidence}% confidence
              </div>
            </div>
            
            <div className="diagnosis-details">
              <div className="detail-section">
                <h4>Common Symptoms</h4>
                <ul>
                  {diagnosis.symptoms.map((symptom, idx) => (
                    <li key={idx}>{formatSymptomName(symptom)}</li>
                  ))}
                </ul>
              </div>
              
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
           Please consult with a healthcare professional for proper evaluation and diagnosis. 
           The confidence percentages are based on symptom matching and are not clinical assessments.</p>
        <button onClick={() => downloadPdfReport(diagnosticResults)} className="btn btn-primary download-btn">
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
      symptoms: PropTypes.arrayOf(PropTypes.string).isRequired,
      redFlags: PropTypes.arrayOf(PropTypes.string),
      labSuggestions: PropTypes.arrayOf(PropTypes.string)
    })
  )
};

export default AIResponseDisplay;
