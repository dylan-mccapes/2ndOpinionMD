import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';

export function TimelineStatusIndicator() {
  const { isAuthenticated, user } = useAuth();
  const { status, loading } = useTimelineStatus();
  const navigate = useNavigate();

  if (!isAuthenticated || loading) return null;

  const isSystemUser = user?.subscription_tier && user.subscription_tier !== 'free';

  if (!isSystemUser) return null;

  if (status?.has_timeline) {
    return (
      <span
        className="text-xs font-mono px-2 py-0.5 rounded"
        style={{ color: 'var(--accent-green)', backgroundColor: 'var(--bg-tertiary)' }}
      >
        TIMELINE READY ({status.event_count})
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => navigate('/timeline/upload')}
      className="text-xs font-mono px-2 py-0.5 rounded cursor-pointer"
      style={{
        color: 'var(--accent-yellow)',
        backgroundColor: 'var(--bg-tertiary)',
        border: 'none',
      }}
    >
      UPLOAD TIMELINE
    </button>
  );
}
