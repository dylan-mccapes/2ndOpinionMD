import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import Select from 'react-select';
import PropTypes from 'prop-types';
import { SYMPTOMS, PRIOR_DIAGNOSES, SEX_OPTIONS } from '../../utils/constants';
import { formatSymptomData } from '../../utils/formatData';
import { processSymptomInput } from '../../utils/openaiService';
import './SymptomIntakeForm.css';

const SymptomIntakeForm = ({ onSubmit }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { control, handleSubmit, formState: { errors } } = useForm();

  const processForm = async (data) => {
    setIsLoading(true);
    setError('');
    
    try {
      const formattedData = formatSymptomData(data);
      
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
      <p>Please provide your information to receive a second opinion analysis</p>
      
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
