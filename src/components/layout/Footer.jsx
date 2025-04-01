import React from 'react';
import { Link } from 'react-router-dom';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-logo">
            <h3>2ndOpinionMD.ai</h3>
            <p>AI-powered second opinions for autoimmune disease</p>
          </div>
          <div className="footer-links">
            <div className="footer-links-section">
              <h4>Legal</h4>
              <ul>
                <li><Link to="/privacy">Privacy Policy</Link></li>
                <li><Link to="/disclaimer">Disclaimer</Link></li>
                <li><Link to="/hipaa">HIPAA Compliance</Link></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} 2ndOpinionMD.ai. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
