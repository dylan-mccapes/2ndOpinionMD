import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import Select from 'react-select';
import PropTypes from 'prop-types';
import { SYMPTOMS, PRIOR_DIAGNOSES, SEX_OPTIONS, RACE_OPTIONS } from '../../utils/constants';
import { formatSymptomData } from '../../utils/formatData';
import { processSymptomInput } from '../../utils/openaiService';
import { MISDIAGNOSIS_PATTERNS } from '../../utils/ethosOfHealth';
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
      const isDebug = process.env.NODE_ENV !== 'production' || /[?&]debug=1\b/.test(window.location.search);
      isDebug && console.log('Form data submitted:', data);
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
      isDebug && console.error('Error processing symptoms:', err);
      setError(err.response?.data?.detail || 'Failed to process symptoms. Please try again.');
      
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="symptom-intake-container">
      <h2>Symptom Intake Form</h2>
      <div className="form-header">
        <p>Please provide your information to receive a second opinion diagnostic analysis</p>
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
            <li><strong>Symptom Analysis:</strong> Comprehensive evaluation of your symptom patterns and presentation</li>
            <li><strong>Misdiagnosis Patterns:</strong> Identifying commonly misdiagnosed conditions through pattern recognition</li>
            <li><strong>Risk Assessment:</strong> Detecting early signs of health changes and potential concerns</li>
            <li><strong>Diagnostic Confidence:</strong> Providing confidence scores for potential diagnoses</li>
          </ul>
          <p>This system helps provide more accurate diagnoses and personalized recommendations based on your unique health profile.</p>
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
        <section className="form-section">
          <h3>What is your birthdate?</h3>
          <div className="form-group">
            <Controller
              name="birthdate"
              control={control}
              rules={{ required: 'Birthdate is required' }}
              defaultValue=""
              render={({ field }) => (
                <input 
                  {...field}
                  id="birthdate" 
                  type="date" 
                  className={errors.birthdate ? 'input-error' : ''}
                  max={new Date().toISOString().split('T')[0]}
                />
              )}
            />
            {errors.birthdate && <span className="error-message">{errors.birthdate.message}</span>}
          </div>
        </section>

        <section className="form-section">
          <h3>What is your sex?</h3>
          <div className="form-group">
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
        </section>
        
        <section className="form-section">
          <h3>What is your height?</h3>
          <div className="form-group">
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
        </section>

        <section className="form-section">
          <h3>What is your weight?</h3>
          <div className="form-group">
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
        </section>
        
        <section className="form-section">
          <h3>What is your race/ethnicity?</h3>
          <div className="form-group">
            <Controller
              name="race"
              control={control}
              render={({ field }) => (
                <Select
                  {...field}
                  inputId="race"
                  options={RACE_OPTIONS}
                  className={errors.race ? 'select-error' : ''}
                  placeholder="Select your race/ethnicity"
                  classNamePrefix="select"
                />
              )}
            />
            {errors.race && <span className="error-message">{errors.race.message}</span>}
          </div>
        </section>

        <section className="form-section">
          <h3>What is your occupation?</h3>
          <div className="form-group">
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
        </section>
        
        <section className="form-section">
          <h3>What are your symptoms? <span className="ethos-label">(Used for diagnostic analysis)</span></h3>
          <div className="form-group">
            <Controller
              name="symptoms"
              control={control}
              rules={{ required: 'Please describe your symptoms' }}
              defaultValue=""
              render={({ field }) => (
                <textarea
                  {...field}
                  id="symptoms"
                  className={errors.symptoms ? 'input-error' : ''}
                  placeholder="Please describe all your symptoms in detail..."
                  rows="4"
                />
              )}
            />
            {errors.symptoms && <span className="error-message">{errors.symptoms.message}</span>}
          </div>
        </section>
        
        <section className="form-section">
          <h3>How long have you had these symptoms?</h3>
          <div className="form-group">
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
                  placeholder="Duration in months"
                />
              )}
            />
            {errors.durationMonths && <span className="error-message">{errors.durationMonths.message}</span>}
          </div>
        </section>
        
        <section className="form-section">
          <h3>What environmental factors might be affecting your health?</h3>
          <div className="form-group">
            <Controller
              name="environmental_factors"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <textarea
                  {...field}
                  id="environmental_factors"
                  className={errors.environmental_factors ? 'input-error' : ''}
                  placeholder="Describe any environmental factors such as foods, products, chemicals, workplace conditions, living environment, etc. that you think might be affecting your health..."
                  rows="3"
                />
              )}
            />
            {errors.environmental_factors && <span className="error-message">{errors.environmental_factors.message}</span>}
          </div>
        </section>

        <section className="form-section">
          <h3>What life stressors are you currently experiencing?</h3>
          <div className="form-group">
            <Controller
              name="life_stressors"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <textarea
                  {...field}
                  id="life_stressors"
                  className={errors.life_stressors ? 'input-error' : ''}
                  placeholder="Describe any current life stressors such as work stress, relationship issues, financial concerns, major life changes, etc..."
                  rows="3"
                />
              )}
            />
            {errors.life_stressors && <span className="error-message">{errors.life_stressors.message}</span>}
          </div>
        </section>

        <section className="form-section">
          <h3>Do you have any prior diagnoses? (Optional)</h3>
          <div className="form-group">
            <Controller
              name="priorDiagnoses"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <textarea
                  {...field}
                  id="priorDiagnoses"
                  className={errors.priorDiagnoses ? 'input-error' : ''}
                  placeholder="List any previous medical diagnoses you have received..."
                  rows="3"
                />
              )}
            />
            {errors.priorDiagnoses && <span className="error-message">{errors.priorDiagnoses.message}</span>}
          </div>
        </section>
        
        <div className="ethos-evaluation-info">
          <h3>Diagnostic Health Evaluation</h3>
          <p>Your symptom data will be analyzed using our Ethos of Health model to determine:</p>
          <ul>
            <li><strong>Symptom Patterns:</strong> How your symptoms relate to potential conditions</li>
            <li><strong>Risk Factors:</strong> Important symptoms and suggested tests to discuss with your doctor</li>
            <li><strong>Diagnostic Confidence:</strong> How certain we are about potential diagnoses</li>
          </ul>
          <p>This information will be displayed in your diagnostic report.</p>
        </div>
        
        <div className="disclaimer">
          <h3>Important Notice</h3>
          <p>This tool is designed to help you track and journal your symptoms to share with your healthcare provider. The generated report is for informational purposes only and is not a medical diagnosis. Please consult with a healthcare professional for proper evaluation and diagnosis.</p>
        </div>
        
        <button 
          type="submit" 
          className="btn btn-primary submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Analyzing Symptoms...' : 'Generate Diagnostic Report'}
        </button>
      </form>
    </div>
  );
};

SymptomIntakeForm.propTypes = {
  onSubmit: PropTypes.func.isRequired
};

export default SymptomIntakeForm;
