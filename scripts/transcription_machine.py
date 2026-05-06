#!/usr/bin/env python3
"""
🎤 Transcription Machine 🎤

Audio transcription using OpenAI Whisper.

Purpose:
    - Transcribe audio files to text
    - Support multiple audio formats (m4a, mp3, wav, caf, etc.)
    - Generate clean, readable transcripts
    - Optionally include timestamps

Philosophy:
    "Listen first. Transcribe honestly."
    - Uses Whisper (state-of-art speech recognition)
    - No editing or correction of transcribed content
    - Preserves speaker intent as heard
    - Provides timestamps for navigation

Technical:
    - Uses Whisper large-v3 model (best quality)
    - Runs on CPU (no GPU required, but slower)
    - First run downloads model (~3GB)
    - Supports many audio formats via ffmpeg

Usage:
    # Basic transcription
    python3 transcription_machine.py <audio_file.m4a>
    
    # With timestamps
    python3 transcription_machine.py <audio_file.m4a> --timestamps
    
    # Save to file
    python3 transcription_machine.py <audio_file.m4a> --output transcript.txt
    
    # Different model size (faster but less accurate)
    python3 transcription_machine.py <audio_file.m4a> --model base
"""

import sys
import argparse
from pathlib import Path
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

try:
    import whisper
except ImportError:
    print("❌ Error: whisper not installed")
    print("\nInstall with:")
    print("  pip install openai-whisper")
    print("\nAlso requires ffmpeg:")
    print("  brew install ffmpeg  (macOS)")
    print("  apt install ffmpeg   (Linux)")
    sys.exit(1)

# ========================================
# Core Functions
# ========================================

def transcribe_audio(audio_path: str, model_size: str = "base", include_timestamps: bool = False, verbose: bool = True) -> dict:
    """
    Transcribe audio file using Whisper.
    
    Args:
        audio_path: Path to audio file
        model_size: Whisper model size (tiny, base, small, medium, large)
        include_timestamps: Include word-level timestamps
        verbose: Print progress messages
        
    Returns:
        Dictionary with 'text' and optionally 'segments' (if timestamps requested)
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        print(f"❌ Error: File not found: {audio_path}")
        sys.exit(1)
    
    if verbose:
        print(f"🎤 Loading Whisper model ({model_size})...")
    
    # Load model
    model = whisper.load_model(model_size)
    
    if verbose:
        print(f"🎵 Transcribing: {audio_path.name}")
        print(f"   Duration: {get_audio_duration(str(audio_path)):.1f}s")
        print()
    
    # Transcribe
    result = model.transcribe(str(audio_path), verbose=verbose)
    
    return result


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds."""
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=None, duration=1)
        # Load just 1 second to get sr, then calculate total duration
        import soundfile as sf
        info = sf.info(audio_path)
        return info.duration
    except:
        return 0.0


def format_timestamp(seconds: float) -> str:
    """Format timestamp as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def print_transcript(result: dict, include_timestamps: bool = False):
    """Print transcript to console."""
    print("=" * 80)
    print("📝 TRANSCRIPT")
    print("=" * 80)
    print()
    
    if include_timestamps and 'segments' in result:
        for segment in result['segments']:
            start = format_timestamp(segment['start'])
            end = format_timestamp(segment['end'])
            text = segment['text'].strip()
            print(f"[{start} - {end}] {text}")
            print()
    else:
        print(result['text'])
    
    print()
    print("=" * 80)


def save_transcript(result: dict, output_path: Path, include_timestamps: bool = False):
    """Save transcript to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("TRANSCRIPT\n")
        f.write("=" * 80 + "\n\n")
        
        if include_timestamps and 'segments' in result:
            for segment in result['segments']:
                start = format_timestamp(segment['start'])
                end = format_timestamp(segment['end'])
                text = segment['text'].strip()
                f.write(f"[{start} - {end}] {text}\n\n")
        else:
            f.write(result['text'] + "\n")
    
    print(f"✅ Transcript saved to: {output_path}")


# ========================================
# CLI
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description='Transcription Machine: Audio transcription using Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 transcription_machine.py song.m4a
  python3 transcription_machine.py recording.caf --timestamps
  python3 transcription_machine.py meeting.mp3 --output transcript.txt
  python3 transcription_machine.py audio.wav --model large
        """
    )
    
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--model', default='base', 
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size (default: base)')
    parser.add_argument('--timestamps', action='store_true',
                       help='Include word-level timestamps')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file path (optional)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    
    args = parser.parse_args()
    
    # Run transcription
    result = transcribe_audio(
        args.audio_file,
        model_size=args.model,
        include_timestamps=args.timestamps,
        verbose=not args.quiet
    )
    
    # Print transcript
    if not args.quiet:
        print_transcript(result, include_timestamps=args.timestamps)
    
    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        save_transcript(result, output_path, include_timestamps=args.timestamps)
    
    # Return for scripting
    return result


if __name__ == "__main__":
    main()

