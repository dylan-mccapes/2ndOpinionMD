import React from 'react';
import PropTypes from 'prop-types';
import JournalAnalysisDisplay from './JournalAnalysisDisplay';
import './JournalResponse.css';
import '../../styles/Journal.css';

const JournalResponse = ({ response, timelineData }) => {
  if (!response) {
    return null;
  }
  
  const formattedDate = response.timestamp 
    ? new Date(response.timestamp).toLocaleString() 
    : new Date().toLocaleString();
  
  const analysisData = {
    analysis: typeof response.analysis === 'string' 
      ? response.analysis 
      : (response.analysis?.analysis || "No analysis available."),
    patternObservation: response.patternObservation || response.analysis?.patternObservations || "",
    diagnoses: response.diagnoses || response.analysis?.diagnoses || [],
    symptoms: response.categories?.symptoms || response.analysis?.symptoms || [],
    environmental_factors: response.categories?.environmental_factors || response.analysis?.environmental_factors || [],
    life_stressors: response.categories?.life_stressors || response.analysis?.life_stressors || []
  };
  
  return (
    <div className="journal-response-container">
      <div className="journal-response-header">
        <h2>AI Analysis</h2>
        <div className="response-date">{formattedDate}</div>
      </div>
      
      <div className="journal-response-content">
        <JournalAnalysisDisplay 
          analysis={analysisData} 
          timelineData={timelineData} 
        />
        
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
