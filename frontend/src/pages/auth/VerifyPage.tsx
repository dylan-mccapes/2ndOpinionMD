import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

type VerifyState = 'loading' | 'success' | 'error' | 'no-token';

export function VerifyPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [state, setState] = useState<VerifyState>(token ? 'loading' : 'no-token');
  const [errorMessage, setErrorMessage] = useState('');
  const [ptvWarning, setPtvWarning] = useState('');

  useEffect(() => {
    if (!token) return;

    const verify = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/verify-email?token=${encodeURIComponent(token)}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: res.statusText }));
          const detail = data.detail;
          setErrorMessage(typeof detail === 'string' ? detail : 'Verification failed');
          setState('error');
          return;
        }
        const ok = await res.json().catch(() => ({}));
        if (ok && ok.ptv_initialized === false) {
          setPtvWarning(
            'Email verified, but the clinical graph record could not be created yet. Try logging in — the system will retry automatically.',
          );
        } else {
          setPtvWarning('');
        }
        setState('success');
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : 'Network error');
        setState('error');
      }
    };

    verify();
  }, [token]);

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        EMAIL VERIFICATION
      </h1>

      <div
        className="p-6 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: state === 'success' ? 'var(--accent-green)' : state === 'error' ? 'var(--accent-red)' : 'var(--border-color)',
        }}
      >
        {state === 'loading' && (
          <p className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
            Verifying email...
          </p>
        )}

        {state === 'no-token' && (
          <div>
            <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-red)' }}>
              No verification token provided.
            </p>
            <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              Check your email for the verification link.
            </p>
          </div>
        )}

        {state === 'success' && (
          <div>
            <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-green)' }}>
              Email verified successfully.
            </p>
            {ptvWarning ? (
              <p className="text-xs font-mono mb-3" style={{ color: 'var(--text-secondary)' }}>
                {ptvWarning}
              </p>
            ) : null}
            <Link
              to="/auth/login"
              className="px-3 py-1.5 rounded text-xs font-mono no-underline"
              style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
            >
              GO TO LOGIN
            </Link>
          </div>
        )}

        {state === 'error' && (
          <div>
            <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-red)' }}>
              {errorMessage}
            </p>
            <Link
              to="/auth/login"
              className="text-xs font-mono no-underline"
              style={{ color: 'var(--accent-blue)' }}
            >
              BACK TO LOGIN
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
