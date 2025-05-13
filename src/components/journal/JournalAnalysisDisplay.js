import React from 'react';
import { ZONES, STAX_LEVELS } from '../../utils/ethosOfHealth';
import { downloadTimelinePdf } from '../../utils/pdfGenerator';
import '../../styles/Journal.css';

const JournalAnalysisDisplay = ({ analysis, timelineData }) => {
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
  
  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return '#28a745'; // Green
    if (confidence >= 60) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
  };
  
  const handleDownloadPdf = () => {
    if (timelineData) {
      downloadTimelinePdf(timelineData, `diagnosis-timeline-${Date.now()}.pdf`);
    }
  };
  
  return (
    <div className="journal-analysis">
      <h3>AI Analysis</h3>
      
      {/* Analysis section */}
      <div className="analysis-results">
        <h4>Analysis Results:</h4>
        <p>{analysis.analysis || "No analysis available."}</p>
      </div>
      
      {/* Diagnoses section with updated confidence scores */}
      {analysis.diagnoses && analysis.diagnoses.length > 0 && (
        <div className="diagnoses-list">
          <h4>Updated Diagnoses:</h4>
          {analysis.diagnoses.map((diagnosis, index) => (
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
            </div>
          ))}
        </div>
      )}
      
      {/* RAG Data section */}
      <div className="analysis-categories">
        <h4>Relevant Data Retrieved:</h4>
        
        {/* Symptoms section */}
        <div className="analysis-section">
          <h5>Identified Symptoms:</h5>
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
          <h5>Environmental Factors:</h5>
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
          <h5>Life Stressors:</h5>
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
      
      {/* PDF Download Button */}
      <div className="timeline-actions">
        <button 
          onClick={handleDownloadPdf} 
          className="btn btn-primary download-btn"
          disabled={!timelineData}
        >
          Download Timeline PDF
        </button>
      </div>
      
      <div className="important-note">
        <p>This analysis is for informational purposes only and is not a medical diagnosis. Please consult with a healthcare professional for proper evaluation and diagnosis.</p>
      </div>
    </div>
  );
};

export default JournalAnalysisDisplay;
