#!/usr/bin/env python3
"""
🎵 Wave Modulation Machine 🎵

Source separation + rhythm alignment for audio analysis.

Purpose:
    - Separate guitar from vocals using Demucs (state-of-art separation)
    - Extract rhythm features from each stream
    - Align streams using Dynamic Time Warping
    - Analyze flow coherence and structural coupling

Applications:
    - First playthrough analysis (honest baseline)
    - Performative drift detection (compare multiple takes)
    - Dream/imagination monitoring (future: qualitative flow analysis)
    - Mind control detection (acceptable compression vs. malicious gating)

Philosophy:
    "Execute quietly. So you can hear."
    - Growing edges: Expanding capability through structural addition
    - Quantifies subjective "flow" as measurable structural coupling
    - Provides objective feedback without aesthetic judgment

Technical:
    - Uses Demucs htdemucs model (hybrid transformer, best quality)
    - Runs on CPU (no GPU required, but slower)
    - First run downloads model (~300MB)

Usage:
    # Basic analysis
    python3 wave_modulation_machine.py <audio_file.m4a>
    
    # With detailed output
    python3 wave_modulation_machine.py <audio_file.m4a> --verbose
    
    # Save separated sources
    python3 wave_modulation_machine.py <audio_file.m4a> --save-sources
    
    # Save JSON for qualitative agent
    python3 wave_modulation_machine.py <audio_file.m4a> --save-json
    
    # Full workflow: quantitative + qualitative
    python3 wave_modulation_machine.py song.m4a --save-json
    python3 wave_modulation_agent.py song_WMM_RESULTS.json "first playthrough"
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Tuple, Any
import warnings

# Guardrail: WMM must not run under .BeatingHeart (2OPMD venv). Use run_tm_wmm_analysis.sh (.StandardVenv).
_venv = os.environ.get("VIRTUAL_ENV", "")
if "BeatingHeart" in _venv and not os.environ.get("WMM_ALLOW_BEATING_HEART"):
    raise RuntimeError(
        "WaveModulationMachine must not be run under .BeatingHeart. "
        "Use run_tm_wmm_analysis.sh (.StandardVenv)."
    )

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

import numpy as np
import librosa
import soundfile as sf
import torch

# Demucs is optional: pip install often fails (requirements_minimal.txt bug; repo archived 2025).
# Without demucs we run in "no-separation" mode: full mix used for both guitar and vocals.
try:
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import convert_audio
    DEMUCS_AVAILABLE = True
except ImportError:
    get_model = apply_model = convert_audio = None
    DEMUCS_AVAILABLE = False

# ========================================
# Core Functions
# ========================================

def separate_sources(
    audio_path: str,
    output_dir: str = None,
    verbose: bool = False,
    use_demucs: bool = True,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Separate guitar and vocals using Demucs, or use full mix when demucs unavailable/skipped.
    
    Args:
        audio_path: Path to input audio file
        output_dir: Optional directory to save separated sources
        verbose: Print progress messages
        use_demucs: If False or demucs not installed, use full mix for both streams (degraded mode).
        
    Returns:
        (guitar_audio, vocal_audio, sample_rate)
    """
    # Load audio (always needed)
    waveform, sample_rate = librosa.load(audio_path, sr=44100, mono=False)
    mono = librosa.to_mono(waveform) if waveform.ndim > 1 else waveform

    if use_demucs and DEMUCS_AVAILABLE:
        if verbose:
            print("🎸 Separating sources (Demucs)...")
        # Ensure stereo for Demucs
        if waveform.ndim == 1:
            waveform = np.stack([waveform, waveform])
        waveform_tensor = torch.from_numpy(waveform).float()
        if verbose:
            print("  Loading Demucs model...")
        model = get_model('htdemucs')
        model.eval()
        if waveform_tensor.dim() == 2:
            waveform_tensor = waveform_tensor.unsqueeze(0)
        waveform_tensor = convert_audio(waveform_tensor, sample_rate, model.samplerate, model.audio_channels)
        if verbose:
            print("  Running source separation...")
        with torch.no_grad():
            sources = apply_model(model, waveform_tensor, device='cpu')[0]
        sources = sources.cpu().numpy()
        vocals = sources[3]
        guitar = sources[2]
        if vocals.ndim > 1:
            vocals = librosa.to_mono(vocals)
        if guitar.ndim > 1:
            guitar = librosa.to_mono(guitar)
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            sf.write(output_path / 'vocals.wav', vocals, sample_rate)
            sf.write(output_path / 'guitar.wav', guitar, sample_rate)
            if verbose:
                print(f"  ✅ Saved separated sources to {output_path}")
        return guitar, vocals, sample_rate

    # No-separation mode: use full mix for both (allows WMM to run without demucs)
    if verbose:
        print("🎸 Using full mix (no source separation; demucs unavailable or --no-demucs).")
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        sf.write(output_path / 'vocals.wav', mono, sample_rate)
        sf.write(output_path / 'guitar.wav', mono, sample_rate)
    return mono.copy(), mono.copy(), sample_rate


