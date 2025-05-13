import React from 'react';
import PropTypes from 'prop-types';
import { ZONES, STAX_LEVELS } from '../../utils/ethosOfHealth';
import { downloadTimelinePdf } from '../../utils/pdfGenerator';
import './JournalResponse.css';
import '../../styles/Journal.css';

const JournalResponse = ({ response, timelineData }) => {
  if (!response) {
    return null;
  }
  
  const formattedDate = response.timestamp 
    ? new Date(response.timestamp).toLocaleString() 
    : new Date().toLocaleString();
  
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
    <div className="journal-response-container">
      <div className="journal-response-header">
        <h2>AI Analysis</h2>
        <div className="response-date">{formattedDate}</div>
      </div>
      
      <div className="journal-response-content">
        {/* Analysis section */}
        {response.analysis && (
          <div className="analysis-section">
            <h3>Analysis</h3>
            <div className="analysis-text">
              <p>{response.analysis}</p>
            </div>
          </div>
        )}
        
        {/* Diagnoses section */}
        {response.diagnoses && response.diagnoses.length > 0 && (
          <div className="diagnoses-list">
            <h3>Updated Diagnoses</h3>
            {response.diagnoses.map((diagnosis, index) => (
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
          <h3>Relevant Data Retrieved</h3>
          
          {/* Symptoms section */}
          <div className="category-section">
            <h4>Identified Symptoms</h4>
            {response.categories && response.categories.symptoms && response.categories.symptoms.length > 0 ? (
              <ul className="category-list">
                {response.categories.symptoms.map((symptom, index) => (
                  <li key={`symptom-${index}`} className="category-item">
                    {typeof symptom === 'string' ? symptom : symptom.symptom || JSON.stringify(symptom)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-data">No symptoms identified.</p>
            )}
          </div>
          
          {/* Environmental factors section */}
          <div className="category-section">
            <h4>Environmental Factors</h4>
            {response.categories && response.categories.environmental_factors && response.categories.environmental_factors.length > 0 ? (
              <ul className="category-list">
                {response.categories.environmental_factors.map((factor, index) => (
                  <li key={`env-factor-${index}`} className="category-item">{factor}</li>
                ))}
              </ul>
            ) : (
              <p className="no-data">No environmental factors identified.</p>
            )}
          </div>
          
          {/* Life stressors section */}
          <div className="category-section">
            <h4>Life Stressors</h4>
            {response.categories && response.categories.life_stressors && response.categories.life_stressors.length > 0 ? (
              <ul className="category-list">
                {response.categories.life_stressors.map((stressor, index) => (
                  <li key={`stressor-${index}`} className="category-item">{stressor}</li>
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
        
        <div className="disclaimer">
          <h3>Important Note</h3>
          <p>This analysis is for informational purposes only and is not a medical diagnosis. 
             Please consult with a healthcare professional for proper evaluation and diagnosis.</p>
        </div>
      </div>
    </div>
  );
};

JournalResponse.propTypes = {
  response: PropTypes.shape({
    text: PropTypes.string,
    analysis: PropTypes.string,
    timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
    categories: PropTypes.shape({
      symptoms: PropTypes.array,
      environmental_factors: PropTypes.array,
      life_stressors: PropTypes.array
    }),
    diagnoses: PropTypes.array
  }),
  timelineData: PropTypes.object
};

export default JournalResponse;
