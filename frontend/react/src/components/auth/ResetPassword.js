import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import './Auth.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [token, setToken] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      setError('No reset token provided');
      return;
    }
    setToken(tokenParam);
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      await apiFetch(
        getApiUrl(`/auth/reset-password/${token}`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_password: password })
        }
      );
      
      alert('Password reset successfully! You can now log in with your new password.');
      navigate('/login');
    } catch (err) {
      console.error('Reset password error:', err);
      setError(err.message || 'Unable to reset password. The link may be invalid or expired.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="auth-container">
        <div className="error-message">Invalid reset link</div>
        <div className="auth-links">
          <Link to="/login">Go to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-logo-container">
        <img src="/images/2ndOpinionMD-logo.jpg" alt="2ndOpinionMD Logo" className="auth-logo" />
        <h3 className="auth-logo-text">2ndOpinionMD</h3>
      </div>
      
      <h2>Reset Password</h2>
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label htmlFor="password">New Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="form-control"
            placeholder="Enter new password"
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
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            className="form-control"
            placeholder="Confirm new password"
          />
        </div>
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={isLoading}
        >
          {isLoading ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>
      
      <div className="auth-links">
        Remember your password? <Link to="/login">Log in</Link>
      </div>
    </div>
  );
};

export default ResetPassword;
