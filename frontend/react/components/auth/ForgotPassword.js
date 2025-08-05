import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Auth.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setIsLoading(true);

    try {
      await axios.post(
        getApiUrl(`${API_ENDPOINTS.AUTH}/forgot-password`),
        { email }
      );
      
      setMessage('If an account with that email exists, a password reset link has been sent.');
    } catch (err) {
      console.error('Forgot password error:', err);
      setError(
        err.response?.data?.detail || 
        'Unable to send reset email. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-logo-container">
        <img src="/images/2ndOpinionMD-logo.jpg" alt="2ndOpinionMD Logo" className="auth-logo" />
        <h3 className="auth-logo-text">2ndOpinionMD</h3>
      </div>
      
      <h2>Reset Password</h2>
      {error && <div className="error-message">{error}</div>}
      {message && <div className="success-message">{message}</div>}
      
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="form-control"
            placeholder="Enter your email"
          />
        </div>
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Sending...' : 'Send Reset Link'}
        </button>
      </form>
      
      <div className="auth-links">
        Remember your password? <Link to="/login">Log in</Link>
      </div>
    </div>
  );
};

export default ForgotPassword;
