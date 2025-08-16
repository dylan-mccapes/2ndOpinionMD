import React, { Component } from 'react';
import PropTypes from 'prop-types';
import './ErrorBoundary.css';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React Error Boundary caught an error:', error);
    console.error('Component stack trace:', errorInfo.componentStack);
    
    this.setState({
      error,
      errorInfo
    });
    
  }

  render() {
    if (this.state.hasError) {
      const errorMsg = typeof this.state.error === 'string'
        ? this.state.error
        : this.state.error?.message
        ?? (() => { try { return JSON.stringify(this.state.error); } catch { return 'Something went wrong'; } })();

      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <details>
            <summary>View Error Details</summary>
            <p>{errorMsg}</p>
            <p>Component Stack:</p>
            <pre>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
          </details>
          <button 
            className="error-retry-button"
            onClick={() => {
              this.setState({ hasError: false, error: null, errorInfo: null });
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired
};

export default ErrorBoundary;
