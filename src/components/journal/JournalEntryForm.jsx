import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useForm } from 'react-hook-form';
import './JournalEntryForm.css';

const JournalEntryForm = ({ onSubmit }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register, handleSubmit, reset, formState: { errors } } = useForm();
  
  const processEntry = async (data) => {
    setLoading(true);
    setError('');
    
    try {
      if (onSubmit) {
        await onSubmit(data.entry);
      }
      reset();
    } catch (err) {
      console.error('Error submitting journal entry:', err);
      setError(err.response?.data?.detail || 'Failed to process journal entry. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="journal-form-container">
      <h2>Symptom Journal</h2>
      <p>Track your symptoms over time and get AI-powered insights</p>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit(processEntry)} className="journal-form">
        <div className="form-group">
          <label htmlFor="entry">How are you feeling today?</label>
          <textarea
            id="entry"
            className={errors.entry ? 'form-control input-error' : 'form-control'}
            rows="6"
            {...register('entry', { 
              required: 'Please enter your journal entry',
              minLength: { value: 10, message: 'Entry must be at least 10 characters' }
            })}
            placeholder="Describe your symptoms, energy levels, and any changes since your last entry..."
          />
          {errors.entry && <span className="error-message">{errors.entry.message}</span>}
        </div>
        
        <button 
          type="submit" 
          className="btn btn-primary submit-btn"
          disabled={loading}
        >
          {loading ? 'Analyzing...' : 'Submit Journal Entry'}
        </button>
      </form>
    </div>
  );
};

JournalEntryForm.propTypes = {
  onSubmit: PropTypes.func
};

export default JournalEntryForm;
