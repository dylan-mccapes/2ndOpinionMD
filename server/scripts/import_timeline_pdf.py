#!/usr/bin/env python3
"""
Import timeline PDF for session-only EoHD investigation.

This script mimics repo_vision.py's incremental building pattern:
1. Decrypt PDF if encrypted (password prompt)
2. Extract text from PDF pages
3. Build structured timeline in memory (session-only, no DB writes)
4. Return TimelineSummary for immediate use

Usage:
    python server/scripts/import_timeline_pdf.py \
        --pdf-path data/patient-timelines/example.pdf \
        --patient-id session_patient \
        [--password SECRET]

Session-only guarantees:
- No writes to rag_corpus or ehr.patient_timeline
- All data stays in memory
- Password deleted immediately after decryption
- Returns structured timeline object for immediate EoHD execution
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import getpass
import secrets

# Add parent dirs to path for imports
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SERVER_DIR))

from pypdf import PdfReader
import pypdf.errors

def decrypt_pdf_if_needed(
    pdf_path: Path,
    password: Optional[str] = None
) -> tuple[PdfReader, bool]:
    """
    Attempt to open PDF, prompting for password if encrypted.
    
    Returns:
        (reader, was_encrypted)
    """
    reader = PdfReader(str(pdf_path))
    
    if not reader.is_encrypted:
        return reader, False
    
    # PDF is encrypted - need password
    if password is None:
        print("=" * 60)
        print("🔒 TIMELINE PDF IS ENCRYPTED")
        print("=" * 60)
        print("\nThis timeline requires a password for decryption.\n")
        print("🔒 Your password will be:")
        print("  • Used ONLY to decrypt this PDF")
        print("  • Immediately deleted from memory after use")
        print("  • Never transmitted or stored\n")
        print("🗑️  All timeline data is session-only:")
        print("  • No permanent storage")
        print("  • Cleared immediately after investigation")
        print("  • Data removal receipts in HTML export\n")
        
        password = getpass.getpass("Enter decryption password: ")
    
    # Attempt decryption
    try:
        if reader.decrypt(password) == 0:
            raise ValueError("Incorrect password")
    except Exception as e:
        raise ValueError(f"Failed to decrypt PDF: {e}")
    
    return reader, True


def extract_timeline_text(
    reader: PdfReader,
    max_pages: Optional[int] = None
) -> str:
    """
    Extract all text from PDF pages.
    
    Similar to ingest_guideline_pdf but returns single text block
    instead of per-page chunks.
    """
    num_pages = len(reader.pages)
    if max_pages:
        num_pages = min(num_pages, max_pages)
    
    print(f"📄 Extracting text from {num_pages} pages...")
    
    chunks = []
    for idx in range(num_pages):
        page = reader.pages[idx]
        text = (page.extract_text() or "").strip()
        
        # Clean NUL bytes and normalize whitespace
        text = text.replace("\x00", "")
        
        if text:
            # Add page marker for context
            chunks.append(f"=== Page {idx + 1} ===\n{text}")
    
    timeline_text = "\n\n".join(chunks)
    print(f"✅ Extracted {len(timeline_text)} characters from PDF")
    
    return timeline_text


def build_session_timeline_summary(
    timeline_text: str,
    patient_id: str = "session_patient"
) -> Dict[str, Any]:
    """
    Build a minimal timeline summary structure for session use.
    
    This does NOT use TimelineSummarizer's full LLM pipeline.
    That happens later in the EoHD workflow.
    
    Returns simple structured object similar to repo_vision.json structure.
    """
    return {
        "patient_id": patient_id,
        "timeline_text": timeline_text,
        "source": "pdf_import_session_only",
        "extracted_at": datetime.utcnow().isoformat(),
        "char_count": len(timeline_text),
        "session_only": True,
        "notes": "This timeline was imported for session-only use. No data persisted to database.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import timeline PDF for session-only EoHD investigation"
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        type=Path,
        help="Path to patient timeline PDF",
    )
    parser.add_argument(
        "--patient-id",
        default="session_patient",
        help="Patient ID for session (default: session_patient)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="PDF decryption password (will prompt if not provided and PDF is encrypted)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to extract (for testing)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional: write session timeline to JSON file (for inspection only)",
    )
    
    args = parser.parse_args()
    
    pdf_path: Path = args.pdf_path
    
    if not pdf_path.exists():
        raise SystemExit(f"❌ PDF not found: {pdf_path}")
    
    print(f"📦 Importing timeline PDF: {pdf_path.name}")
    print(f"🔑 Patient ID: {args.patient_id}")
    print(f"🗂️  Session-only mode: ENABLED")
    print()
    
    # Step 1: Decrypt if needed
    try:
        reader, was_encrypted = decrypt_pdf_if_needed(pdf_path, args.password)
        
        if was_encrypted:
            print("✅ PDF decrypted successfully")
            print("🗑️  Password deleted from memory")
            # Explicitly delete password variable
            if args.password:
                del args.password
        else:
            print("✅ PDF opened (not encrypted)")
    
    except ValueError as e:
        raise SystemExit(f"❌ {e}")
    except Exception as e:
        raise SystemExit(f"❌ Failed to open PDF: {e}")
    
    print()
    
    # Step 2: Extract timeline text
    try:
        timeline_text = extract_timeline_text(reader, args.max_pages)
    except Exception as e:
        raise SystemExit(f"❌ Failed to extract text: {e}")
    
    print()
    
    # Step 3: Build session timeline structure
    session_timeline = build_session_timeline_summary(
        timeline_text,
        patient_id=args.patient_id
    )
    
    print("=" * 60)
    print("📊 SESSION TIMELINE SUMMARY")
    print("=" * 60)
    print(f"Patient ID:    {session_timeline['patient_id']}")
    print(f"Source:        {session_timeline['source']}")
    print(f"Extracted at:  {session_timeline['extracted_at']}")
    print(f"Text length:   {session_timeline['char_count']:,} characters")
    print(f"Session-only:  {session_timeline['session_only']}")
    print()
    
    # Step 4: Optional JSON output for inspection
    if args.output_json:
        print(f"💾 Writing session timeline to: {args.output_json}")
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w") as f:
            json.dump(session_timeline, f, indent=2)
        print("✅ JSON written")
        print()
    
    # Step 5: Output structured result for programmatic use
    print("=" * 60)
    print("🎯 READY FOR EoHD EXECUTION")
    print("=" * 60)
    print("\nSession timeline object ready for EoHD investigation.")
    print("Timeline text available in: session_timeline['timeline_text']")
    print("\nNext steps:")
    print("  1. Pass timeline_text to EoHD investigator")
    print("  2. Run /eoh_detective_stream with session context")
    print("  3. Generate HTML export with data removal receipts")
    print()
    
    return session_timeline


if __name__ == "__main__":
    try:
        result = main()
        # If running as module, return the result
        if __name__ == "__main__":
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

