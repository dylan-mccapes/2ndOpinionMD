import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

export interface ChatMessageData {
  message_id: string;
  patient_id: string;
  role: 'patient' | 'doctor' | 'system' | 'agent';
  content: string;
  created_at: string;
  last_referenced: string;
  decay_score: number;
  retention_reason: string;
  anchored_event_ids: string[];
  reference_edges: Record<string, string[]>;
  author_id: string | null;
}

interface ChatHistoryResponse {
  patient_id: string;
  messages: ChatMessageData[];
  total_active: number;
  total_chars: number;
  budget_remaining: number;
}

interface SendResponse {
  message_id: string;
  decay_score: number;
  evicted_count: number;
}

interface ChatStats {
  patient_id: string;
  total_messages: number;
  active_messages: number;
  evicted_messages: number;
  total_chars: number;
  max_chars: number;
  anchored_count: number;
  avg_decay_score: number;
}

export function useChatGraph(patientId: string | null) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [stats, setStats] = useState<ChatStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const headers = token ? { ...authHeaders(token), 'Content-Type': 'application/json' } : {};

  const loadHistory = useCallback(async () => {
    if (!patientId || !token) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch<ChatHistoryResponse>(
        `/api/chat/history/${patientId}?limit=200`,
        { headers },
      );
      setMessages(data.messages);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setMessages([]);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load chat');
      }
    } finally {
      setLoading(false);
    }
  }, [patientId, token]);

  const loadStats = useCallback(async () => {
    if (!patientId || !token) return;
    try {
      const data = await apiFetch<ChatStats>(
        `/api/chat/stats/${patientId}`,
        { headers },
      );
      setStats(data);
    } catch {
      // Stats are advisory, don't block on failure
    }
  }, [patientId, token]);

  const sendMessage = useCallback(async (
    content: string,
    role: 'patient' | 'doctor',
    anchoredEventIds?: string[],
    referenceEdges?: Record<string, string[]>,
  ): Promise<SendResponse | null> => {
    if (!patientId || !token) return null;
    setSending(true);
    setError('');
    try {
      const resp = await apiFetch<SendResponse>('/api/chat/send', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          patient_id: patientId,
          role,
          content,
          anchored_event_ids: anchoredEventIds || [],
          reference_edges: referenceEdges || {},
        }),
      });
      await loadHistory();
      await loadStats();
      return resp;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      return null;
    } finally {
      setSending(false);
    }
  }, [patientId, token, loadHistory, loadStats]);

  const anchorToEvent = useCallback(async (messageId: string, eventId: string) => {
    if (!token) return;
    try {
      await apiFetch('/api/chat/anchor', {
        method: 'POST',
        headers,
        body: JSON.stringify({ message_id: messageId, event_id: eventId }),
      });
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to anchor message');
    }
  }, [token, loadHistory]);

  useEffect(() => {
    if (patientId) {
      loadHistory();
      loadStats();
    }
  }, [patientId, loadHistory, loadStats]);

  return {
    messages,
    stats,
    loading,
    sending,
    error,
    sendMessage,
    anchorToEvent,
    refresh: loadHistory,
  };
}
