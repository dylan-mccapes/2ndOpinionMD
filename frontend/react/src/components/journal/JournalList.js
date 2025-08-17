import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import { downloadJournalTimelinePdf } from '../../utils/pdfGenerator';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import { normalizeStringList } from '../../utils/normalizeList';
import '../../styles/Journal.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const JournalList = () => {
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchEntries = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          const mockEntries = [
            {
              id: 1,
              date: new Date().toISOString(),
              entry_text: 'Today I experienced joint pain in my hands and wrists. The stiffness was particularly bad this morning and lasted about an hour. I also felt quite fatigued throughout the day.',
              symptoms: [
                { symptom: 'Joint pain in hands', severity: 7 },
                { symptom: 'Morning stiffness', severity: 6 },
                { symptom: 'Fatigue', severity: 8 }
              ],
              ai_analysis: {
                analysis: 'Based on your symptoms, there appears to be an inflammatory pattern consistent with autoimmune conditions. The combination of joint pain, morning stiffness, and fatigue suggests possible rheumatoid arthritis or similar inflammatory arthritis.',
                symptoms: ['feeling tired', 'joint pain in hands', 'morning stiffness'],
                diagnoses: [
                  { name: 'Chronic Fatigue Syndrome', confidence: 60, status: 'new', staxLevel: 2, zone: 3, tags: ['#SuspectedDx_ChronicFatigueSyndrome', '#EarlyZoneShift'] },
                  { name: 'Rheumatoid Arthritis', confidence: 75, status: 'new', staxLevel: 2, zone: 3, tags: ['#SuspectedDx_RheumatoidArthritis', '#InflammatoryPattern'] }
                ],
                followUpQuestions: ['How long does your morning stiffness typically last?', 'Have you noticed any swelling in your joints?'],
                trackingSuggestions: ['Track morning stiffness duration daily', 'Monitor joint swelling patterns', 'Note weather correlation with symptoms'],
                journalingRecommendation: { promptType: 'Clinical', suggestedPrompt: 'Describe your joint symptoms in detail, including which joints are affected and when symptoms are worst.' },
                patternObservations: 'Symptoms appear to worsen in cold, humid weather and during periods of high stress. Morning stiffness lasting more than 30 minutes is particularly concerning.',
                timestamp: new Date().toISOString()
              }
            },
            {
              id: 2,
              date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
              entry_text: 'Brain fog was prominent today, along with some knee pain. Energy levels were low, making it difficult to concentrate at work.',
              symptoms: [
                { symptom: 'Brain fog', severity: 6 },
                { symptom: 'Joint pain in knees', severity: 5 },
                { symptom: 'Low energy', severity: 7 }
              ],
              ai_analysis: {
                analysis: 'Continued inflammatory symptoms with cognitive involvement. The presence of brain fog alongside joint symptoms strengthens the autoimmune hypothesis.',
                symptoms: ['brain fog', 'joint pain in knees', 'low energy'],
                diagnoses: [
                  { name: 'Migraine', confidence: 50, status: 'new', staxLevel: 2, zone: 3, tags: ['#SuspectedDx_Migraine', '#CognitiveSymptoms'] },
                  { name: 'Systemic Lupus Erythematosus', confidence: 65, status: 'ongoing', staxLevel: 3, zone: 4, tags: ['#SuspectedDx_Lupus', '#MultiSystemInvolvement'] }
                ],
                followUpQuestions: ['How often do you experience brain fog?', 'Do you have any skin rashes or sun sensitivity?'],
                trackingSuggestions: ['Monitor cognitive symptoms daily', 'Track energy levels throughout the day', 'Note any skin changes'],
                journalingRecommendation: { promptType: 'Symptom Tracking', suggestedPrompt: 'Focus on describing your cognitive symptoms and how they impact your daily activities.' },
                patternObservations: 'Symptoms show consistency over time with some variation in severity. Cognitive symptoms are becoming more prominent.',
                timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
              }
            }
          ];
          setEntries(mockEntries);
          setIsLoading(false);
          return;
        }
        
        const response = await apiFetch(
          getApiUrl(API_ENDPOINTS.JOURNAL),
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        setEntries(response);
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
      
      await apiFetch(
        getApiUrl(`${API_ENDPOINTS.JOURNAL}/${entryId}`),
        {
          method: 'DELETE',
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

  const handleDownloadReport = async () => {
    if (entries.length === 0) {
      setError('No journal entries to download.');
      return;
    }
    
    setIsDownloading(true);
    setError('');
    
    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        const mockEntries = [
          {
            id: 1,
            date: new Date().toISOString(),
            symptoms: [
              { symptom: 'Joint pain in hands', severity: 7 },
              { symptom: 'Morning stiffness', severity: 6 },
              { symptom: 'Fatigue', severity: 8 }
            ],
            environmental_factors: [
              { factor_type: 'Weather', description: 'Cold and humid conditions' },
              { factor_type: 'Stress', description: 'Work deadline pressure' }
            ],
            ai_analysis: {
              analysis: 'Based on your symptoms, there appears to be an inflammatory pattern consistent with autoimmune conditions. The combination of joint pain, morning stiffness, and fatigue suggests possible rheumatoid arthritis or similar inflammatory arthritis.',
              patternObservations: 'Symptoms appear to worsen in cold, humid weather and during periods of high stress. Morning stiffness lasting more than 30 minutes is particularly concerning.',
              life_stressors: ['Work-related stress', 'Sleep disruption from pain'],
              diagnoses: [
                { name: 'Rheumatoid Arthritis', confidence: 75, status: 'new' },
                { name: 'Fibromyalgia', confidence: 45, status: 'eliminated' },
                { name: 'Lupus', confidence: 60, status: 'ongoing' }
              ]
            }
          },
          {
            id: 2,
            date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            symptoms: [
              { symptom: 'Brain fog', severity: 6 },
              { symptom: 'Joint pain in knees', severity: 5 },
              { symptom: 'Low energy', severity: 7 }
            ],
            environmental_factors: [
              { factor_type: 'Diet', description: 'High inflammatory foods this week' },
              { factor_type: 'Exercise', description: 'Reduced activity due to pain' }
            ],
            ai_analysis: {
              analysis: 'Continued inflammatory symptoms with cognitive involvement. The presence of brain fog alongside joint symptoms strengthens the autoimmune hypothesis.',
              patternObservations: 'Symptoms show consistency over time with some variation in severity. Cognitive symptoms are becoming more prominent.',
              life_stressors: ['Dietary changes needed', 'Exercise limitations'],
              diagnoses: [
                { name: 'Rheumatoid Arthritis', confidence: 80, status: 'ongoing' },
                { name: 'Systemic Lupus Erythematosus', confidence: 65, status: 'new' }
              ]
            }
          }
        ];
        
        await downloadJournalTimelinePdf(mockEntries, `journal-timeline-test-${Date.now()}.pdf`);
        return;
      }
      
      const response = await apiFetch(
        getApiUrl(`${API_ENDPOINTS.JOURNAL}?limit=1000`),
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      await downloadJournalTimelinePdf(response, `journal-timeline-${Date.now()}.pdf`);
    } catch (err) {
      console.error('Error downloading journal report:', err);
      setError('Unable to download journal report. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };
  
  if (isLoading) {
    return <div className="loading">Loading journal entries...</div>;
  }
  
  return (
    <div className="journal-list-container">
      <div className="journal-header">
        <h2>Your Journal Entries</h2>
        <div className="header-buttons">
          <button 
            onClick={handleDownloadReport}
            className="download-report-button"
            disabled={isDownloading || entries.length === 0}
          >
            {isDownloading ? 'Generating...' : 'Download Report'}
          </button>
          <Link to="/journal/new" className="new-entry-button">
            New Entry
          </Link>
        </div>
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
                  {(() => {
                    const normalized = normalizeStringList(entry.ai_analysis?.symptoms ?? entry.symptoms);
                    return normalized.slice(0, 3).map((symptom, index) => (
                      <li key={index} className="symptom-tag low-severity">
                        {symptom}
                      </li>
                    )).concat(
                      normalized.length > 3
                        ? [<li key="more" className="more-symptoms">+{normalized.length - 3} more</li>]
                        : []
                    );
                  })()}
                </ul>
              </div>
              
              {entry.ai_analysis && (() => {
                const analysis = parseJournalAnalysis(entry.ai_analysis);
                if (!analysis) return null;
                
                return (
                  <div className="entry-analysis-preview">
                    {/* Show top diagnosis with confidence */}
                    {analysis.diagnoses && analysis.diagnoses.length > 0 && (
                      <div className="top-diagnosis">
                        <strong>Top Diagnosis:</strong> {analysis.diagnoses[0].name}
                        {analysis.diagnoses[0].confidence && (
                          <span className="confidence"> ({analysis.diagnoses[0].confidence}%)</span>
                        )}
                        {/* Show first 2-3 tags */}
                        {analysis.diagnoses[0].tags && analysis.diagnoses[0].tags.length > 0 && (
                          <div className="preview-tags">
                            {analysis.diagnoses[0].tags.slice(0, 3).map((tag, i) => (
                              <span key={i} className="preview-tag">{tag}</span>
                            ))}
                            {analysis.diagnoses[0].tags.length > 3 && (
                              <span className="more-tags">+{analysis.diagnoses[0].tags.length - 3} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {/* Fallback to analysis text if no diagnoses */}
                    {(!analysis.diagnoses || analysis.diagnoses.length === 0) && analysis.analysis && (
                      <p>{analysis.analysis.substring(0, 100)}...</p>
                    )}
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JournalList;
