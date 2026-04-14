import { useState, useRef, useCallback, useEffect } from 'react';
import { Card, DS, InlineMessage } from '../lib/ui';

export type AudioState = 'idle' | 'recording' | 'paused' | 'stopped';

interface AudioCaptureProps {
  onChunk: (blob: Blob, index: number) => void;
  onStateChange?: (state: AudioState) => void;
  disabled?: boolean;
}

const CHUNK_INTERVAL_MS = 15_000;

export function AudioCapture({ onChunk, onStateChange, disabled }: AudioCaptureProps) {
  const [state, setState] = useState<AudioState>('idle');
  const [consented, setConsented] = useState(false);
  const [duration, setDuration] = useState(0);
  const [micError, setMicError] = useState('');
  const [chunksSent, setChunksSent] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunkIndexRef = useRef(0);
  const durationRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const updateState = useCallback(
    (s: AudioState) => {
      setState(s);
      onStateChange?.(s);
    },
    [onStateChange],
  );

  const stopAllTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setMicError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunkIndexRef.current = 0;
      setChunksSent(0);

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          onChunk(e.data, chunkIndexRef.current);
          chunkIndexRef.current += 1;
          setChunksSent(chunkIndexRef.current);
        }
      };

      recorder.onerror = () => {
        setMicError('Recording error occurred');
        updateState('stopped');
      };

      recorder.start(CHUNK_INTERVAL_MS);
      updateState('recording');
      setDuration(0);

      durationRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Microphone access denied';
      setMicError(msg);
    }
  }, [onChunk, updateState]);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      updateState('paused');
      if (durationRef.current) clearInterval(durationRef.current);
    }
  }, [updateState]);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      updateState('recording');
      durationRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    }
  }, [updateState]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    stopAllTracks();
    if (durationRef.current) clearInterval(durationRef.current);
    updateState('stopped');
  }, [stopAllTracks, updateState]);

  const reset = useCallback(() => {
    stopRecording();
    setDuration(0);
    setChunksSent(0);
    chunkIndexRef.current = 0;
    updateState('idle');
  }, [stopRecording, updateState]);

  useEffect(() => {
    return () => {
      stopAllTracks();
      if (durationRef.current) clearInterval(durationRef.current);
    };
  }, [stopAllTracks]);

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  if (!consented) {
    return (
      <Card style={{ padding: DS.pad.inner }}>
        <p className="text-sm font-mono" style={{ color: 'var(--text-primary)', marginBottom: DS.mb.md }}>
          Patient consent is required before recording. By proceeding, you confirm that the patient
          has been informed and has consented to audio recording of this encounter.
        </p>
        <button
          type="button"
          onClick={() => setConsented(true)}
          disabled={disabled}
          className="px-4 py-2 rounded text-sm font-mono font-bold"
          style={{
            backgroundColor: 'var(--accent-red)',
            color: '#fff',
            opacity: disabled ? 0.5 : 1,
          }}
        >
          PATIENT HAS CONSENTED — ENABLE RECORDING
        </button>
      </Card>
    );
  }

  return (
    <Card style={{ padding: DS.pad.inner }}>
      <div className="flex items-center" style={{ gap: DS.gap.lg, marginBottom: DS.mb.md }}>
        {state === 'recording' && (
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ backgroundColor: '#ef4444', boxShadow: '0 0 8px #ef4444' }}
          />
        )}
        <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
          {state === 'idle' && 'READY'}
          {state === 'recording' && 'RECORDING'}
          {state === 'paused' && 'PAUSED'}
          {state === 'stopped' && 'STOPPED'}
        </span>
        {(state === 'recording' || state === 'paused') && (
          <span className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
            {formatDuration(duration)}
          </span>
        )}
        {state === 'recording' || state === 'paused' ? (
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            Chunks sent: {chunksSent}
          </span>
        ) : null}
      </div>

      <div className="flex items-center" style={{ gap: DS.gap.md }}>
        {state === 'idle' && (
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled}
            className="px-4 py-2 rounded text-sm font-mono font-bold"
            style={{ backgroundColor: '#ef4444', color: '#fff', opacity: disabled ? 0.5 : 1 }}
          >
            REC
          </button>
        )}

        {state === 'recording' && (
          <>
            <button
              type="button"
              onClick={pauseRecording}
              className="px-4 py-2 rounded text-sm font-mono font-bold"
              style={{ backgroundColor: 'var(--accent-yellow)', color: '#000' }}
            >
              PAUSE
            </button>
            <button
              type="button"
              onClick={stopRecording}
              className="px-4 py-2 rounded text-sm font-mono font-bold"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
            >
              STOP
            </button>
          </>
        )}

        {state === 'paused' && (
          <>
            <button
              type="button"
              onClick={resumeRecording}
              className="px-4 py-2 rounded text-sm font-mono font-bold"
              style={{ backgroundColor: '#ef4444', color: '#fff' }}
            >
              RESUME
            </button>
            <button
              type="button"
              onClick={stopRecording}
              className="px-4 py-2 rounded text-sm font-mono font-bold"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
            >
              STOP
            </button>
          </>
        )}

        {state === 'stopped' && (
          <button
            type="button"
            onClick={reset}
            className="px-4 py-2 rounded text-sm font-mono font-bold"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
          >
            NEW RECORDING
          </button>
        )}
      </div>

      {micError && (
        <InlineMessage variant="error" style={{ marginTop: DS.mb.sm }}>{micError}</InlineMessage>
      )}
    </Card>
  );
}
