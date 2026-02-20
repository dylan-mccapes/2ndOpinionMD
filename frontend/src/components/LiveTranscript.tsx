import { useEffect, useRef } from 'react';

export interface TranscriptSegment {
  text: string;
  chunkIndex: number;
  timestamp: string;
}

interface LiveTranscriptProps {
  segments: TranscriptSegment[];
  isRecording: boolean;
}

export function LiveTranscript({ segments, isRecording }: LiveTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [segments]);

  if (segments.length === 0 && !isRecording) {
    return null;
  }

  return (
    <div
      className="rounded border"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: 'var(--border-color)' }}>
        <span className="text-xs font-mono font-bold" style={{ color: 'var(--accent-blue)' }}>
          TRANSCRIPT
        </span>
        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {segments.length} segment{segments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="p-4 overflow-auto"
        style={{ maxHeight: '300px' }}
      >
        {segments.length === 0 && isRecording && (
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            Listening... transcript will appear here.
          </p>
        )}

        {segments.map((seg, i) => (
          <div key={`seg-${seg.chunkIndex}-${i}`} className="mb-2">
            <span className="text-xs font-mono mr-2" style={{ color: 'var(--text-muted)' }}>
              [{String(seg.chunkIndex).padStart(2, '0')}]
            </span>
            <span className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
              {seg.text}
            </span>
          </div>
        ))}

        {isRecording && segments.length > 0 && (
          <div className="mt-1">
            <span
              className="inline-block w-2 h-4 align-middle"
              style={{ backgroundColor: 'var(--accent-green)' }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
