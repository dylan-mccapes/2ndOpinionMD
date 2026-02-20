import { useState } from 'react';
import { Link } from 'react-router-dom';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        FORGOT PASSWORD
      </h1>

      <div
        className="p-6 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            EMAIL
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-2 rounded border text-sm font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        <button
          disabled={!email.trim()}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-blue)',
            color: '#fff',
          }}
        >
          SEND RESET LINK
        </button>

        <div className="mt-4">
          <Link
            to="/auth/login"
            className="text-xs font-mono no-underline"
            style={{ color: 'var(--text-muted)' }}
          >
            BACK TO LOGIN
          </Link>
        </div>
      </div>
    </div>
  );
}
