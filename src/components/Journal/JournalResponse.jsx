import React from 'react';
import PropTypes from 'prop-types';
import './JournalResponse.css';

const JournalResponse = ({ response }) => {
  if (!response) {
    return null;
  }
  
  return (
    <div className="journal-response-container">
      <h2>AI Analysis</h2>
      <div className="journal-response-content">
        <div className="response-text">
          <p>{response.text}</p>
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
    text: PropTypes.string.isRequired
  })
};

export default JournalResponse;
