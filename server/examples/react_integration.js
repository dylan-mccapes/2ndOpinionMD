/**
 * Example React integration for the 2ndOpinionMD-MVP project
 * This file demonstrates how to integrate the Chroma vector database
 * with the React frontend for symptom analysis and diagnosis.
 */

import { useState, useEffect } from 'react';

/**
 * Component for submitting symptoms and receiving AI-generated diagnoses
 */
const SymptomAnalyzer = () => {
  const [symptoms, setSymptoms] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSymptomChange = (e) => {
    const symptomText = e.target.value;
    if (e.key === 'Enter' && symptomText.trim()) {
      setSymptoms([...symptoms, symptomText.trim()]);
      e.target.value = '';
    }
  };

  const removeSymptom = (index) => {
    setSymptoms(symptoms.filter((_, i) => i !== index));
  };

  const analyzeSymptoms = async () => {
    if (symptoms.length === 0) {
      setError('Please enter at least one symptom');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:3001/api/diagnose', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          symptoms,
          model: 'gpt-3.5-turbo' // Can be changed to other models
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Error analyzing symptoms:', err);
      setError(`Error analyzing symptoms: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="symptom-analyzer">
      <h2>Symptom Analyzer</h2>
      
      {/* Symptom input */}
      <div className="symptom-input">
        <label htmlFor="symptom-input">Enter your symptoms (press Enter after each):</label>
        <input
          type="text"
          id="symptom-input"
          onKeyDown={handleSymptomChange}
          placeholder="e.g., joint pain, fatigue, fever"
          disabled={isLoading}
        />
      </div>
      
      {/* Symptom tags */}
      <div className="symptom-tags">
        {symptoms.map((symptom, index) => (
          <div key={index} className="symptom-tag">
            {symptom}
            <button onClick={() => removeSymptom(index)} disabled={isLoading}>×</button>
          </div>
        ))}
      </div>
      
      {/* Submit button */}
      <button 
        onClick={analyzeSymptoms} 
        disabled={isLoading || symptoms.length === 0}
        className="analyze-button"
      >
        {isLoading ? 'Analyzing...' : 'Analyze Symptoms'}
      </button>
      
      {/* Error message */}
      {error && <div className="error-message">{error}</div>}
      
      {/* Results */}
      {results && (
        <div className="analysis-results">
          <h3>Potential Diagnoses</h3>
          {results.diagnoses.map((diagnosis, index) => (
            <div key={index} className="diagnosis-card">
              <h4>{diagnosis.name} <span className="confidence">({diagnosis.confidence}% confidence)</span></h4>
              <p>{diagnosis.explanation}</p>
              
              {diagnosis.redFlags.length > 0 && (
                <div className="red-flags">
                  <h5>Red Flags to Watch For:</h5>
                  <ul>
                    {diagnosis.redFlags.map((flag, i) => (
                      <li key={i}>{flag}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {diagnosis.labSuggestions.length > 0 && (
                <div className="lab-suggestions">
                  <h5>Suggested Lab Tests:</h5>
                  <ul>
                    {diagnosis.labSuggestions.map((test, i) => (
                      <li key={i}>{test}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SymptomAnalyzer;

/**
 * Example usage in your main App component:
 * 
 * import SymptomAnalyzer from './components/SymptomAnalyzer';
 * 
 * function App() {
 *   return (
 *     <div className="App">
 *       <header className="App-header">
 *         <h1>2ndOpinionMD</h1>
 *       </header>
 *       <main>
 *         <SymptomAnalyzer />
 *       </main>
 *     </div>
 *   );
 * }
 */
