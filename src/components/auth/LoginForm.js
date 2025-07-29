import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import './Auth.css';

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
      const formData = new FormData();
      formData.append('username', email); // FastAPI expects 'username' field
      formData.append('password', password);

      const response = await axios.post(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/auth/token`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (response.data && response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        
        const userResponse = await axios.get(
          `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/auth/me`,
          {
            headers: {
              'Authorization': `Bearer ${response.data.access_token}`
            }
          }
        );
        
        localStorage.setItem('user', JSON.stringify(userResponse.data));
        
        if (onLoginSuccess) {
          onLoginSuccess(userResponse.data);
        }
        
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      if (err.response?.status === 423) {
        setError('Account locked due to too many failed login attempts. Please reset your password or wait 15 minutes.');
      } else {
        setError(
          err.response?.data?.detail || 
          'Unable to log in. Please check your credentials and try again.'
        );
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
