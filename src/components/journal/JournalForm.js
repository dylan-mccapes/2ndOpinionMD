import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import '../../styles/Journal.css';

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
  const navigate = useNavigate();
  
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
      date: new Date().toISOString()
    };
    
    setIsLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }
      
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/journal/journal`,
        journalData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.data) {
        navigate('/journal', { 
          state: { 
            message: 'Journal entry created successfully!',
            entryId: response.data.id
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
  
  return (
    <div className="journal-form-container">
      <h2>New Journal Entry</h2>
      <p className="form-description">
        Track your symptoms, environmental factors, and other health metrics to help identify patterns.
      </p>
      
      {error && <div className="error-message">{error}</div>}
      
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
                  />
                </label>
              </div>
              
              <button 
                type="button" 
                className="remove-button"
                onClick={() => removeSymptom(index)}
                disabled={formData.symptoms.length === 1}
              >
                Remove
              </button>
            </div>
          ))}
          
          <button 
            type="button" 
            className="add-button"
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
                />
              </div>
              
              <button 
                type="button" 
                className="remove-button"
                onClick={() => removeFactor(index)}
                disabled={formData.environmental_factors.length === 1}
              >
                Remove
              </button>
            </div>
          ))}
          
          <button 
            type="button" 
            className="add-button"
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
              />
            </label>
          </div>
        </section>
        
        <section className="form-section">
          <h3>Additional Notes</h3>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="Any other observations or notes about your health today..."
            rows="4"
          />
        </section>
        
        <button 
          type="submit" 
          className="submit-button"
          disabled={isLoading}
        >
          {isLoading ? 'Saving...' : 'Save Journal Entry'}
        </button>
      </form>
    </div>
  );
};

export default JournalForm;
