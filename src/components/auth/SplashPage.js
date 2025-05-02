import React from 'react';
import { Link } from 'react-router-dom';
import '../../styles/SplashPage.css';

const SplashPage = () => {
  return (
    <div className="splash-container">
      <div className="splash-content">
        <div className="logo-container">
          <img 
            src="/2ndOpinionMD-logo.jpg" 
            alt="2ndOpinionMD Logo" 
            className="splash-logo" 
          />
        </div>
        
        <h1 className="splash-title">2ndOpinionMD</h1>
        <p className="splash-subtitle">
          AI-powered second opinions for autoimmune disease diagnosis
        </p>
        
        <div className="splash-buttons">
          <Link to="/login" className="splash-button login-button">
            Log In
          </Link>
          <Link to="/register" className="splash-button signup-button">
            Sign Up
          </Link>
        </div>
        
        <div className="splash-features">
          <div className="feature">
            <i className="feature-icon brain-icon"></i>
            <h3>AI-Powered Analysis</h3>
            <p>Advanced algorithms analyze your symptoms for accurate insights</p>
          </div>
          
          <div className="feature">
            <i className="feature-icon journal-icon"></i>
            <h3>Symptom Journaling</h3>
            <p>Track symptoms, triggers, and patterns over time</p>
          </div>
          
          <div className="feature">
            <i className="feature-icon report-icon"></i>
            <h3>Comprehensive Reports</h3>
            <p>Detailed reports to share with your healthcare provider</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SplashPage;
