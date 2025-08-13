import React from 'react';
import './SecurityBadge.css';

const SecurityBadge = () => {
  return (
    <div className="security-badge">
      <div className="security-icon">
        <svg 
          width="20" 
          height="20" 
          viewBox="0 0 20 20" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg"
        >
          <path 
            d="M10 0L0 4V10C0 15.5 4.5 20 10 20C15.5 20 20 15.5 20 10V4L10 0ZM10 11C9.4 11 9 10.6 9 10V6C9 5.4 9.4 5 10 5C10.6 5 11 5.4 11 6V10C11 10.6 10.6 11 10 11ZM10 15C9.4 15 9 14.6 9 14C9 13.4 9.4 13 10 13C10.6 13 11 13.4 11 14C11 14.6 10.6 15 10 15Z" 
            fill="#3C7D88"
          />
        </svg>
      </div>
      <div className="security-text">
        <p>HIPAA Compliant</p>
        <span className="security-details">Your data is secure &amp; protected</span>
      </div>
    </div>
  );
};

export default SecurityBadge;
