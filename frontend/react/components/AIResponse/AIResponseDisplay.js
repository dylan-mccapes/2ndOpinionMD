import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { downloadPdfReport } from '../../utils/pdfGenerator';
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
            <li><strong>Confidence Scores:</strong> Indicate how well your symptoms match potential conditions</li>
            <li><strong>Tags:</strong> Provide additional context about your diagnostic terrain</li>
            <li><strong>Risk Factors:</strong> Highlight important symptoms and suggested tests</li>
          </ul>
          <p>Higher confidence scores indicate better symptom matching with potential conditions.</p>
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
            

            
            <div className="diagnosis-details">
              {diagnosis.explanation && (
                <div className="detail-section">
                  <h4>Recommendations</h4>
                  <p>{diagnosis.explanation}</p>
                </div>
              )}
              
              {diagnosis.icd10Code && (
                <div className="detail-section">
                  <h4>ICD-10 Code</h4>
                  <p className="icd-code">{diagnosis.icd10Code}</p>
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
      icd10Code: PropTypes.string,
      tags: PropTypes.arrayOf(PropTypes.string),
      status: PropTypes.string,
      explanation: PropTypes.string
    })
  )
};

export default AIResponseDisplay;
