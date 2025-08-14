import React from 'react';
import './NetworkBackground.css';

const NetworkBackground = ({ opacity = 0.1 }) => {
  return (
    <div className="network-background" style={{ opacity }}>
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="network-pattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
            <circle cx="20" cy="20" r="1" fill="#3C7D88" />
          </pattern>
          <pattern id="network-lines" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="100" y2="100" stroke="#3C7D88" strokeWidth="0.5" strokeOpacity="0.2" />
            <line x1="100" y1="0" x2="0" y2="100" stroke="#3C7D88" strokeWidth="0.5" strokeOpacity="0.2" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#network-pattern)" />
        <rect width="100%" height="100%" fill="url(#network-lines)" />
      </svg>
    </div>
  );
};

export default NetworkBackground;
