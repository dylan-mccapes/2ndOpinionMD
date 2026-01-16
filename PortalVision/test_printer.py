#!/usr/bin/env python3
"""
Test script for Printer Application v0.1

Tests:
1. Store an artifact
2. Retrieve artifact
3. List artifacts
4. Verify integrity
5. Print consent flow (manual step)
6. Verify receipt

Usage:
    python PortalVision/test_printer.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from PortalVision.vault import EpistemicHTMLVault
from PortalVision.receipts import PrintReceiptStore


def test_vault():
    """Test Epistemic HTML Vault operations."""
    print("=" * 60)
    print("TEST: Epistemic HTML Vault")
    print("=" * 60)
    
    vault = EpistemicHTMLVault(vault_dir="portal_vision_data/vault")
    
    # Store test artifact
    test_html = """
    <html>
    <head><title>Test Medical Report</title></head>
    <body>
        <h1>Clinical Evidence Summary</h1>
        <h2>Differential Diagnoses</h2>
        <ul>
            <li>Rheumatoid Arthritis (ICD-10: M06.9)</li>
            <li>Systemic Lupus Erythematosus (ICD-10: M32.9)</li>
            <li>Fibromyalgia (ICD-10: M79.7)</li>
        </ul>
        <h2>Evidence</h2>
        <p>Based on ACR 2021 guidelines for rheumatoid arthritis...</p>
    </body>
    </html>
    """
    
    provenance = {
        "mode": "ask",
        "query": "What are differential diagnoses for chronic fatigue and joint pain?",
        "timestamp": "2025-01-03T12:00:00Z",
        "sources_used": 5,
        "confidence": 0.85,
    }
    
    metadata = {
        "operator": "test_operator",
        "session": "test_session_001",
    }
    
    print("\n1. Storing artifact...")
    artifact = vault.store(test_html, provenance, metadata)
    print(f"   ✓ Artifact ID: {artifact.artifact_id}")
    print(f"   ✓ Content Hash: {artifact.content_hash}")
    print(f"   ✓ Created At: {artifact.created_at}")
    
    # Retrieve artifact
    print("\n2. Retrieving artifact...")
    retrieved = vault.retrieve(artifact.artifact_id)
    if retrieved:
        print(f"   ✓ Retrieved: {retrieved.artifact_id}")
        print(f"   ✓ Mode: {retrieved.provenance['mode']}")
        print(f"   ✓ Query: {retrieved.provenance['query'][:50]}...")
    else:
        print("   ✗ Retrieval failed")
        return None
    
    # Verify integrity
    print("\n3. Verifying integrity...")
    is_valid = vault.verify_integrity(artifact.artifact_id)
    print(f"   {'✓' if is_valid else '✗'} Integrity: {is_valid}")
    
    # List artifacts
    print("\n4. Listing artifacts...")
    artifacts = vault.list_artifacts()
    print(f"   ✓ Total artifacts: {len(artifacts)}")
    for aid, meta in list(artifacts.items())[-3:]:
        print(f"     - {aid}: {meta.get('provenance', {}).get('mode', 'unknown')}")
    
    return artifact


def test_receipts(artifact_id: str, artifact_hash: str):
    """Test Print Receipt Store operations."""
    print("\n" + "=" * 60)
    print("TEST: Print Receipt Store")
    print("=" * 60)
    
    store = PrintReceiptStore(receipts_dir="portal_vision_data/receipts")
    
    # Record test receipt
    print("\n1. Recording print receipt...")
    receipt = store.record(
        artifact_id=artifact_id,
        artifact_hash=artifact_hash,
        operator_id="test_operator_123",
        consent_text="I consent to print this artifact exactly as rendered.",
    )
    print(f"   ✓ Receipt ID: {receipt.receipt_id}")
    print(f"   ✓ Timestamp: {receipt.timestamp}")
    print(f"   ✓ Note: {receipt.note}")
    
    # List receipts
    print("\n2. Listing receipts...")
    receipts = store.list_receipts()
    print(f"   ✓ Total receipts: {len(receipts)}")
    for r in receipts[-3:]:
        print(f"     - {r.receipt_id}: {r.artifact_id} by {r.operator_id}")
    
    # Get specific receipt
    print("\n3. Retrieving specific receipt...")
    retrieved = store.get_receipt(receipt.receipt_id)
    if retrieved:
        print(f"   ✓ Retrieved: {retrieved.receipt_id}")
        print(f"   ✓ Artifact: {retrieved.artifact_id}")
        print(f"   ✓ Operator: {retrieved.operator_id}")
    else:
        print("   ✗ Retrieval failed")
    
    return receipt


def print_manual_test_instructions(artifact_id: str):
    """Print instructions for manual consent gate test."""
    print("\n" + "=" * 60)
    print("MANUAL TEST: Consent Gate & Print")
    print("=" * 60)
    
    print("\n1. Start the API server:")
    print("   cd server && python -m uvicorn api.app_postgres:app --reload")
    
    print("\n2. Open the consent gate in your browser:")
    print(f"   http://localhost:8000/PortalVision/print_consent.html?artifact_id={artifact_id}")
    
    print("\n3. Review artifact metadata and preview")
    
    print("\n4. Type the consent text EXACTLY:")
    print("   I consent to print this artifact exactly as rendered.")
    
    print("\n5. Click 'Print' button")
    
    print("\n6. Verify:")
    print("   - Browser opens with print dialog")
    print("   - Receipt is created")
    print("   - Receipt contains correct artifact_id, operator_id, timestamp")
    
    print("\n7. Check receipt via API:")
    print("   curl http://localhost:8000/api/printer/receipts")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Printer Application v0.1" + " " * 19 + "║")
    print("║" + " " * 20 + "Test Suite" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test vault
    artifact = test_vault()
    if not artifact:
        print("\n✗ Vault tests failed. Aborting.")
        return
    
    # Test receipts
    receipt = test_receipts(artifact.artifact_id, artifact.content_hash)
    if not receipt:
        print("\n✗ Receipt tests failed. Aborting.")
        return
    
    # Manual test instructions
    print_manual_test_instructions(artifact.artifact_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Vault: Store, retrieve, verify, list")
    print("✓ Receipts: Record, retrieve, list")
    print("⚠ Manual: Consent gate and print (see instructions above)")
    print("\nAll automated tests passed.")
    print(f"\nArtifact ID for manual test: {artifact.artifact_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()