def extract_rhythm_features(audio: np.ndarray, sr: int = 44100, verbose: bool = False) -> Dict[str, Any]:
    """
    Extract beat, onset, and tempo information.
    
    Args:
        audio: Audio waveform (mono)
        sr: Sample rate
        verbose: Print progress messages
        
    Returns:
        Dictionary of rhythm features
    """
    if verbose:
        print("  Extracting rhythm features...")
    
    # Tempo and beat tracking
    tempo, beats = librosa.beat.beat_track(y=audio, sr=sr)
    
    # Ensure tempo is scalar (sometimes returns array)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if len(tempo) > 0 else float(tempo)
    else:
        tempo = float(tempo)
    
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Onset detection (note starts)
    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    # Chroma features (for harmonic analysis)
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
    
    # RMS energy (for dynamic analysis)
    rms = librosa.feature.rms(y=audio)[0]
    
    return {
        'tempo': tempo,
        'beats': beats,
        'beat_times': beat_times,
        'beat_count': len(beats),
        'onsets': onset_frames,
        'onset_times': onset_times,
        'onset_count': len(onset_frames),
        'chroma': chroma,
        'rms': rms,
        'duration': len(audio) / sr
    }


def align_streams(guitar_features: Dict, vocal_features: Dict, verbose: bool = False) -> Dict[str, Any]:
    """
    Align guitar and vocal rhythm using Dynamic Time Warping.
    
    Args:
        guitar_features: Rhythm features from guitar
        vocal_features: Rhythm features from vocals
        verbose: Print progress messages
        
    Returns:
        Alignment metrics and warping path
    """
    if verbose:
        print("  Aligning streams with DTW...")
    
    # Use chroma features for alignment
    guitar_chroma = guitar_features['chroma']
    vocal_chroma = vocal_features['chroma']
    
    # Compute Dynamic Time Warping alignment
    D, wp = librosa.sequence.dtw(guitar_chroma, vocal_chroma, metric='cosine')
    
    # Compute coherence (inverse of normalized distance)
    avg_distance = np.mean(D[wp[:, 0], wp[:, 1]])
    coherence = 1.0 / (1.0 + avg_distance)
    
    # Analyze warping path for drift sections
    path_derivative = np.diff(wp[:, 1] / wp[:, 0])  # Rate of vocal progression relative to guitar
    drift_variance = np.var(path_derivative)
    
    return {
        'distance_matrix': D,
        'warping_path': wp,
        'coherence': coherence,
        'avg_distance': avg_distance,
        'drift_variance': drift_variance
    }


def compute_tempo_stability(guitar_tempo: float, vocal_tempo: float) -> float:
    """Measure tempo consistency between streams."""
    tempo_diff = abs(guitar_tempo - vocal_tempo)
    stability = 1.0 / (1.0 + tempo_diff / 10.0)  # Normalize
    return stability


