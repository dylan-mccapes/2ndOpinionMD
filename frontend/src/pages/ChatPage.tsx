import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';
import { useChatGraph, type ChatMessageData } from '../hooks/useChatGraph';

function DecayIndicator({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score > 0.7 ? 'var(--accent-green)' :
    score > 0.3 ? 'var(--accent-yellow)' :
    'var(--accent-red, #ef4444)';
  return (
    <span
      className="inline-block text-[9px] font-mono px-1 rounded"
      style={{ color, border: `1px solid ${color}`, opacity: 0.7 }}
      title={`Decay score: ${pct}% — higher = more retained`}
    >
      {pct}%
    </span>
  );
}

function AnchorBadge({ eventIds }: { eventIds: string[] }) {
  if (!eventIds.length) return null;
  return (
    <span
      className="inline-block text-[9px] font-mono px-1 rounded ml-1"
      style={{ color: 'var(--accent-blue, #3b82f6)', border: '1px solid var(--accent-blue, #3b82f6)', opacity: 0.7 }}
      title={`Anchored to: ${eventIds.join(', ')}`}
    >
      ⚓ {eventIds.length}
    </span>
  );
}

function ChatBubble({
  msg,
  isOwnMessage,
  onAnchor,
}: {
  msg: ChatMessageData;
  isOwnMessage: boolean;
  onAnchor?: (messageId: string) => void;
}) {
  const roleLabel: Record<string, string> = {
    patient: 'You',
    doctor: 'Doctor',
    agent: '2OPMD',
    system: 'System',
  };

  const roleColor: Record<string, string> = {
    patient: 'var(--accent-green)',
    doctor: 'var(--accent-blue, #3b82f6)',
    agent: 'var(--accent-yellow)',
    system: 'var(--text-muted)',
  };

  const bgClass = isOwnMessage ? 'ml-8' : 'mr-8';
  const date = new Date(msg.created_at).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <div className={`${bgClass} mb-3`}>
      <div
        className="rounded-lg p-3 text-sm"
        style={{
          backgroundColor: isOwnMessage ? 'var(--bg-tertiary, #1e293b)' : 'var(--bg-secondary, #0f172a)',
          border: '1px solid var(--border-primary, #334155)',
        }}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-xs font-bold" style={{ color: roleColor[msg.role] }}>
            {roleLabel[msg.role] || msg.role}
          </span>
          <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{date}</span>
          <DecayIndicator score={msg.decay_score} />
          <AnchorBadge eventIds={msg.anchored_event_ids} />
          {onAnchor && (
            <button
              onClick={() => onAnchor(msg.message_id)}
              className="text-[10px] font-mono opacity-50 hover:opacity-100 transition-opacity"
              style={{ color: 'var(--accent-blue, #3b82f6)' }}
              title="Anchor to PTV event"
            >
              +⚓
            </button>
          )}
        </div>
        <p className="font-mono text-xs leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
          {msg.content}
        </p>
      </div>
    </div>
  );
}

