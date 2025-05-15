import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../../styles/Journal.css';

const JournalList = () => {
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchEntries = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        setEntries(response.data);
      } catch (err) {
        console.error('Error fetching journal entries:', err);
        setError('Unable to load journal entries. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchEntries();
  }, [navigate]);
  
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };
  
  const getSeverityColor = (severity) => {
    if (severity <= 3) return 'low-severity';
    if (severity <= 6) return 'medium-severity';
    return 'high-severity';
  };
  
  const deleteEntry = async (entryId) => {
    if (!window.confirm('Are you sure you want to delete this journal entry?')) {
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      
      await axios.delete(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal/${entryId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      setEntries(entries.filter(entry => entry.id !== entryId));
    } catch (err) {
      console.error('Error deleting journal entry:', err);
      setError('Unable to delete journal entry. Please try again.');
    }
  };
  
  if (isLoading) {
    return <div className="loading">Loading journal entries...</div>;
  }
  
  return (
    <div className="journal-list-container">
      <div className="journal-header">
        <h2>Your Journal Entries</h2>
        <Link to="/journal/new" className="new-entry-button">
          New Entry
        </Link>
      </div>
      
      {location.state?.message && (
        <div className="success-message">{location.state.message}</div>
      )}
      
      {error && <div className="error-message">{error}</div>}
      
      {entries.length === 0 ? (
        <div className="no-entries">
          <p>You haven't created any journal entries yet.</p>
          <Link to="/journal/new" className="start-button">
            Start Journaling
          </Link>
        </div>
      ) : (
        <div className="entries-list">
          {entries.map(entry => (
            <div key={entry.id} className="journal-entry-card">
              <div className="entry-header">
                <h3>{formatDate(entry.date)}</h3>
                <div className="entry-actions">
                  <Link to={`/journal/${entry.id}`} className="view-button">
                    View
                  </Link>
                  <button 
                    className="delete-button"
                    onClick={() => deleteEntry(entry.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
              
              <div className="entry-symptoms">
                <h4>Symptoms:</h4>
                <ul className="symptom-list">
                  {entry.symptoms.slice(0, 3).map((symptom, index) => {
                    if (typeof symptom === 'string') {
                      return (
                        <li key={index} className="symptom-tag low-severity">
                          {symptom}
                        </li>
                      );
                    } else if (symptom && typeof symptom === 'object') {
                      const symptomText = symptom.symptom || '';
                      const severity = symptom.severity || 5;
                      return (
                        <li key={index} className={`symptom-tag ${getSeverityColor(severity)}`}>
                          {symptomText} ({severity}/10)
                        </li>
                      );
                    }
                    return null;
                  })}
                  {entry.symptoms.length > 3 && (
                    <li className="more-symptoms">
                      +{entry.symptoms.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
              
              {entry.ai_analysis && (
                <div className="entry-analysis-preview">
                  {entry.ai_analysis.patternObservations && (
                    <p><strong>Pattern Observations:</strong> {entry.ai_analysis.patternObservations.substring(0, 80)}...</p>
                  )}
                  <p>{entry.ai_analysis.analysis ? entry.ai_analysis.analysis.substring(0, 100) + '...' : 'No analysis available.'}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JournalList;
