import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import Select from 'react-select';
import PropTypes from 'prop-types';
import { SYMPTOMS, PRIOR_DIAGNOSES, SEX_OPTIONS, RACE_OPTIONS } from '../../utils/constants';
import { formatSymptomData } from '../../utils/formatData';
import { processSymptomInput } from '../../utils/openaiService';
import { ZONES, STAX_LEVELS, MISDIAGNOSIS_PATTERNS } from '../../utils/ethosOfHealth';
import './SymptomIntakeForm.css';

const SymptomIntakeForm = ({ onSubmit }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showEthosInfo, setShowEthosInfo] = useState(false);
  const { control, handleSubmit, formState: { errors } } = useForm();
  
  const toggleEthosInfo = () => {
    setShowEthosInfo(!showEthosInfo);
  };

  const processForm = async (data) => {
    setIsLoading(true);
    setError('');
    
    try {
      console.log('Form data submitted:', data);
      const formattedData = formatSymptomData(data);
      
      if (!data.race) {
        data.race = { value: 'prefer_not_to_say', label: 'Prefer not to say' };
      }
      
      const response = await processSymptomInput(data);
      
      if (response && response.error) {
        throw new Error(response.error);
      }
      
      onSubmit(response);
    } catch (err) {
      console.error('Error processing symptoms:', err);
      setError(err.response?.data?.detail || 'Failed to process symptoms. Please try again.');
      
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="symptom-intake-container">
      <h2>Symptom Intake Form</h2>
      <div className="form-header">
        <p>Please provide your information to receive a second opinion analysis</p>
        <button 
          type="button" 
          className="info-button"
          onClick={toggleEthosInfo}
        >
          ℹ️ About Ethos of Health
        </button>
      </div>
      
      {showEthosInfo && (
        <div className="ethos-info-box">
          <h3>About the Ethos of Health Model</h3>
          <p>The 2OPMD Diagnostic Terrain System is designed for autoimmune, rare, and misdiagnosed conditions. It evaluates:</p>
          <ul>
            <li><strong>Zones (1-5):</strong> {Object.entries(ZONES).map(([key, value]) => (
              <span key={key}>{key === '1' ? '' : ', '}{value}</span>
            ))}</li>
            <li><strong>STAX Levels (1-4):</strong> {Object.entries(STAX_LEVELS).map(([key, value]) => (
              <span key={key}>{key === '1' ? '' : ', '}{value}</span>
            ))}</li>
            <li><strong>Misdiagnosis Patterns:</strong> Identifying commonly misdiagnosed conditions through pattern recognition</li>
            <li><strong>Early Zone Shifts:</strong> Detecting early signs of terrain destabilization</li>
            <li><strong>Diagnostic Confidence:</strong> Requiring 95%+ certainty for final diagnoses</li>
          </ul>
          <p>This system helps provide more accurate diagnoses and personalized recommendations based on your unique health terrain.</p>
          <button 
            type="button" 
            className="close-info-button"
            onClick={toggleEthosInfo}
          >
            Close
          </button>
        </div>
      )}
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit(processForm)} className="symptom-form">
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="age">Age</label>
            <Controller
              name="age"
              control={control}
              rules={{ required: 'Age is required', min: { value: 1, message: 'Must be at least 1' }, max: { value: 120, message: 'Must be 120 or less' } }}
              defaultValue=""
              render={({ field }) => (
                <input 
                  {...field}
                  id="age" 
                  type="number" 
                  className={errors.age ? 'input-error' : ''}
                  placeholder="Enter your age"
                />
              )}
            />
            {errors.age && <span className="error-message">{errors.age.message}</span>}
          </div>
          
          <div className="form-group">
            <label htmlFor="sex">Sex</label>
            <Controller
              name="sex"
              control={control}
              rules={{ required: 'Sex is required' }}
              render={({ field }) => (
                <Select
                  {...field}
                  inputId="sex"
                  options={SEX_OPTIONS}
                  className={errors.sex ? 'select-error' : ''}
                  placeholder="Select your sex"
                  classNamePrefix="select"
                />
              )}
            />
            {errors.sex && <span className="error-message">{errors.sex.message}</span>}
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="height">Height</label>
            <Controller
              name="height"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <input 
                  {...field}
                  id="height" 
                  type="text" 
                  className={errors.height ? 'input-error' : ''}
                  placeholder="e.g., 5'10&quot; or 178cm"
                />
              )}
            />
            {errors.height && <span className="error-message">{errors.height.message}</span>}
          </div>
          
          <div className="form-group">
            <label htmlFor="weight">Weight (lbs)</label>
            <Controller
              name="weight"
              control={control}
              defaultValue=""
              rules={{ min: { value: 0, message: 'Weight cannot be negative' } }}
              render={({ field }) => (
                <input 
                  {...field}
                  id="weight" 
                  type="number" 
                  className={errors.weight ? 'input-error' : ''}
                  placeholder="Enter weight in pounds"
                />
              )}
            />
            {errors.weight && <span className="error-message">{errors.weight.message}</span>}
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="race">Race</label>
            <Controller
              name="race"
              control={control}
              render={({ field }) => (
                <Select
                  {...field}
                  inputId="race"
                  options={RACE_OPTIONS}
                  className={errors.race ? 'select-error' : ''}
                  placeholder="Select your race"
                  classNamePrefix="select"
                />
              )}
            />
            {errors.race && <span className="error-message">{errors.race.message}</span>}
          </div>
          
          <div className="form-group">
            <label htmlFor="occupation">Occupation</label>
            <Controller
              name="occupation"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <input 
                  {...field}
                  id="occupation" 
                  type="text" 
                  className={errors.occupation ? 'input-error' : ''}
                  placeholder="Enter your occupation"
                />
              )}
            />
            {errors.occupation && <span className="error-message">{errors.occupation.message}</span>}
          </div>
        </div>
        
        <div className="form-group">
          <label htmlFor="symptoms">Symptoms</label>
          <Controller
            name="symptoms"
            control={control}
            rules={{ required: 'At least one symptom is required' }}
            render={({ field }) => (
              <Select
                {...field}
                inputId="symptoms"
                options={SYMPTOMS}
                isMulti
                className={errors.symptoms ? 'select-error' : ''}
                placeholder="Select your symptoms"
                classNamePrefix="select"
              />
            )}
          />
          {errors.symptoms && <span className="error-message">{errors.symptoms.message}</span>}
        </div>
        
        <div className="form-group">
          <label htmlFor="durationMonths">Duration (months)</label>
          <Controller
            name="durationMonths"
            control={control}
            rules={{ required: 'Duration is required', min: { value: 0, message: 'Cannot be negative' } }}
            defaultValue=""
            render={({ field }) => (
              <input 
                {...field}
                id="durationMonths" 
                type="number" 
                className={errors.durationMonths ? 'input-error' : ''}
                placeholder="How long have you had these symptoms?"
              />
            )}
          />
          {errors.durationMonths && <span className="error-message">{errors.durationMonths.message}</span>}
        </div>
        
        <div className="form-group">
          <label htmlFor="priorDiagnoses">Prior Diagnoses (Optional)</label>
          <Controller
            name="priorDiagnoses"
            control={control}
            render={({ field }) => (
              <Select
                {...field}
                inputId="priorDiagnoses"
                options={PRIOR_DIAGNOSES}
                isMulti
                placeholder="Select any prior diagnoses"
                classNamePrefix="select"
              />
            )}
          />
        </div>
        
        <button 
          type="submit" 
          className="btn btn-primary submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Analyzing Symptoms...' : 'Generate Report'}
        </button>
      </form>
    </div>
  );
};

SymptomIntakeForm.propTypes = {
  onSubmit: PropTypes.func.isRequired
};

export default SymptomIntakeForm;
