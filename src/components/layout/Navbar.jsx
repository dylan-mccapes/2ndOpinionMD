import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = ({ user, onLogout }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          2ndOpinionMD.ai
        </Link>
        
        <button 
          className="hamburger-button"
          onClick={toggleMobileMenu}
          aria-label="Toggle mobile menu"
          aria-expanded={isMobileMenuOpen}
        >
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
        </button>
        
        <ul className="navbar-menu desktop-menu">
          <li className="navbar-item">
            <Link to="/dashboard" className="navbar-link">Dashboard</Link>
          </li>
          <li className="navbar-item">
            <Link to="/journal" className="navbar-link">Journal</Link>
          </li>
          <li className="navbar-item">
            <Link to="/intake" className="navbar-link">Symptom Intake</Link>
          </li>
          {user ? (
            <li className="navbar-item">
              <button onClick={onLogout} className="navbar-link logout-button">Logout</button>
            </li>
          ) : (
            <>
              <li className="navbar-item">
                <Link to="/login" className="navbar-link">Login</Link>
              </li>
              <li className="navbar-item">
                <Link to="/register" className="navbar-link">Register</Link>
              </li>
            </>
          )}
        </ul>
        
        <ul className={`navbar-menu mobile-menu ${isMobileMenuOpen ? 'mobile-menu-open' : ''}`}>
          <li className="navbar-item">
            <Link to="/dashboard" className="navbar-link" onClick={toggleMobileMenu}>Dashboard</Link>
          </li>
          <li className="navbar-item">
            <Link to="/journal" className="navbar-link" onClick={toggleMobileMenu}>Journal</Link>
          </li>
          <li className="navbar-item">
            <Link to="/intake" className="navbar-link" onClick={toggleMobileMenu}>Symptom Intake</Link>
          </li>
          {user ? (
            <li className="navbar-item">
              <button onClick={() => { onLogout(); toggleMobileMenu(); }} className="navbar-link logout-button">Logout</button>
            </li>
          ) : (
            <>
              <li className="navbar-item">
                <Link to="/login" className="navbar-link" onClick={toggleMobileMenu}>Login</Link>
              </li>
              <li className="navbar-item">
                <Link to="/register" className="navbar-link" onClick={toggleMobileMenu}>Register</Link>
              </li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
