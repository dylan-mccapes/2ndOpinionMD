import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = ({ user, onLogout }) => {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          2ndOpinionMD.ai
        </Link>
        <ul className="navbar-menu">
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
      </div>
    </nav>
  );
};

export default Navbar;
