import { Component, type ReactNode, type ErrorInfo } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    const { error, errorInfo } = this.state;

    return (
      <div
        className="max-w-2xl mx-auto p-6"
        style={{ color: 'var(--text-primary)' }}
      >
        <div
          className="p-6 rounded-xl border"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--accent-red)',
          }}
        >
          <h1
            className="text-lg font-mono font-bold mb-4"
            style={{ color: 'var(--accent-red)' }}
          >
            RENDER ERROR
          </h1>

          <div className="space-y-4">
            <div>
              <p
                className="text-xs font-mono font-bold mb-1"
                style={{ color: 'var(--text-secondary)' }}
              >
                CAUSE
              </p>
              <p
                className="text-sm font-mono p-3 rounded-lg"
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  borderLeft: '2px solid var(--accent-red)',
                }}
              >
                {error?.message ?? 'Unknown error'}
              </p>
            </div>

            {error?.name && error.name !== 'Error' && (
              <div>
                <p
                  className="text-xs font-mono font-bold mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  TYPE
                </p>
                <p
                  className="text-sm font-mono"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {error.name}
                </p>
              </div>
            )}

            {errorInfo?.componentStack && (
              <div>
                <p
                  className="text-xs font-mono font-bold mb-1"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  COMPONENT STACK
                </p>
                <pre
                  className="text-xs font-mono p-3 rounded-lg overflow-auto"
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-muted)',
                    maxHeight: '200px',
                  }}
                >
                  {errorInfo.componentStack}
                </pre>
              </div>
            )}

            <div>
              <p
                className="text-xs font-mono font-bold mb-2"
                style={{ color: 'var(--text-secondary)' }}
              >
                RECOVERY PATHS
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={this.handleReset}
                  className="px-3 py-1.5 rounded text-xs font-mono cursor-pointer"
                  style={{
                    backgroundColor: 'var(--accent-green)',
                    color: '#000',
                  }}
                >
                  RETRY RENDER
                </button>
                <button
                  onClick={this.handleGoHome}
                  className="px-3 py-1.5 rounded text-xs font-mono cursor-pointer"
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  RETURN TO MODES
                </button>
                <button
                  onClick={this.handleReload}
                  className="px-3 py-1.5 rounded text-xs font-mono cursor-pointer"
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  RELOAD PAGE
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
