import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';
import './Auth.css';

const RegisterForm = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    
    setIsLoading(true);

    try {
      const response = await axios.post(
        getApiUrl(`${API_ENDPOINTS.AUTH}/register`),
        {
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name
        }
      );

      if (response.data) {
        navigate('/login', { 
          state: { 
            message: 'Registration successful! Please log in with your new account.' 
          } 
        });
      }
    } catch (err) {
      console.error('Registration error:', err);
      if (err.response?.data?.detail?.errors) {
        setError(err.response.data.detail.errors.join(', '));
      } else {
        setError(
          err.response?.data?.detail || 
          'Unable to register. Please try again with a different email.'
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <h2>Create an Account</h2>
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="full_name">Full Name</label>
          <input
            type="text"
            id="full_name"
            name="full_name"
            value={formData.full_name}
            onChange={handleChange}
            required
            className={error && error.includes('name') ? "form-control input-error" : "form-control"}
            placeholder="Enter your full name"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            className={error && error.includes('email') ? "form-control input-error" : "form-control"}
            placeholder="Enter your email address"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            minLength="8"
            className={error && error.includes('password') ? "form-control input-error" : "form-control"}
            placeholder="Create a password (min 8 characters)"
          />
          <small className="password-requirements">
            Password must contain: uppercase letter, lowercase letter, number, special character, minimum 8 characters
          </small>
        </div>
        
        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            minLength="8"
            className={error && error.includes('match') ? "form-control input-error" : "form-control"}
            placeholder="Confirm your password"
          />
        </div>
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Creating Account...' : 'Sign Up'}
        </button>
      </form>
      
      <div className="auth-links">
        Already have an account? <Link to="/login">Log in</Link>
      </div>
    </div>
  );
};

export default RegisterForm;
