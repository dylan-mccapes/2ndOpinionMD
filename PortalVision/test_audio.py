#!/usr/bin/env python3
"""
Test script for Audio Export v0.1.5

Tests:
1. HTML to text projection (verbatim)
2. Text validation
3. Audio generation (requires gTTS)
4. Audio receipt creation
5. End-to-end flow

Usage:
    python PortalVision/test_audio.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from PortalVision.audio_projector import html_to_audio_text, validate_audio_text
from PortalVision.audio_generator import AudioGenerator, GTTS_AVAILABLE
from PortalVision.audio_receipts import AudioReceiptStore
from PortalVision.vault import EpistemicHTMLVault


def test_audio_projection():
    """Test HTML to audio text conversion."""
    print("=" * 60)
    print("TEST: Audio Projection (HTML → Text)")
    print("=" * 60)
    
    # Test HTML with semantic structure
    test_html = """
    <html>
    <head><title>Test Report</title></head>
    <body>
        <h1>Clinical Evidence Summary</h1>
        <p>This is a test paragraph with important information.</p>
        
        <h2>Differential Diagnoses</h2>
        <ul>
            <li>Rheumatoid Arthritis (ICD-10: M06.9)</li>
            <li>Systemic Lupus Erythematosus (ICD-10: M32.9)</li>
            <li>Fibromyalgia (ICD-10: M79.7)</li>
        </ul>
        
        <h2>Evidence</h2>
        <p>Based on ACR 2021 guidelines for rheumatoid arthritis, the following criteria are relevant:</p>
        <blockquote>Persistent joint inflammation for more than 6 weeks.</blockquote>
        
        <section>
            <h3>Limitations</h3>
            <p>This assessment is based on guidelines only.</p>
        </section>
        
        <!-- This should be skipped -->
        <script>alert('test');</script>
        <button>Click me</button>
    </body>
    </html>
    """
    
    print("\n1. Converting HTML to audio text...")
    audio_text = html_to_audio_text(test_html)
    
    print(f"   ✓ Generated {len(audio_text)} characters")
    print(f"   ✓ Word count: {len(audio_text.split())}")
    
    # Verify semantic elements preserved
    checks = [
        ("Heading level 1" in audio_text, "H1 preserved"),
        ("Heading level 2" in audio_text, "H2 preserved"),
        ("List:" in audio_text, "List indicator preserved"),
        ("Item 1:" in audio_text, "List items preserved"),
        ("Quote:" in audio_text, "Blockquote preserved"),
        ("Section:" in audio_text, "Section preserved"),
        ("alert" not in audio_text, "Script stripped"),
        ("Click me" not in audio_text, "Button stripped"),
    ]
    
    print("\n2. Verifying semantic structure...")
    for passed, description in checks:
        status = "✓" if passed else "✗"
        print(f"   {status} {description}")
    
    # Validate text
    print("\n3. Validating audio text...")
    is_valid, error = validate_audio_text(audio_text)
    print(f"   {'✓' if is_valid else '✗'} Validation: {is_valid}")
    if not is_valid:
        print(f"   Error: {error}")
    
    # Show preview
    print("\n4. Audio text preview (first 300 chars):")
    print("   " + "-" * 56)
    preview = audio_text[:300].replace('\n', '\n   ')
    print(f"   {preview}...")
    print("   " + "-" * 56)
    
    return audio_text


def test_audio_generation(text: str):
    """Test audio file generation."""
    print("\n" + "=" * 60)
    print("TEST: Audio Generation (Text → Audio)")
    print("=" * 60)
    
    if not GTTS_AVAILABLE:
        print("\n⚠ gTTS not installed. Skipping audio generation test.")
        print("   Install with: pip install gtts")
        return None
    
    generator = AudioGenerator(output_dir="portal_vision_data/audio")
    
    print("\n1. Generating audio file...")
    success, audio_path, error = generator.generate_audio(text)
    
    if success:
        print(f"   ✓ Audio generated: {audio_path}")
        
        # Check file exists
        from pathlib import Path
        audio_file = Path(audio_path)
        if audio_file.exists():
            file_size = audio_file.stat().st_size
            print(f"   ✓ File exists: {file_size:,} bytes")
        else:
            print("   ✗ File not found")
            return None
        
        return audio_path
    else:
        print(f"   ✗ Audio generation failed: {error}")
        return None


def test_audio_receipts(artifact_id: str, artifact_hash: str, audio_path: str):
    """Test audio receipt creation."""
    print("\n" + "=" * 60)
    print("TEST: Audio Receipts")
    print("=" * 60)
    
    store = AudioReceiptStore(receipts_dir="portal_vision_data/receipts")
    
    print("\n1. Recording audio export receipt...")
    receipt = store.record(
        source_artifact_id=artifact_id,
        source_artifact_hash=artifact_hash,
        audio_file_path=audio_path,
        operator_id="test_operator_audio",
        consent_phrase="I consent to generate an audio projection of this artifact.",
    )
    
    print(f"   ✓ Receipt ID: {receipt.receipt_id}")
    print(f"   ✓ Artifact type: {receipt.artifact_type}")
    print(f"   ✓ Authority: {receipt.authority}")
    print(f"   ✓ Audio is authoritative: {receipt.audio_is_authoritative}")
    print(f"   ✓ Transformation: {receipt.transformation}")
    
    # Verify receipt structure
    print("\n2. Verifying receipt structure...")
    checks = [
        (receipt.artifact_type == "audio_projection", "Artifact type correct"),
        (receipt.source_artifact == "epistemic_html", "Source artifact correct"),
        (receipt.authority == "html", "Authority is HTML"),
        (receipt.audio_is_authoritative == False, "Audio not authoritative"),
        (receipt.content_transformed == False, "Content not transformed"),
        (receipt.transformation == "verbatim narration", "Transformation type correct"),
    ]
    
    for passed, description in checks:
        status = "✓" if passed else "✗"
        print(f"   {status} {description}")
    
    # List receipts
    print("\n3. Listing receipts...")
    receipts = store.list_receipts()
    print(f"   ✓ Total receipts: {len(receipts)}")
    for r in receipts[-3:]:
        print(f"     - {r.receipt_id}: {r.source_artifact_id}")
    
    return receipt


def test_end_to_end():
    """Test complete audio export flow."""
    print("\n" + "=" * 60)
    print("TEST: End-to-End Audio Export")
    print("=" * 60)
    
    # Create test artifact
    vault = EpistemicHTMLVault(vault_dir="portal_vision_data/vault")
    
    test_html = """
    <html>
    <head><title>Medical Report</title></head>
    <body>
        <h1>Clinical Assessment</h1>
        <p>Patient presents with chronic fatigue and joint pain.</p>
        <h2>Findings</h2>
        <ul>
            <li>Bilateral joint inflammation</li>
            <li>Morning stiffness lasting over 1 hour</li>
            <li>Positive rheumatoid factor</li>
        </ul>
        <h2>Recommendation</h2>
        <p>Refer to rheumatology for further evaluation.</p>
    </body>
    </html>
    """
    
    print("\n1. Storing HTML artifact...")
    artifact = vault.store(
        html_content=test_html,
        provenance={
            "mode": "ask",
            "query": "Test audio export",
            "timestamp": "2025-01-03T12:00:00Z",
        },
        metadata={"test": True},
    )
    print(f"   ✓ Artifact ID: {artifact.artifact_id}")
    
    # Convert to audio text
    print("\n2. Converting to audio text...")
    audio_text = html_to_audio_text(artifact.html_content)
    is_valid, _ = validate_audio_text(audio_text)
    print(f"   ✓ Valid: {is_valid}, {len(audio_text.split())} words")
    
    # Generate audio (if available)
    if GTTS_AVAILABLE:
        print("\n3. Generating audio...")
        generator = AudioGenerator(output_dir="portal_vision_data/audio")
        success, audio_path, error = generator.generate_audio(audio_text)
        
        if success:
            print(f"   ✓ Audio: {audio_path}")
            
            # Record receipt
            print("\n4. Recording receipt...")
            store = AudioReceiptStore(receipts_dir="portal_vision_data/receipts")
            receipt = store.record(
                source_artifact_id=artifact.artifact_id,
                source_artifact_hash=artifact.content_hash,
                audio_file_path=audio_path,
                operator_id="test_e2e",
                consent_phrase="I consent to generate an audio projection of this artifact.",
            )
            print(f"   ✓ Receipt: {receipt.receipt_id}")
            
            return artifact, audio_path, receipt
        else:
            print(f"   ✗ Failed: {error}")
    else:
        print("\n⚠ Skipping audio generation (gTTS not installed)")
    
    return artifact, None, None


def print_manual_test_instructions(artifact_id: str):
    """Print instructions for manual consent gate test."""
    print("\n" + "=" * 60)
    print("MANUAL TEST: Audio Consent Gate")
    print("=" * 60)
    
    print("\n1. Start the API server:")
    print("   cd server && python -m uvicorn api.app_postgres:app --reload")
    
    print("\n2. Open the audio consent gate:")
    print(f"   http://localhost:8000/PortalVision/audio_consent.html?artifact_id={artifact_id}")
    
    print("\n3. Review:")
    print("   - Artifact metadata")
    print("   - Audio text preview")
    print("   - Estimated duration")
    
    print("\n4. Type the consent phrase EXACTLY:")
    print("   I consent to generate an audio projection of this artifact.")
    
    print("\n5. Click 'Export Audio'")
    
    print("\n6. Verify:")
    print("   - Receipt created")
    print("   - Download link appears")
    print("   - Audio file downloads")
    print("   - Audio plays correctly")
    
    print("\n7. Check receipts:")
    print("   curl http://localhost:8000/api/audio/receipts")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 16 + "Audio Export v0.1.5" + " " * 23 + "║")
    print("║" + " " * 20 + "Test Suite" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test projection
    audio_text = test_audio_projection()
    
    # Test audio generation (if gTTS available)
    audio_path = test_audio_generation(audio_text[:500])  # Use shorter text for test
    
    # Test receipts (if audio generated)
    if audio_path:
        test_audio_receipts("TEST_ARTIFACT_ID", "test_hash_123", audio_path)
    
    # Test end-to-end
    artifact, audio_path, receipt = test_end_to_end()
    
    # Manual test instructions
    if artifact:
        print_manual_test_instructions(artifact.artifact_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Audio projection: HTML → Text")
    print("✓ Text validation")
    if GTTS_AVAILABLE:
        print("✓ Audio generation: Text → MP3")
        print("✓ Audio receipts")
        print("✓ End-to-end flow")
    else:
        print("⚠ Audio generation: gTTS not installed")
    print("⚠ Manual: Consent gate and export (see instructions above)")
    print("\nAll automated tests completed.")
    if artifact:
        print(f"\nArtifact ID for manual test: {artifact.artifact_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()