function BudgetBar({ stats }: { stats: { total_chars: number; max_chars: number; anchored_count: number; avg_decay_score: number } }) {
  const pct = Math.round((stats.total_chars / stats.max_chars) * 100);
  const barColor =
    pct > 80 ? 'var(--accent-red, #ef4444)' :
    pct > 50 ? 'var(--accent-yellow)' :
    'var(--accent-green)';

  return (
    <div className="px-4 py-2" style={{ borderBottom: '1px solid var(--border-primary, #334155)' }}>
      <div className="flex items-center justify-between text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
        <span>Budget: {(stats.total_chars / 1000).toFixed(1)}k / {(stats.max_chars / 1000).toFixed(0)}k chars</span>
        <span>⚓ {stats.anchored_count} anchored</span>
        <span>Avg decay: {Math.round(stats.avg_decay_score * 100)}%</span>
      </div>
      <div className="mt-1 h-1 rounded-full" style={{ backgroundColor: 'var(--bg-tertiary, #1e293b)' }}>
        <div
          className="h-1 rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}

export function ChatPage() {
  const { token, isAuthenticated, user } = useAuth();
  const { status } = useTimelineStatus();
  const patientId = status?.timeline_id ?? user?.id ?? null;
  const role = user?.user_type === 'doctor' ? 'doctor' : 'patient';

  const { messages, stats, loading, sending, error, sendMessage, anchorToEvent, refresh } = useChatGraph(patientId);

  const [input, setInput] = useState('');
  const [anchorEventId, setAnchorEventId] = useState('');
  const [showAnchorInput, setShowAnchorInput] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
          Please log in to access chat.
        </p>
      </div>
    );
  }

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    const content = input.trim();
    if (!content) return;

    const anchors = anchorEventId.trim() ? [anchorEventId.trim()] : undefined;
    setInput('');
    setAnchorEventId('');
    setShowAnchorInput(false);

    await sendMessage(content, role as 'patient' | 'doctor', anchors);
  };

  const handleAnchorMessage = async (messageId: string) => {
    const eventId = prompt('Enter PTV event ID to anchor to:');
    if (eventId) {
      await anchorToEvent(messageId, eventId);
    }
  };

  return (
    <div className="max-w-3xl mx-auto flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border-primary, #334155)' }}>
        <h1 className="text-lg font-mono font-bold" style={{ color: 'var(--accent-yellow)' }}>
          Chat
        </h1>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {role === 'doctor' ? 'Clinical conversation — messages anchor to the patient graph' : 'Your conversation with 2OPMD — everything here helps your care team'}
        </p>
      </div>

      {/* Budget bar */}
      {stats && <BudgetBar stats={stats} />}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
        {loading && (
          <p className="text-xs font-mono text-center" style={{ color: 'var(--text-muted)' }}>Loading...</p>
        )}

        {!loading && messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-sm font-mono mb-2" style={{ color: 'var(--text-muted)' }}>
              No messages yet.
            </p>
            <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              {role === 'patient'
                ? 'Tell us about your day. How are you feeling? Your words help the graph understand you.'
                : 'Clinical observations anchored here persist in the patient graph.'}
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatBubble
            key={msg.message_id}
            msg={msg}
            isOwnMessage={msg.role === role}
            onAnchor={handleAnchorMessage}
          />
        ))}

        {sending && (
          <div className="ml-8 mb-3">
            <div
              className="rounded-lg p-3 text-sm animate-pulse"
              style={{
                backgroundColor: 'var(--bg-tertiary, #1e293b)',
                border: '1px solid var(--border-primary, #334155)',
              }}
            >
              <span className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                Sending...
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid var(--border-primary, #334155)', backgroundColor: 'var(--bg-primary)' }}>
        {error && (
          <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent-red, #ef4444)' }}>{error}</p>
        )}

        {showAnchorInput && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-mono" style={{ color: 'var(--accent-blue, #3b82f6)' }}>⚓</span>
            <input
              type="text"
              value={anchorEventId}
              onChange={(e) => setAnchorEventId(e.target.value)}
              placeholder="PTV event ID to anchor to..."
              className="flex-1 text-xs font-mono px-2 py-1 rounded"
              style={{
                backgroundColor: 'var(--bg-secondary, #0f172a)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-primary, #334155)',
              }}
            />
            <button
              onClick={() => { setShowAnchorInput(false); setAnchorEventId(''); }}
              className="text-[10px] font-mono"
              style={{ color: 'var(--text-muted)' }}
            >
              ✕
            </button>
          </div>
        )}

        <form onSubmit={handleSend} className="flex items-end gap-2">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e);
                }
              }}
              placeholder={role === 'patient'
                ? "How are you feeling today? What's on your mind?"
                : "Clinical observation or question..."}
              rows={2}
              className="w-full text-sm font-mono px-3 py-2 rounded-lg resize-none"
              style={{
                backgroundColor: 'var(--bg-secondary, #0f172a)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-primary, #334155)',
              }}
              disabled={sending}
            />
          </div>
          <div className="flex flex-col gap-1">
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="px-4 py-2 rounded-lg text-xs font-mono font-bold transition-opacity disabled:opacity-30"
              style={{
                backgroundColor: 'var(--accent-yellow)',
                color: 'var(--bg-primary, #000)',
              }}
            >
              Send
            </button>
            <button
              type="button"
              onClick={() => setShowAnchorInput(!showAnchorInput)}
              className="px-2 py-1 rounded text-[10px] font-mono transition-opacity"
              style={{
                color: 'var(--accent-blue, #3b82f6)',
                border: '1px solid var(--accent-blue, #3b82f6)',
                opacity: showAnchorInput ? 1 : 0.5,
              }}
              title="Anchor this message to a PTV event"
            >
              ⚓
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
