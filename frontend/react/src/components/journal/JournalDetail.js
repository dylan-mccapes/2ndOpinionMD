import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import JournalAnalysisDisplay from './JournalAnalysisDisplay';
import '../../styles/Journal.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const JournalDetail = ({ testMode = false }) => {
  const [entry, setEntry] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const { entryId } = useParams();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchEntry = async () => {
      try {
        if (testMode) {
          const mockEntry = {
            id: 1,
            date: new Date().toISOString(),
            entry_text: 'Today I experienced joint pain in my hands and wrists. The stiffness was particularly bad this morning and lasted about an hour. I also felt quite fatigued throughout the day.',
            symptoms: [
              { symptom: 'Joint pain in hands', severity: 7 },
              { symptom: 'Morning stiffness', severity: 6 },
              { symptom: 'Fatigue', severity: 8 },
              { symptom: 'Wrist pain', severity: 6 }
            ],
            environmental_factors: [
              { factor_type: 'Weather', description: 'Cold and humid conditions' },
              { factor_type: 'Stress', description: 'Work deadline pressure' }
            ],
            stress_level: 7,
            sleep_quality: 6,
            diet_notes: 'Had more inflammatory foods this week, including processed snacks and less vegetables.',
            notes: 'Symptoms seem to be getting worse over the past few days. Need to track more carefully.',
            ai_analysis: {
              analysis: 'Based on your symptoms, there appears to be an inflammatory pattern consistent with autoimmune conditions. The combination of joint pain, morning stiffness, and fatigue suggests possible rheumatoid arthritis or similar inflammatory arthritis. The morning stiffness lasting over an hour is particularly significant as it indicates inflammatory rather than mechanical joint problems.',
              symptoms: ['feeling tired', 'joint pain in hands', 'morning stiffness', 'wrist pain'],
              environmental_factors: ['cold weather', 'humidity', 'work stress'],
              life_stressors: ['work deadlines', 'sleep disruption from pain'],
              diagnoses: [
                { 
                  name: 'Chronic Fatigue Syndrome', 
                  confidence: 60, 
                  status: 'new', 
                  staxLevel: 2, 
                  zone: 3, 
                  tags: ['#SuspectedDx_ChronicFatigueSyndrome', '#EarlyZoneShift', '#FatiguePattern'] 
                },
                { 
                  name: 'Rheumatoid Arthritis', 
                  confidence: 75, 
                  status: 'new', 
                  staxLevel: 2, 
                  zone: 3, 
                  tags: ['#SuspectedDx_RheumatoidArthritis', '#InflammatoryPattern', '#MorningStiffness'] 
                },
                { 
                  name: 'Fibromyalgia', 
                  confidence: 45, 
                  status: 'eliminated', 
                  staxLevel: 1, 
                  zone: 2, 
                  tags: ['#RuledOut_Fibromyalgia', '#LackOfTenderPoints'] 
                }
              ],
              followUpQuestions: [
                'How long does your morning stiffness typically last?', 
                'Have you noticed any swelling in your joints?',
                'Do you have any family history of autoimmune conditions?',
                'Have you experienced any skin rashes or sun sensitivity?'
              ],
              trackingSuggestions: [
                'Track morning stiffness duration daily', 
                'Monitor joint swelling patterns', 
                'Note weather correlation with symptoms',
                'Record sleep quality and its impact on symptoms',
                'Track response to anti-inflammatory medications'
              ],
              journalingRecommendation: { 
                promptType: 'Clinical', 
                suggestedPrompt: 'Describe your joint symptoms in detail, including which joints are affected, when symptoms are worst, and any factors that make them better or worse. Pay special attention to morning stiffness duration and any swelling you notice.' 
              },
              patternObservations: 'Symptoms appear to worsen in cold, humid weather and during periods of high stress. Morning stiffness lasting more than 30 minutes is particularly concerning and suggests inflammatory arthritis. The combination of fatigue and joint symptoms in a symmetric pattern is consistent with systemic autoimmune conditions.',
              timestamp: new Date().toISOString()
            }
          };
          setEntry(mockEntry);
          setIsLoading(false);
          return;
        }

        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        
        const response = await apiFetch(
          getApiUrl(`${API_ENDPOINTS.JOURNAL}/${entryId}`),
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        setEntry(response);
        
        if (response && response.reportId) {
          try {
            const timelineResponse = await apiFetch(
              getApiUrl(`${API_ENDPOINTS.JOURNAL}/timeline/${response.reportId}`),
              {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              }
            );
            
            if (timelineResponse) {
              setTimelineData({
                initialDiagnosis: {
                  date: response.createdAt,
                  diagnoses: response.previousDiagnoses || []
                },
                journalEntries: timelineResponse.journalEntries || []
              });
            }
          } catch (timelineErr) {
            console.error('Error fetching timeline data:', timelineErr);
          }
        }
      } catch (err) {
        console.error('Error fetching journal entry:', err);
        setError(err.message || 'Unable to load journal entry. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchEntry();
  }, [entryId, navigate, testMode]);
  
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
            {entry.symptoms.map((symptom, index) => {
              if (typeof symptom === 'string') {
                return (
                  <div key={index} className="symptom-tag low-severity">
                    {symptom}
                  </div>
                );
              } else if (symptom && typeof symptom === 'object') {
                const symptomText = symptom.symptom || '';
                const severity = symptom.severity || 5;
                return (
                  <div key={index} className={`symptom-tag ${getSeverityColor(severity)}`}>
                    {symptomText} ({severity}/10)
                  </div>
                );
              }
              return null;
            })}
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
