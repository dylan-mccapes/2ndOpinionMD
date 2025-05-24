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
  
  console.log('Response structure:', JSON.stringify(response, null, 2));
  
  console.log('Analysis data extraction - DETAILED:', {
    responseType: typeof response,
    analysisType: typeof response.analysis,
    directAnalysis: response.analysis,
    nestedAnalysis: response.analysis?.analysis,
    aiAnalysis: response.ai_analysis,
    aiAnalysisType: typeof response.ai_analysis,
    aiAnalysisAnalysis: response.ai_analysis?.analysis,
    aiAnalysisPatternObservations: response.ai_analysis?.patternObservations,
    patternObservations: response.patternObservations || response.analysis?.patternObservations,
    categories: response.categories,
    rawAnalysis: JSON.stringify(response.analysis)
  });
  
  const analysisData = {
    analysis: response.ai_analysis?.analysis || 
              (typeof response.analysis === 'string' ? response.analysis : response.analysis?.analysis) || 
              response.text ||
              "No analysis available.",
    patternObservations: response.ai_analysis?.patternObservations || 
                         response.patternObservations || 
                         response.analysis?.patternObservations || 
                         "",
    diagnoses: response.ai_analysis?.diagnoses || 
               response.diagnoses || 
               response.analysis?.diagnoses || 
               [],
    symptoms: response.ai_analysis?.symptoms || 
              response.categories?.symptoms || 
              response.analysis?.symptoms || 
              [],
    environmental_factors: response.ai_analysis?.environmental_factors || 
                          response.categories?.environmental_factors || 
                          response.analysis?.environmental_factors || 
                          [],
    life_stressors: response.ai_analysis?.life_stressors || 
                   response.categories?.life_stressors || 
                   response.analysis?.life_stressors || 
                   []
  };
  
  console.log('Final analysisData being passed to JournalAnalysisDisplay:', analysisData);
  
  if (process.env.NODE_ENV === 'development') {
    setTimeout(() => {
      const debugDiv = document.createElement('div');
      debugDiv.id = 'journal-debug-info';
      debugDiv.style.display = 'none';
      debugDiv.innerHTML = `
        <h3>Debug Info</h3>
        <pre>${JSON.stringify({response, analysisData}, null, 2)}</pre>
      `;
      document.body.appendChild(debugDiv);
    }, 1000);
  }
  
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
             This journal analysis is designed to help you track patterns and share insights with your healthcare provider.
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