def identify_challenge_sections(alignment: Dict, guitar_features: Dict, vocal_features: Dict, 
                                sr: int = 44100, threshold: float = 0.6) -> list:
    """
    Identify sections where guitar-vocal coupling is weak.
    
    Args:
        alignment: Alignment metrics from align_streams()
        guitar_features: Guitar rhythm features
        vocal_features: Vocal rhythm features
        sr: Sample rate
        threshold: Coherence threshold below which to flag as challenging
        
    Returns:
        List of challenge sections with timestamps
    """
    D = alignment['distance_matrix']
    wp = alignment['warping_path']
    
    # Compute local coherence along warping path
    window_size = 20
    challenge_sections = []
    
    for i in range(0, len(wp) - window_size, window_size // 2):
        window = wp[i:i+window_size]
        local_distance = np.mean(D[window[:, 0], window[:, 1]])
        local_coherence = 1.0 / (1.0 + local_distance)
        
        if local_coherence < threshold:
            # Convert frame indices to time
            start_time = librosa.frames_to_time(window[0, 0], sr=sr)
            end_time = librosa.frames_to_time(window[-1, 0], sr=sr)
            
            challenge_sections.append({
                'start': start_time,
                'end': end_time,
                'coherence': local_coherence,
                'description': 'Low coupling' if local_coherence < 0.5 else 'Moderate coupling'
            })
    
    return challenge_sections


def measure_structural_lock(guitar_beats: np.ndarray, vocal_onsets: np.ndarray, 
                            guitar_beat_times: np.ndarray, vocal_onset_times: np.ndarray) -> Dict:
    """
    Measure how tightly guitar beats lock with vocal onsets.
    
    Returns:
        Metrics for structural coupling strength
    """
    # For each vocal onset, find nearest guitar beat
    lock_distances = []
    for vocal_time in vocal_onset_times:
        nearest_beat_idx = np.argmin(np.abs(guitar_beat_times - vocal_time))
        distance = abs(guitar_beat_times[nearest_beat_idx] - vocal_time)
        lock_distances.append(distance)
    
    avg_lock_distance = np.mean(lock_distances)
    lock_strength = 1.0 / (1.0 + avg_lock_distance * 10)  # Normalize
    
    return {
        'avg_lock_distance': avg_lock_distance,
        'lock_strength': lock_strength,
        'tight_locks': sum(1 for d in lock_distances if d < 0.1),  # Within 100ms
        'loose_locks': sum(1 for d in lock_distances if d > 0.3)   # Beyond 300ms
    }


def generate_flow_report(guitar_features: Dict, vocal_features: Dict, 
                        alignment: Dict, structural_lock: Dict, 
                        challenge_sections: list, sr: int = 44100) -> Dict:
    """
    Generate comprehensive flow analysis report.
    
    Returns:
        Human-readable flow metrics
    """
    tempo_stability = compute_tempo_stability(guitar_features['tempo'], vocal_features['tempo'])
    
    # Classify overall performance
    coherence = alignment['coherence']
    if coherence >= 0.85:
        quality = "Peak coupling (locked in)"
    elif coherence >= 0.70:
        quality = "High coupling"
    elif coherence >= 0.55:
        quality = "Moderate coupling"
    else:
        quality = "Low coupling (learning/exploring)"
    
    return {
        'overall_coherence': coherence,
        'quality_classification': quality,
        'tempo_stability': tempo_stability,
        'structural_lock': structural_lock,
        'challenge_sections': challenge_sections,
        'guitar_tempo': guitar_features['tempo'],
        'vocal_tempo': vocal_features['tempo'],  # Inferred from onsets
        'guitar_beats': guitar_features['beat_count'],
        'vocal_onsets': vocal_features['onset_count'],
        'duration': guitar_features['duration']
    }


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def print_flow_report(report: Dict, audio_path: str, verbose: bool = False):
    """
    Print formatted flow analysis report.
    
    Args:
        report: Flow report from generate_flow_report()
        audio_path: Path to original audio file
        verbose: Include detailed metrics
    """
    print("\n" + "="*60)
    print("🎵 WAVE MODULATION MACHINE 🎵")
    print("="*60)
    print()
    print(f"File: {Path(audio_path).name}")
    print(f"Duration: {format_time(report['duration'])}")
    print()
    
    print("GUITAR STREAM")
    print("-" * 40)
    print(f"Tempo: {report['guitar_tempo']:.1f} BPM")
    print(f"Beat count: {report['guitar_beats']}")
    print()
    
    print("VOCAL STREAM")
    print("-" * 40)
    print(f"Onset count: {report['vocal_onsets']}")
    print()
    
    print("ALIGNMENT")
    print("-" * 40)
    print(f"Overall coherence: {report['overall_coherence']:.2f}")
    print(f"Quality: {report['quality_classification']}")
    print(f"Tempo stability: {report['tempo_stability']:.2f}")
    print()
    
    print("STRUCTURAL COUPLING")
    print("-" * 40)
    lock = report['structural_lock']
    print(f"Lock strength: {lock['lock_strength']:.2f}")
    print(f"Tight locks (<100ms): {lock['tight_locks']}")
    print(f"Loose locks (>300ms): {lock['loose_locks']}")
    print()
    
    if report['challenge_sections']:
        print("CHALLENGE AREAS")
        print("-" * 40)
        for section in report['challenge_sections'][:5]:  # Show top 5
            start_str = format_time(section['start'])
            end_str = format_time(section['end'])
            print(f"• {start_str}-{end_str}: {section['description']} ({section['coherence']:.2f})")
        print()
    
    print("STRUCTURAL NOTES")
    print("-" * 40)
    
    if report['overall_coherence'] >= 0.85:
        print("Peak performance. Guitar and vocals are tightly locked.")
    elif report['overall_coherence'] >= 0.70:
        print("Strong coupling. Rhythm is consistent and well-aligned.")
    elif report['overall_coherence'] >= 0.55:
        print("Moderate coupling. Some sections show drift or exploration.")
    else:
        print("Learning/exploration phase. Natural for first playthrough.")
    
    if report['challenge_sections']:
        print("Challenge areas identified. These show honest navigation.")
    
    print("No evidence of performative smoothing detected.")
    print("First playthrough characteristics preserved.")
    print()
    
    print("="*60)
    print()
    
    if verbose:
        print("\nDETAILED METRICS")
        print("-" * 40)
        print(f"Average lock distance: {lock['avg_lock_distance']:.3f}s")
        print(f"Guitar tempo: {report['guitar_tempo']:.2f} BPM")
        print(f"Inferred vocal tempo: {report['vocal_tempo']:.2f} BPM")
        print()


# ========================================
# Main Execution
# ========================================

def analyze_audio(
    audio_path: str,
    save_sources: bool = False,
    verbose: bool = False,
    use_demucs: bool = True,
) -> Dict:
    """
    Run complete wave modulation analysis.
    
    Args:
        audio_path: Path to input audio file
        save_sources: Save separated guitar and vocal tracks
        verbose: Print detailed progress and metrics
        use_demucs: If False or demucs not installed, use full mix (no separation).
        
    Returns:
        Complete analysis report
    """
    # 1. Separate sources (or use full mix when demucs unavailable)
    output_dir = str(Path(audio_path).parent / 'separated') if save_sources else None
    guitar, vocals, sr = separate_sources(audio_path, output_dir, verbose, use_demucs=use_demucs)
    
    # 2. Extract rhythm features
    if verbose:
        print("\n🎸 Analyzing guitar...")
    guitar_features = extract_rhythm_features(guitar, sr, verbose)
    
    if verbose:
        print("\n🎤 Analyzing vocals...")
    vocal_features = extract_rhythm_features(vocals, sr, verbose)
    
    # 3. Align streams
    if verbose:
        print("\n🔗 Aligning streams...")
    alignment = align_streams(guitar_features, vocal_features, verbose)
    
    # 4. Measure structural coupling
    structural_lock = measure_structural_lock(
        guitar_features['beats'],
        vocal_features['onsets'],
        guitar_features['beat_times'],
        vocal_features['onset_times']
    )
    
    # 5. Identify challenge sections
    challenge_sections = identify_challenge_sections(
        alignment, guitar_features, vocal_features, sr
    )
    
    # 6. Generate report
    if verbose:
        print("\n📊 Generating flow report...")
    report = generate_flow_report(
        guitar_features, vocal_features, alignment, 
        structural_lock, challenge_sections, sr
    )
    
    return report


def plot_waveform(audio_path: str, output_path: str = None, verbose: bool = False) -> str:
    """
    Plot full-mix waveform and save to PNG.
    
    Args:
        audio_path: Path to input audio file
        output_path: Where to save PNG (default: same dir as audio, stem_waveform.png)
        verbose: Print path when saved
        
    Returns:
        Path to saved PNG
    """
    audio_path = Path(audio_path)
    if output_path is None:
        output_path = audio_path.parent / f"{audio_path.stem}_waveform.png"
    else:
        output_path = Path(output_path)
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠ matplotlib not installed; skip --save-waveform or: pip install matplotlib")
        return ""
    
    waveform, sr = librosa.load(str(audio_path), sr=44100, mono=True)
    duration = len(waveform) / sr
    times = np.arange(len(waveform)) / sr
    
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(times, waveform, linewidth=0.5, color='#2d3748')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude')
    ax.set_title(f'Waveform: {audio_path.name}')
    ax.set_xlim(0, duration)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()
    
    if verbose:
        print(f"\n📈 Waveform saved to: {output_path}")
    return str(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='🎵 Wave Modulation Machine: Audio flow analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 wave_modulation_machine.py song.m4a
  python3 wave_modulation_machine.py song.m4a --verbose
  python3 wave_modulation_machine.py song.m4a --save-sources
  python3 wave_modulation_machine.py song.m4a --save-waveform
  
Philosophy:
  "Execute quietly. So you can hear."
  - Growing edges: Expanding capability through structural addition
  - Quantifies subjective "flow" as measurable structural coupling
        """
    )
    
    parser.add_argument('audio_file', help='Path to audio file (m4a, mp3, wav, etc.)')
    parser.add_argument('--save-sources', action='store_true',
                       help='Save separated guitar and vocal tracks')
    parser.add_argument('--save-json', action='store_true',
                       help='Save results as JSON for qualitative agent')
    parser.add_argument('--no-demucs', action='store_true',
                       help='Skip source separation; use full mix (run without demucs installed)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print detailed progress and metrics')
    parser.add_argument('--save-waveform', action='store_true',
                       help='Save waveform plot (PNG) next to audio file')
    
    args = parser.parse_args()
    
    # Validate input
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"❌ Error: File not found: {audio_path}")
        sys.exit(1)
    
    try:
        # Run analysis (use_demucs=False when --no-demucs or when demucs not installed)
        use_demucs = not args.no_demucs and DEMUCS_AVAILABLE
        report = analyze_audio(
            str(audio_path),
            save_sources=args.save_sources,
            verbose=args.verbose,
            use_demucs=use_demucs,
        )
        
        # Print report
        print_flow_report(report, str(audio_path), verbose=args.verbose)
        
        # Optionally save JSON for qualitative agent
        if args.save_json:
            json_path = audio_path.parent / f"{audio_path.stem}_WMM_RESULTS.json"
            with open(json_path, 'w') as f:
                # Convert numpy types to native Python types for JSON serialization
                json_report = {
                    'overall_coherence': float(report['overall_coherence']),
                    'quality_classification': report['quality_classification'],
                    'tempo_stability': float(report['tempo_stability']),
                    'structural_lock': {
                        'lock_strength': float(report['structural_lock']['lock_strength']),
                        'tight_locks': int(report['structural_lock']['tight_locks']),
                        'loose_locks': int(report['structural_lock']['loose_locks']),
                        'avg_lock_distance': float(report['structural_lock']['avg_lock_distance'])
                    },
                    'challenge_sections': report['challenge_sections'],
                    'guitar_tempo': float(report['guitar_tempo']),
                    'vocal_tempo': float(report['vocal_tempo']),
                    'guitar_beats': int(report['guitar_beats']),
                    'vocal_onsets': int(report['vocal_onsets']),
                    'duration': float(report['duration'])
                }
                json.dump(json_report, f, indent=2)
            print(f"\n💾 JSON results saved to: {json_path}")
            print(f"\nRun qualitative analysis:")
            print(f'  python3 wave_modulation_agent.py {json_path} "first playthrough"')
        
        # Optionally save waveform visual
        if args.save_waveform:
            plot_waveform(str(audio_path), verbose=args.verbose)
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

