import React from 'react';
import { format } from 'date-fns';
import '../../styles/Journal.css';

const JournalTimeline = ({ timelineData }) => {
  if (!timelineData || !timelineData.initialDiagnosis || !timelineData.journalEntries) {
    return <div className="timeline-empty">No timeline data available</div>;
  }



  const getStatusClass = (status) => {
    switch (status) {
      case 'new': return 'status-new';
      case 'confirmed': return 'status-confirmed';
      case 'eliminated': return 'status-eliminated';
      default: return '';
    }
  };

  const sortedEntries = [...timelineData.journalEntries].sort((a, b) => 
    new Date(a.entryDate) - new Date(b.entryDate)
  );

  return (
    <div className="journal-timeline">
      <h3>Diagnosis Timeline</h3>
      
      <div className="timeline-container">
        {/* Initial Diagnosis */}
        <div className="timeline-item initial-diagnosis">
          <div className="timeline-date">
            <span className="date-label">Initial Assessment</span>
            <span className="date-value">{format(new Date(timelineData.initialDiagnosis.date), 'MMM d, yyyy')}</span>
          </div>
          <div className="timeline-content">
            <h4>Initial Diagnoses</h4>
            <ul className="diagnosis-list">
              {timelineData.initialDiagnosis.diagnoses.map((diagnosis, index) => (
                <li key={index} className="diagnosis-item">
                  <div className="diagnosis-header">
                    <span className="diagnosis-name">{diagnosis.name}</span>
                    <span className="diagnosis-confidence">{diagnosis.confidence}%</span>
                  </div>

                </li>
              ))}
            </ul>
          </div>
        </div>
        
        {/* Journal Entries */}
        {sortedEntries.map((entry, entryIndex) => (
          <div key={entryIndex} className="timeline-item journal-entry">
            <div className="timeline-date">
              <span className="date-label">Journal Entry</span>
              <span className="date-value">{format(new Date(entry.entryDate), 'MMM d, yyyy')}</span>
            </div>
            <div className="timeline-content">
              <div className="entry-content">
                <p>{entry.content}</p>
              </div>
              
              {entry.analysis && (
                <div className="entry-analysis">
                  {entry.analysis.symptoms && entry.analysis.symptoms.length > 0 && (
                    <div className="analysis-section">
                      <h5>Symptoms</h5>
                      <ul>
                        {entry.analysis.symptoms.map((symptom, i) => (
                          <li key={i}>{symptom}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {entry.analysis.environmentalFactors && entry.analysis.environmentalFactors.length > 0 && (
                    <div className="analysis-section">
                      <h5>Environmental Factors</h5>
                      <ul>
                        {entry.analysis.environmentalFactors.map((factor, i) => (
                          <li key={i}>{factor}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {entry.analysis.lifeStressors && entry.analysis.lifeStressors.length > 0 && (
                    <div className="analysis-section">
                      <h5>Life Stressors</h5>
                      <ul>
                        {entry.analysis.lifeStressors.map((stressor, i) => (
                          <li key={i}>{stressor}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {entry.analysis.diagnoses && entry.analysis.diagnoses.length > 0 && (
                    <div className="analysis-section">
                      <h5>Updated Diagnoses</h5>
                      <ul className="diagnosis-list">
                        {entry.analysis.diagnoses.map((diagnosis, i) => (
                          <li key={i} className={`diagnosis-item ${getStatusClass(diagnosis.status)}`}>
                            <div className="diagnosis-header">
                              <span className="diagnosis-name">{diagnosis.name}</span>
                              <span className="diagnosis-confidence">{diagnosis.confidence}%</span>
                              {diagnosis.status && (
                                <span className={`status-badge status-${diagnosis.status}`}>
                                  {diagnosis.status.charAt(0).toUpperCase() + diagnosis.status.slice(1)}
                                </span>
                              )}
                            </div>

                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default JournalTimeline;
