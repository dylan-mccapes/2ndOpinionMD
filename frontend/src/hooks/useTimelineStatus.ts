import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface TimelineStatus {
  has_timeline: boolean;
  timeline_id: string | null;
  event_count: number;
  last_updated: string | null;
}

interface UseTimelineStatusReturn {
  status: TimelineStatus | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
}

const DEFAULT_STATUS: TimelineStatus = {
  has_timeline: false,
  timeline_id: null,
  event_count: 0,
  last_updated: null,
};

export function useTimelineStatus(): UseTimelineStatusReturn {
  const { token, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<TimelineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    if (!token || !isAuthenticated) {
      setStatus(null);
      return;
    }
    setLoading(true);
    setError('');

    try {
      const data = await apiFetch<TimelineStatus>('/api/timeline/status', {
        headers: authHeaders(token),
      });
      setStatus(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setStatus(DEFAULT_STATUS);
      } else if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
        setStatus(DEFAULT_STATUS);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to check timeline status');
        setStatus(DEFAULT_STATUS);
      }
    } finally {
      setLoading(false);
    }
  }, [token, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      refresh();
    } else {
      setStatus(null);
    }
  }, [isAuthenticated, refresh]);

  return { status, loading, error, refresh };
}
