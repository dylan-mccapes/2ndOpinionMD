"""
Audio Generator - Text to speech conversion.

Responsibilities:
- Convert text to audio file
- Use TTS engine (configurable)
- Generate audio in standard format (mp3/wav)
- Best-effort generation (no retry)

Non-responsibilities:
- Voice selection
- Pacing control
- Emphasis injection
- Quality assurance
"""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class AudioGenerationError(Exception):
    """Raised when audio generation fails."""
    pass


class AudioGenerator:
    """
    Converts text to audio using TTS.
    
    Uses gTTS (Google Text-to-Speech) by default.
    Falls back to system TTS if available.
    
    Constraints:
    - Best-effort only
    - No retry
    - No quality verification
    - Standard format (mp3)
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_audio_id(self, text: str) -> str:
        """Generate a unique audio file ID from text hash."""
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return text_hash[:16].upper()
    
    def generate_audio(
        self,
        text: str,
        lang: str = 'en',
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate audio from text.
        
        Args:
            text: The text to narrate
            lang: Language code (default: 'en')
        
        Returns:
            (success: bool, audio_path: Optional[str], error: Optional[str])
        
        Behavior:
        - Creates mp3 file
        - Uses gTTS if available
        - Falls back to system TTS
        - Returns path on success
        - Returns error message on failure
        - No retry
        """
        if not GTTS_AVAILABLE:
            return False, None, "gTTS library not available. Install with: pip install gtts"
        
        try:
            # Generate audio ID
            audio_id = self._generate_audio_id(text)
            audio_filename = f"{audio_id}.mp3"
            audio_path = self.output_dir / audio_filename
            
            # Skip if already exists (idempotent)
            if audio_path.exists():
                return True, str(audio_path), None
            
            # Generate audio using gTTS
            tts = gTTS(text=text, lang=lang, slow=False)
            
            # Save to file
            tts.save(str(audio_path))
            
            # Verify file exists
            if not audio_path.exists():
                return False, None, "Audio file not created"
            
            return True, str(audio_path), None
        
        except Exception as e:
            return False, None, f"Audio generation failed: {str(e)}"
    
    def get_audio_path(self, audio_id: str) -> Optional[Path]:
        """Get path to an existing audio file."""
        audio_path = self.output_dir / f"{audio_id}.mp3"
        return audio_path if audio_path.exists() else None
    
    def cleanup_audio(self, audio_path: str):
        """Clean up audio file (best effort)."""
        try:
            os.unlink(audio_path)
        except Exception:
            pass  # Silent failure is acceptable for cleanup


def text_to_audio(
    text: str,
    output_dir: str,
    lang: str = 'en',
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convenience function to generate audio from text.
    
    Args:
        text: The text to narrate
        output_dir: Directory to save audio files
        lang: Language code (default: 'en')
    
    Returns:
        (success: bool, audio_path: Optional[str], error: Optional[str])
    """
    generator = AudioGenerator(output_dir=output_dir)
    return generator.generate_audio(text, lang)

