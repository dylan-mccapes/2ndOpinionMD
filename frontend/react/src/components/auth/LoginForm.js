import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import './Auth.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const LoginForm = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await apiFetch(
        getApiUrl(API_ENDPOINTS.AUTH_TOKEN),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ username: email, password }),
        }
      );

      if (response && response.access_token) {
        localStorage.setItem('token', response.access_token);
        
        const userResponse = await apiFetch(
          getApiUrl(API_ENDPOINTS.AUTH_ME),
          {
            headers: {
              'Authorization': `Bearer ${response.access_token}`
            }
          }
        );
        
        localStorage.setItem('user', JSON.stringify(userResponse));
        
        if (onLoginSuccess) {
          onLoginSuccess(userResponse);
        }
        
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      const status = err.status;
      if (status === 423) {
        setError('Account locked due to too many failed login attempts. Please reset your password or wait 15 minutes.');
      } else if (status === 401) {
        setError(err.message || 'Invalid email or password.');
      } else {
        setError(err.message || 'Unable to log in. Please check your credentials and try again.');
      }
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
      
      <h2>Log In</h2>
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={error ? "form-control input-error" : "form-control"}
            placeholder="Enter your email"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={error ? "form-control input-error" : "form-control"}
            placeholder="Enter your password"
          />
        </div>
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Logging in...' : 'Log In'}
        </button>
      </form>
      
      <div className="auth-links">
        <Link to="/forgot-password">Forgot your password?</Link><br />
        Don't have an account? <Link to="/register">Sign up</Link>
      </div>
    </div>
  );
};

export default LoginForm;
