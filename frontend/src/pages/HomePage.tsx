import { useNavigate } from 'react-router-dom';
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
];

export function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const { status } = useTimelineStatus();

  const isSystemUser = isAuthenticated && user?.subscription_tier && user.subscription_tier !== 'free';
  const hasTimeline = status?.has_timeline ?? false;

  const eohdCard: ModeCard = isSystemUser && hasTimeline
    ? {
        id: 'eohd',
        label: 'EoHD',
        description: 'Timeline-aware EoH Detective reasoning. Temporal hypothesis evolution and inflection points.',
        route: '/eohd',
        enabled: true,
      }
    : isSystemUser
    ? {
        id: 'eohd',
        label: 'EoHD',
        description: 'Timeline-aware EoH Detective reasoning. Upload your timeline to unlock.',
        route: '/timeline/upload',
        enabled: true,
        disabledReason: 'Upload timeline to enable',
      }
    : {
        id: 'eohd',
        label: 'EoHD',
        description: 'Timeline-aware EoH Detective reasoning. Temporal hypothesis evolution and inflection points.',
        route: '/eohd',
        enabled: false,
        disabledReason: 'Requires system user subscription',
      };

  const MODES = [...BASE_MODES, eohdCard];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1
          className="text-2xl font-mono font-bold mb-2"
          style={{ color: 'var(--text-primary)' }}
        >
          MODE SELECTOR
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Four orthogonal clinical modes. Select one. No shortcuts. No
          recommendations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {MODES.map((mode) => (
          <button
            key={mode.id}
            onClick={() => mode.enabled && navigate(mode.route)}
            disabled={!mode.enabled}
            className="text-left p-6 rounded border transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-color)',
            }}
            onMouseEnter={(e) => {
              if (mode.enabled) {
                e.currentTarget.style.borderColor = 'var(--accent-green)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span
                className="text-lg font-mono font-bold tracking-wider"
                style={{
                  color: mode.enabled
                    ? 'var(--accent-green)'
                    : 'var(--text-muted)',
                }}
              >
                {mode.label}
              </span>
              {!mode.enabled && (
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
              className="text-sm"
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
