import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import JournalAnalysisDisplay from './JournalAnalysisDisplay';
import '../../styles/Journal.css';

const JournalDetail = () => {
  const [entry, setEntry] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const { entryId } = useParams();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchEntry = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal/${entryId}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        setEntry(response.data);
        
        if (response.data && response.data.reportId) {
          try {
            const timelineResponse = await axios.get(
              `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/timeline/${response.data.reportId}`,
              {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              }
            );
            
            if (timelineResponse.data) {
              setTimelineData({
                initialDiagnosis: {
                  date: response.data.createdAt,
                  diagnoses: response.data.previousDiagnoses || []
                },
                journalEntries: timelineResponse.data.journalEntries || []
              });
            }
          } catch (timelineErr) {
            console.error('Error fetching timeline data:', timelineErr);
          }
        }
      } catch (err) {
        console.error('Error fetching journal entry:', err);
        setError('Unable to load journal entry. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchEntry();
  }, [entryId, navigate]);
  
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const getSeverityColor = (severity) => {
    if (severity <= 3) return 'low-severity';
    if (severity <= 6) return 'medium-severity';
    return 'high-severity';
  };
  
  if (isLoading) {
    return <div className="loading">Loading journal entry...</div>;
  }
  
  if (error) {
    return (
      <div className="journal-detail-container">
        <div className="error-message">{error}</div>
        <Link to="/journal" className="back-button">
          Back to Journal
        </Link>
      </div>
    );
  }
  
  if (!entry) {
    return (
      <div className="journal-detail-container">
        <div className="error-message">Journal entry not found.</div>
        <Link to="/journal" className="back-button">
          Back to Journal
        </Link>
      </div>
    );
  }
  
  return (
    <div className="journal-detail-container">
      <div className="journal-detail-header">
        <Link to="/journal" className="back-button">
          &larr; Back to Journal
        </Link>
        <h2>Journal Entry: {formatDate(entry.date)}</h2>
      </div>
      
      <div className="journal-detail-content">
        <section className="detail-section">
          <h3>Symptoms</h3>
          <div className="symptom-tags">
            {entry.symptoms.map((symptom, index) => (
              <div key={index} className={`symptom-tag ${getSeverityColor(symptom.severity)}`}>
                {symptom.symptom} ({symptom.severity}/10)
              </div>
            ))}
          </div>
        </section>
        
        {entry.environmental_factors && entry.environmental_factors.length > 0 && (
          <section className="detail-section">
            <h3>Environmental Factors</h3>
            <ul className="factors-list">
              {entry.environmental_factors.map((factor, index) => (
                <li key={index}>
                  <strong>{factor.factor_type}:</strong> {factor.description}
                </li>
              ))}
            </ul>
          </section>
        )}
        
        <section className="detail-section metrics-section">
          <h3>Health Metrics</h3>
          <div className="metrics-grid">
            {entry.stress_level && (
              <div className="metric">
                <h4>Stress Level</h4>
                <div className={`metric-value ${getSeverityColor(entry.stress_level)}`}>
                  {entry.stress_level}/10
                </div>
              </div>
            )}
            
            {entry.sleep_quality && (
              <div className="metric">
                <h4>Sleep Quality</h4>
                <div className={`metric-value ${getSeverityColor(10 - entry.sleep_quality + 1)}`}>
                  {entry.sleep_quality}/10
                </div>
              </div>
            )}
          </div>
          
          {entry.diet_notes && (
            <div className="diet-notes">
              <h4>Diet Notes</h4>
              <p>{entry.diet_notes}</p>
            </div>
          )}
        </section>
        
        {entry.notes && (
          <section className="detail-section">
            <h3>Additional Notes</h3>
            <p>{entry.notes}</p>
          </section>
        )}
        
        {entry.ai_analysis && (
          <section className="detail-section ai-analysis">
            <JournalAnalysisDisplay 
              analysis={entry.ai_analysis} 
              timelineData={timelineData} 
            />
          </section>
        )}
      </div>
    </div>
  );
};

export default JournalDetail;
