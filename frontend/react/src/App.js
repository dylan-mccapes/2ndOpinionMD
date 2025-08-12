import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import './App.css';

function AppContent() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      setIsAuthenticated(true);
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLoginSuccess = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
    navigate('/login');
  };

  return (
    <div className="App">
      <Routes>
        <Route path="/login" element={
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <h1>2ndOpinionMD Login</h1>
            <p>Login form would be here</p>
            <button onClick={() => handleLoginSuccess({full_name: 'Test User'})}>
              Test Login
            </button>
          </div>
        } />
        
        <Route path="/journal" element={
          !isAuthenticated ? <Navigate to="/login" /> : (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <h1>Journal</h1>
              <p>Journal functionality would be here</p>
              <button onClick={handleLogout}>Logout</button>
            </div>
          )
        } />
        
        <Route path="/diagnose" element={
          !isAuthenticated ? <Navigate to="/login" /> : (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <h1>Diagnose</h1>
              <p>Diagnosis functionality would be here</p>
              <button onClick={handleLogout}>Logout</button>
            </div>
          )
        } />
        
        <Route path="/diagnostics" element={
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <h1>Diagnostics</h1>
            <p>Diagnostics page (unlinked from main nav)</p>
          </div>
        } />
        
        <Route path="/" element={
          !isAuthenticated ? <Navigate to="/login" /> : (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <h1>Welcome, {user?.full_name || 'User'}</h1>
              <p>Dashboard would be here</p>
              <div>
                <a href="/journal" style={{margin: '10px'}}>Journal</a>
                <a href="/diagnose" style={{margin: '10px'}}>Diagnose</a>
              </div>
              <button onClick={handleLogout}>Logout</button>
            </div>
          )
        } />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
