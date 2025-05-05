import React from 'react';
import PropTypes from 'prop-types';
import './JournalResponse.css';

const JournalResponse = ({ response }) => {
  if (!response) {
    return null;
  }
  
  const formattedDate = response.timestamp 
    ? new Date(response.timestamp).toLocaleString() 
    : new Date().toLocaleString();
  
  return (
    <div className="journal-response-container">
      <div className="journal-response-header">
        <h2>AI Analysis</h2>
        <div className="response-date">{formattedDate}</div>
      </div>
      
      <div className="journal-response-content">
        {response.analysis && (
          <div className="analysis-section">
            <h3>Analysis</h3>
            <div className="analysis-text">
              <p>{response.analysis}</p>
            </div>
          </div>
        )}
        
        <div className="response-text">
          <p>{response.text}</p>
        </div>
        
        {response.categories && (
          <div className="categories-container">
            {response.categories.symptoms.length > 0 && (
              <div className="category-section">
                <h3>Symptoms</h3>
                <ul className="category-list">
                  {response.categories.symptoms.map((symptom, index) => (
                    <li key={`symptom-${index}`} className="category-item">
                      {typeof symptom === 'string' ? symptom : symptom.symptom || JSON.stringify(symptom)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {response.categories.environmental_factors.length > 0 && (
              <div className="category-section">
                <h3>Environmental Factors</h3>
                <ul className="category-list">
                  {response.categories.environmental_factors.map((factor, index) => (
                    <li key={`env-factor-${index}`} className="category-item">{factor}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {response.categories.life_stressors.length > 0 && (
              <div className="category-section">
                <h3>Life Stressors</h3>
                <ul className="category-list">
                  {response.categories.life_stressors.map((stressor, index) => (
                    <li key={`stressor-${index}`} className="category-item">{stressor}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
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
    text: PropTypes.string.isRequired,
    analysis: PropTypes.string,
    timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
    categories: PropTypes.shape({
      symptoms: PropTypes.array,
      environmental_factors: PropTypes.array,
      life_stressors: PropTypes.array
    })
  })
};

export default JournalResponse;
