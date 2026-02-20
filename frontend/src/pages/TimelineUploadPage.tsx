import { useState, useRef, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authHeaders, ApiError } from '../lib/api';

type UploadState = 'idle' | 'uploading' | 'extracting' | 'ingesting' | 'done' | 'error';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

interface ImportResponse {
  timeline_id: string;
  patient_id: string;
  event_count: number;
  status: string;
  message: string;
}

export function TimelineUploadPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [error, setError] = useState('');
  const [result, setResult] = useState<ImportResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    if (selected && selected.type !== 'application/pdf') {
      setError('Only PDF files are accepted.');
      setFile(null);
      return;
    }
    if (selected && selected.size > 10 * 1024 * 1024) {
      setError('File exceeds 10MB limit.');
      setFile(null);
      return;
    }
    setError('');
    setFile(selected);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !file) return;

    setError('');
    setResult(null);
    setUploadState('uploading');

    const formData = new FormData();
    formData.append('file', file);
    if (showPassword && password) {
      formData.append('password', password);
    }

    try {
      setUploadState('extracting');

      const res = await fetch(`${API_BASE}/api/timeline/import-pdf`, {
        method: 'POST',
        headers: authHeaders(token),
        body: formData,
      });

      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new ApiError(res.status, body || res.statusText);
      }

      setUploadState('ingesting');
      const data: ImportResponse = await res.json();
      setResult(data);
      setUploadState('done');
    } catch (err) {
      setUploadState('error');
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setError('Access denied. Timeline upload requires a system user subscription.');
        } else if (err.status === 413) {
          setError('File too large. Maximum size is 10MB.');
        } else if (err.status === 400) {
          setError(`Invalid request: ${err.body}`);
        } else {
          setError(`API ${err.status}: ${err.body}`);
        }
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed');
      }
    }
  };

  const stateLabel = (state: UploadState): string => {
    switch (state) {
      case 'idle': return 'READY';
      case 'uploading': return 'UPLOADING...';
      case 'extracting': return 'EXTRACTING TEXT...';
      case 'ingesting': return 'BUILDING TIMELINE...';
      case 'done': return 'COMPLETE';
      case 'error': return 'FAILED';
    }
  };

  const stateColor = (state: UploadState): string => {
    switch (state) {
      case 'idle': return 'var(--text-muted)';
      case 'uploading':
      case 'extracting':
      case 'ingesting': return 'var(--accent-yellow)';
      case 'done': return 'var(--accent-green)';
      case 'error': return 'var(--accent-red)';
    }
  };

  const isProcessing = uploadState === 'uploading' || uploadState === 'extracting' || uploadState === 'ingesting';

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          TIMELINE UPLOAD
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Upload your patient timeline PDF to enable EoHD investigations.
        </p>
      </div>

      <div
        className="p-4 rounded border mb-4"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
            STATUS:
          </span>
          <span className="text-xs font-mono font-bold" style={{ color: stateColor(uploadState) }}>
            {stateLabel(uploadState)}
          </span>
        </div>

        {uploadState === 'done' && result ? (
          <div className="space-y-3">
            <div
              className="p-3 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)' }}
            >
              <p className="text-sm font-mono" style={{ color: 'var(--accent-green)' }}>
                Timeline ingested successfully.
              </p>
              <div className="mt-2 space-y-1">
                <p className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                  TIMELINE ID: <span style={{ color: 'var(--text-primary)' }}>{result.timeline_id}</span>
                </p>
                <p className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                  EVENTS: <span style={{ color: 'var(--text-primary)' }}>{result.event_count}</span>
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/eohd')}
              className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer"
              style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
            >
              PROCEED TO EoHD
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div
                className="p-3 rounded text-sm font-mono"
                style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
              >
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-mono font-bold mb-1" style={{ color: 'var(--text-secondary)' }}>
                PATIENT TIMELINE PDF
              </label>
              <div
                className="p-4 rounded border text-center cursor-pointer"
                style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', borderStyle: 'dashed' }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={isProcessing}
                />
                {file ? (
                  <div>
                    <p className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                      {file.name}
                    </p>
                    <p className="text-xs font-mono mt-1" style={{ color: 'var(--text-muted)' }}>
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    Click to select PDF file (max 10MB)
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showPassword}
                  onChange={(e) => setShowPassword(e.target.checked)}
                  disabled={isProcessing}
                />
                <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                  PDF IS ENCRYPTED
                </span>
              </label>
              {showPassword && (
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full mt-2 p-2 rounded border text-sm font-mono"
                  style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                  placeholder="PDF password"
                  disabled={isProcessing}
                />
              )}
            </div>

            <button
              type="submit"
              disabled={!file || isProcessing}
              className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
            >
              {isProcessing ? stateLabel(uploadState) : 'UPLOAD & INGEST'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
