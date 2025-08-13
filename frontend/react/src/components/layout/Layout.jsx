import React from 'react';
import Navbar from './Navbar';
import Footer from './Footer';
import './Layout.css';

const Layout = ({ children, user, onLogout }) => {
  return (
    <div className="layout">
      <Navbar user={user} onLogout={onLogout} />
      <main className="main-content">{children}</main>
      <Footer />
    </div>
  );
};

export default Layout;
