import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props){ super(props); this.state = { hasError: false, info: null }; }
  static getDerivedStateFromError(){ return { hasError: true }; }
  componentDidCatch(error, info){ this.setState({ info }); /* optional: console.error(error, info); */ }

  render(){
    if (this.state.hasError) {
      return (
        <main style={{padding:16, fontFamily:"system-ui"}}>
          <h2>Something went wrong.</h2>
          <p>This is a temporary ErrorBoundary fallback.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
