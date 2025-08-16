import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import './Auth.css';
import { getApiUrl, API_ENDPOINTS } from '../../utils/apiConfig';

const EmailVerification = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying'); // 'verifying', 'success', 'error'
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        setStatus('error');
        setMessage('No verification token provided');
        return;
      }

      try {
        const response = await apiFetch(
          getApiUrl(`/auth/verify-email?token=${token}`)
        );
        
        setStatus('success');
        setMessage('Email verified successfully! You can now log in.');
        
        setTimeout(() => {
          navigate('/login');
        }, 3000);
        
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
        setMessage(
          err.message || 'Verification failed. The link may be invalid or expired.'
        );
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  return (
    <div className="auth-container">
      <h2>Email Verification</h2>
      
      {status === 'verifying' && (
        <div className="verification-status">
          <p>Verifying your email address...</p>
        </div>
      )}
      
      {status === 'success' && (
        <div className="verification-status success">
          <p>{message}</p>
          <p>Redirecting to login page in 3 seconds...</p>
        </div>
      )}
      
      {status === 'error' && (
        <div className="verification-status error">
          <div className="error-message">{message}</div>
          <div className="auth-links">
            <Link to="/login">Go to Login</Link> | 
            <Link to="/register">Register Again</Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailVerification;
