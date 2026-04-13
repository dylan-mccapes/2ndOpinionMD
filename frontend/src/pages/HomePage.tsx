import { useNavigate, Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';

interface ModeCard {
  id: string;
  label: string;
  description: string;
  route: string;
  enabled: boolean;
  disabledReason?: string;
}

const BASE_MODES: ModeCard[] = [
  {
    id: 'ask',
    label: 'ASK',
    description:
      'Read-only clinical Q&A. Stateless. Each query is independent. SSE streaming.',
    route: '/ask',
    enabled: true,
  },
  {
    id: 'coding',
    label: 'CODING',
    description:
      'Medical coding and classification. ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm with confidence scores.',
    route: '/coding',
    enabled: true,
  },
  {
    id: 'eoh',
    label: 'EoH',
    description:
      'Single Ethos-of-Health reasoning cycle. Hypothesis set, evidence weighting, suggested next steps.',
    route: '/eoh',
    enabled: true,
  },
  {
    id: 'eohd',
    label: 'EoHD',
    description:
      'Timeline-aware EoH Detective reasoning. Temporal hypothesis evolution and inflection points.',
    route: '/eohd',
    enabled: false,
    disabledReason: 'Login to access EoHD',
  },
];

export function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, user } = useAuth();
  const { status } = useTimelineStatus();

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto mt-12 text-center">
        <p className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>Loading...</p>
      </div>
    );
  }

  if (isAuthenticated && user) {
    const portal = user.user_type === 'doctor' ? '/doctor' : '/patient';
    return <Navigate to={portal} replace />;
  }

  const hasTimeline = status?.has_timeline ?? false;

  const MODES: ModeCard[] = isAuthenticated
    ? [
        ...BASE_MODES.slice(0, 3),
        hasTimeline
          ? { id: 'eohd', label: 'EoHD', description: 'Timeline-aware EoH Detective reasoning.', route: '/eohd', enabled: true }
          : { id: 'eohd', label: 'EoHD', description: 'Upload your timeline to unlock EoHD.', route: '/timeline/upload', enabled: true, disabledReason: 'Upload timeline to enable' },
      ]
    : BASE_MODES;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-10">
        <h1
          className="text-2xl font-mono font-bold mb-2"
          style={{ color: 'var(--text-primary)' }}
        >
          2ndOpinionMD
        </h1>
        <p
          className="text-sm font-sans"
          style={{ color: 'var(--text-muted)' }}
        >
          AI-driven clinical second opinions for autoimmune disease.
        </p>
      </div>

      {!isAuthenticated && (
        <div
          className="flex items-center gap-3 mb-8 p-5 rounded-lg border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-green)' }}
        >
          <p className="text-sm font-mono flex-1" style={{ color: 'var(--text-secondary)' }}>
            Login or register to access your portal and all clinical modes.
          </p>
          <Link
            to="/auth/login"
            className="px-4 py-2 rounded text-xs font-mono font-bold no-underline"
            style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
          >
            LOGIN
          </Link>
          <Link
            to="/auth/register"
            className="px-4 py-2 rounded text-xs font-mono font-bold no-underline"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
          >
            REGISTER
          </Link>
        </div>
      )}

      <div className="mb-6">
        <h2
          className="text-lg font-mono font-bold mb-2"
          style={{ color: 'var(--text-primary)' }}
        >
          CLINICAL MODES
        </h2>
        <p
          className="text-xs font-sans"
          style={{ color: 'var(--text-muted)' }}
        >
          Four orthogonal modes. Select one. No shortcuts. No recommendations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {MODES.map((mode) => (
          <button
            key={mode.id}
            onClick={() => {
              if (!isAuthenticated) {
                navigate(`/auth/login?from=${mode.route}`);
              } else if (mode.enabled) {
                navigate(mode.route);
              }
            }}
            disabled={isAuthenticated && !mode.enabled}
            className="text-left p-6 rounded-xl border-y border-r border-l-[3px] transition-colors duration-150 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-color)',
              borderLeftColor: 'transparent',
            }}
            onMouseEnter={(e) => {
              if (mode.enabled || !isAuthenticated) {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.borderLeftColor = 'var(--accent-green)';
                e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.borderLeftColor = 'transparent';
              e.currentTarget.style.backgroundColor = 'var(--bg-secondary)';
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span
                className="text-lg font-mono font-bold tracking-widest uppercase"
                style={{
                  color: mode.enabled || !isAuthenticated
                    ? 'var(--accent-green)'
                    : 'var(--text-muted)',
                }}
              >
                {mode.label}
              </span>
              {isAuthenticated && !mode.enabled && (
                <span
                  className="text-xs font-mono px-2 py-0.5 rounded"
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--accent-yellow)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  DISABLED
                </span>
              )}
            </div>
            <p
              className="text-sm font-sans leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              {mode.description}
            </p>
            {mode.disabledReason && (
              <p
                className="text-xs mt-2 font-mono"
                style={{ color: 'var(--accent-yellow)' }}
              >
                {mode.disabledReason}
              </p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
