import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { downloadTimelinePdf } from '../../utils/pdfGenerator';
import JournalAnalysisDisplay from './JournalAnalysisDisplay';
import JournalTimeline from './JournalTimeline';
import '../../styles/Journal.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const JournalForm = () => {
  const [formData, setFormData] = useState({
    symptoms: [{ symptom: '', severity: 5 }],
    environmental_factors: [{ factor_type: '', description: '' }],
    stress_level: 5,
    diet_notes: '',
    sleep_quality: 5,
    notes: ''
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [parsedSentences, setParsedSentences] = useState([]);
  const [showParsedView, setShowParsedView] = useState(false);
  const [previousDiagnoses, setPreviousDiagnoses] = useState([]);
  const [timelineData, setTimelineData] = useState(null);
  const [showTimeline, setShowTimeline] = useState(false);
  const navigate = useNavigate();
  
  useEffect(() => {
    const fetchReports = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        
        const response = await axios.get(
          getApiUrl(`/reports/user`),
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        if (response.data && response.data.length > 0) {
          setReports(response.data);
          const mostRecentReport = response.data.sort((a, b) => 
            new Date(b.createdAt) - new Date(a.createdAt)
          )[0];
          setSelectedReport(mostRecentReport);
          
          if (mostRecentReport.diagnosticResults) {
            setPreviousDiagnoses(mostRecentReport.diagnosticResults.map(diagnosis => ({
              name: diagnosis.name,
              confidence: diagnosis.confidence,
              staxLevel: diagnosis.staxLevel || 1,
              zone: diagnosis.zone || 1,
              status: 'confirmed'
            })));
          }
        }
      } catch (err) {
        console.error('Error fetching reports:', err);
        setError('Unable to fetch your reports. Please try again.');
      } finally {
        setReportsLoading(false);
      }
    };
    
    fetchReports();
  }, [navigate]);
  
  useEffect(() => {
    const fetchTimelineData = async () => {
      if (!selectedReport) return;
      
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const response = await axios.get(
          getApiUrl(`/journal/timeline/${selectedReport.id}`),
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        if (response.data) {
          setTimelineData({
            initialDiagnosis: {
              date: selectedReport.createdAt,
              diagnoses: selectedReport.diagnosticResults || []
            },
            journalEntries: response.data.journalEntries || []
          });
        }
      } catch (err) {
        console.error('Error fetching timeline data:', err);
      }
    };
    
    fetchTimelineData();
  }, [selectedReport]);
  
  useEffect(() => {
    if (formData.notes) {
      const sentences = formData.notes
        .split(/[.,!?;]+/)
        .map(sentence => sentence.trim())
        .filter(sentence => sentence.length > 0);
      setParsedSentences(sentences);
    } else {
      setParsedSentences([]);
    }
  }, [formData.notes]);
  
  const toggleParsedView = () => {
    setShowParsedView(!showParsedView);
  };
  
  const toggleTimeline = () => {
    setShowTimeline(!showTimeline);
  };
  
  const generateTimelinePdf = async () => {
    if (!selectedReport || !timelineData) {
      setError('No timeline data available to generate PDF');
      return;
    }
    
    try {
      setIsLoading(true);
      await downloadTimelinePdf(timelineData, `diagnosis-timeline-${selectedReport.id}.pdf`);
      setError(''); // Clear any previous errors
    } catch (err) {
      console.error('Error generating timeline PDF:', err);
      setError('Failed to generate timeline PDF. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleReportSelect = (e) => {
    const reportId = e.target.value;
    const report = reports.find(r => r.id === reportId);
    setSelectedReport(report);
    
    if (report && report.diagnosticResults) {
      setPreviousDiagnoses(report.diagnosticResults.map(diagnosis => ({
        name: diagnosis.name,
        confidence: diagnosis.confidence,
        staxLevel: diagnosis.staxLevel || 1,
        zone: diagnosis.zone || 1,
        status: 'confirmed'
      })));
    } else {
      setPreviousDiagnoses([]);
    }
  };
  
  const handleSymptomChange = (index, field, value) => {
    const updatedSymptoms = [...formData.symptoms];
    updatedSymptoms[index] = {
      ...updatedSymptoms[index],
      [field]: field === 'severity' ? parseInt(value) : value
    };
    
    setFormData({
      ...formData,
      symptoms: updatedSymptoms
    });
  };
  
  const addSymptom = () => {
    setFormData({
      ...formData,
      symptoms: [...formData.symptoms, { symptom: '', severity: 5 }]
    });
  };
  
  const removeSymptom = (index) => {
    if (formData.symptoms.length > 1) {
      const updatedSymptoms = formData.symptoms.filter((_, i) => i !== index);
      setFormData({
        ...formData,
        symptoms: updatedSymptoms
      });
    }
  };
  
  const handleFactorChange = (index, field, value) => {
    const updatedFactors = [...formData.environmental_factors];
    updatedFactors[index] = {
      ...updatedFactors[index],
      [field]: value
    };
    
    setFormData({
      ...formData,
      environmental_factors: updatedFactors
    });
  };
  
  const addFactor = () => {
    setFormData({
      ...formData,
      environmental_factors: [...formData.environmental_factors, { factor_type: '', description: '' }]
    });
  };
  
  const removeFactor = (index) => {
    if (formData.environmental_factors.length > 1) {
      const updatedFactors = formData.environmental_factors.filter((_, i) => i !== index);
      setFormData({
        ...formData,
        environmental_factors: updatedFactors
      });
    }
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: name === 'stress_level' || name === 'sleep_quality' 
        ? parseInt(value) 
        : value
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!selectedReport) {
      setError('Please complete a symptom intake form before journaling');
      return;
    }
    
    const validSymptoms = formData.symptoms.filter(s => s.symptom.trim() !== '');
    if (validSymptoms.length === 0) {
      setError('Please add at least one symptom');
      return;
    }
    
    const validFactors = formData.environmental_factors.filter(
      f => f.factor_type.trim() !== '' && f.description.trim() !== ''
    );
    
    const journalData = {
      ...formData,
      symptoms: validSymptoms,
      environmental_factors: validFactors,
      date: new Date().toISOString(),
      reportId: selectedReport.id,
      previousDiagnoses: previousDiagnoses,
      parsedSentences: parsedSentences
    };
    
    setIsLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }
      
      const response = await axios.post(
        getApiUrl(API_ENDPOINTS.JOURNAL),
        journalData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.data) {
        const aiAnalysis = response.data.ai_analysis || {};
        
        if (response.data.diagnoses) {
          const updatedDiagnoses = response.data.diagnoses.map(diagnosis => ({
            ...diagnosis,
            statusText: diagnosis.status === 'new' ? ' (NEW)' : 
                        diagnosis.status === 'confirmed' ? ' (CONFIRMED)' : 
                        diagnosis.status === 'eliminated' ? ' (ELIMINATED)' : '',
            staxLevel: diagnosis.staxLevel || (previousDiagnoses.find(d => d.name === diagnosis.name)?.staxLevel || 1),
            zone: diagnosis.zone || (previousDiagnoses.find(d => d.name === diagnosis.name)?.zone || 1)
          }));
          
          setSelectedReport({
            ...selectedReport,
            diagnosticResults: updatedDiagnoses
          });
          
          setPreviousDiagnoses(updatedDiagnoses);
        }
        
        navigate('/journal', { 
          state: { 
            message: 'Journal entry created successfully!',
            entryId: response.data.id,
            analysis: {
              analysis: response.data.ai_analysis?.analysis || "Your journal entry has been analyzed.",
              symptoms: response.data.ai_analysis?.symptoms || [],
              environmental_factors: response.data.ai_analysis?.environmental_factors || [],
              life_stressors: response.data.ai_analysis?.life_stressors || [],
              diagnoses: response.data.ai_analysis?.diagnoses || []
            },
            timelineData: timelineData
          } 
        });
      }
    } catch (err) {
      console.error('Error creating journal entry:', err);
      setError(
        err.response?.data?.detail || 
        'Unable to create journal entry. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };
  
  if (reports.length === 0 && !reportsLoading) {
    return (
      <div className="journal-form-container">
        <h2>Symptom Journal</h2>
        <div className="no-reports-message">
          <p>You need to complete a symptom intake form before journaling.</p>
          <p>The ethos of health model requires baseline diagnostic information to provide accurate analysis.</p>
          <button 
            className="btn btn-primary"
            onClick={() => navigate('/symptom-intake')}
          >
            Go to Symptom Intake
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="journal-form-container">
      <h2>Symptom Journal</h2>
      <p className="form-description">
        Track your symptoms, environmental factors, and other health metrics to help identify patterns.
      </p>
      
      {error && <div className="error-message">{error}</div>}
      
      {selectedReport && (
        <div className="selected-report-info">
          <h3>Based on Your Symptom Intake</h3>
          <div className="report-diagnoses">
            <div className="diagnoses-header">
              <p><strong>Current Diagnoses:</strong></p>
              <div className="timeline-buttons">
                <button 
                  type="button" 
                  className="btn btn-outline-info btn-sm"
                  onClick={toggleTimeline}
                >
                  {showTimeline ? 'Hide Timeline' : 'Show Timeline'}
                </button>
                {timelineData && (
                  <button 
                    type="button" 
                    className="btn btn-outline-secondary btn-sm ml-2"
                    onClick={generateTimelinePdf}
                    disabled={isLoading}
                  >
                    {isLoading ? 'Generating...' : 'Download Timeline PDF'}
                  </button>
                )}
              </div>
            </div>
            <ul>
              {previousDiagnoses.map((diagnosis, index) => (
                <li key={index}>
                  {diagnosis.name} - Confidence: {diagnosis.confidence}%
                </li>
              ))}
            </ul>
          </div>
          
          {showTimeline && timelineData && (
            <div className="timeline-container">
              <JournalTimeline timelineData={timelineData} />
            </div>
          )}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="journal-form">
        <section className="form-section">
          <h3>Symptoms</h3>
          
          {formData.symptoms.map((symptom, index) => (
            <div key={index} className="symptom-row">
              <div className="symptom-input">
                <input
                  type="text"
                  placeholder="Symptom name"
                  value={symptom.symptom}
                  onChange={(e) => handleSymptomChange(index, 'symptom', e.target.value)}
                  required={index === 0}
                  className="form-control"
                />
              </div>
              
              <div className="severity-slider">
                <label>
                  Severity: {symptom.severity}
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={symptom.severity}
                    onChange={(e) => handleSymptomChange(index, 'severity', e.target.value)}
                    className="form-range"
                  />
                </label>
              </div>
              
              <button 
                type="button" 
                className="btn btn-outline-danger remove-button"
                onClick={() => removeSymptom(index)}
                disabled={formData.symptoms.length === 1}
              >
                Remove
              </button>
            </div>
          ))}
          
          <button 
            type="button" 
            className="btn btn-outline-primary add-button"
            onClick={addSymptom}
          >
            Add Symptom
          </button>
        </section>
        
        <section className="form-section">
          <h3>Environmental Factors</h3>
          
          {formData.environmental_factors.map((factor, index) => (
            <div key={index} className="factor-row">
              <div className="factor-type">
                <select
                  value={factor.factor_type}
                  onChange={(e) => handleFactorChange(index, 'factor_type', e.target.value)}
                  required={index === 0}
                  className="form-select"
                >
                  <option value="">Select type</option>
                  <option value="food">Food</option>
                  <option value="product">Product</option>
                  <option value="environment">Environment</option>
                  <option value="medication">Medication</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div className="factor-description">
                <input
                  type="text"
                  placeholder="Description"
                  value={factor.description}
                  onChange={(e) => handleFactorChange(index, 'description', e.target.value)}
                  required={index === 0}
                  className="form-control"
                />
              </div>
              
              <button 
                type="button" 
                className="btn btn-outline-danger remove-button"
                onClick={() => removeFactor(index)}
                disabled={formData.environmental_factors.length === 1}
              >
                Remove
              </button>
            </div>
          ))}
          
          <button 
            type="button" 
            className="btn btn-outline-primary add-button"
            onClick={addFactor}
          >
            Add Factor
          </button>
        </section>
        
        <section className="form-section">
          <h3>Health Metrics</h3>
          
          <div className="metric-row">
            <label>
              Stress Level: {formData.stress_level}
              <input
                type="range"
                min="1"
                max="10"
                name="stress_level"
                value={formData.stress_level}
                onChange={handleChange}
                className="form-range"
              />
            </label>
          </div>
          
          <div className="metric-row">
            <label>
              Sleep Quality: {formData.sleep_quality}
              <input
                type="range"
                min="1"
                max="10"
                name="sleep_quality"
                value={formData.sleep_quality}
                onChange={handleChange}
                className="form-range"
              />
            </label>
          </div>
          
          <div className="metric-row">
            <label>
              Diet Notes:
              <textarea
                name="diet_notes"
                value={formData.diet_notes}
                onChange={handleChange}
                placeholder="Describe what you ate today, any dietary changes, etc."
                rows="3"
                className="form-control"
              />
            </label>
          </div>
        </section>
        
        <section className="form-section">
          <h3>Additional Notes</h3>
          <div className="notes-header">
            <label htmlFor="notes">Journal your health observations:</label>
            <button 
              type="button" 
              className="btn btn-outline-secondary btn-sm toggle-parsed-view"
              onClick={toggleParsedView}
            >
              {showParsedView ? 'Hide Parsed View' : 'Show Parsed View'}
            </button>
          </div>
          <textarea
            id="notes"
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="Any other observations or notes about your health today..."
            rows="4"
            className="form-control"
          />
          
          {showParsedView && parsedSentences.length > 0 && (
            <div className="parsed-sentences">
              <h4>How Your Journal Will Be Analyzed</h4>
              <p className="parsed-info">
                Your journal entry will be parsed into sentences and analyzed for symptoms, environmental factors, and life stressors.
                This helps our AI provide more accurate insights based on the ethos of health model.
              </p>
              <ul className="sentence-list">
                {parsedSentences.map((sentence, index) => (
                  <li key={index} className="parsed-sentence">
                    <span className="sentence-number">{index + 1}.</span>
                    <span className="sentence-text">{sentence}</span>
                  </li>
                ))}
              </ul>
              <div className="ethos-info">
                <p><strong>Ethos of Health Analysis:</strong> Each sentence will be evaluated to update your diagnostic terrain:</p>
                <ul>
                  <li>Symptoms will be matched to potential diagnoses</li>
                  <li>Environmental factors may reveal triggers</li>
                  <li>Life stressors can impact your Zone classification</li>
                  <li>STAX levels may be adjusted based on symptom complexity</li>
                </ul>
              </div>
            </div>
          )}
        </section>
        
        {formData.notes && (
          <section className="form-section">
            <h3>Preview Analysis</h3>
            <p className="analysis-preview-info">
              This is a preview of how your journal entry will be analyzed. The actual results may vary.
            </p>
            <JournalAnalysisDisplay 
              analysis={{
                analysis: "Based on your journal entry, our AI will analyze your health patterns and update your diagnoses accordingly.",
                summary: "Your journal entry will be analyzed to identify health patterns and update your diagnostic terrain.",
                symptoms: [],
                environmental_factors: [],
                life_stressors: [],
                diagnoses: previousDiagnoses.map(diag => ({
                  ...diag,
                  status: 'confirmed',
                  statusReason: "Based on your journal entry, this diagnosis remains confirmed."
                }))
              }}
            />
          </section>
        )}
        
        <div className="form-actions">
          <button 
            type="submit" 
            className="btn btn-primary submit-btn"
            disabled={isLoading}
          >
            {isLoading ? 'Saving...' : 'Save Journal Entry'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default JournalForm;
