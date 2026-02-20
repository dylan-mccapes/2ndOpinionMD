#!/usr/bin/env python3
"""
Test script for Norman Eric Roberts timeline PDF import with PatientTimelineVision.

Norman is Nate's dad, has Myasthenia Gravis (MG).

Usage:
    cd /path/to/2ndOpinionMD-MVP/server
    python scripts/test_norman_timeline.py /path/to/NormanEricRoberts.pdf
"""

import asyncio
import os
import sys
from pathlib import Path

# Set up path: timeline_summarizer.py uses "from server.api..." imports
# So we need the PARENT of server/ on the path (2ndOpinionMD-MVP/)
script_dir = Path(__file__).parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent  # 2ndOpinionMD-MVP/

# Add parent to path for 'server.*' imports
if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

# Change to server directory for relative imports
os.chdir(server_dir)

from openai import AsyncOpenAI
from server.eoh.timeline_summarizer import summarize_timeline_from_pdf
from server.eoh.patient_timeline_vision import PatientTimelineVision


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_norman_timeline.py /path/to/NormanEricRoberts.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Testing timeline import for Norman Eric Roberts")
    print(f"PDF: {pdf_file}")
    print(f"Condition: Myasthenia Gravis (MG)")
    print("-" * 80)
    
    # Initialize OpenAI client
    client = AsyncOpenAI()
    
    # Test question for EoHD
    question = "What are the key events in Norman's MG journey?"
    
    print(f"Question: {question}")
    print("-" * 80)
    
    # Import and summarize timeline with PatientTimelineVision
    print("Importing timeline PDF...")
    summaries = await summarize_timeline_from_pdf(
        client=client,
        question=question,
        pdf_path=str(pdf_file),
        password=None,  # Will prompt if needed
        patient_id="norman_eric_roberts",
    )
    
    print("\n" + "=" * 80)
    print("TIMELINE SUMMARY")
    print("=" * 80)
    print(summaries.timeline_summary)
    
    if summaries.meds_and_labs_snapshot:
        print("\n" + "=" * 80)
        print("MEDS & LABS SNAPSHOT")
        print("=" * 80)
        print(summaries.meds_and_labs_snapshot)
    
    if summaries.vision_path:
        print("\n" + "=" * 80)
        print("PATIENT TIMELINE VISION")
        print("=" * 80)
        print(f"Vision file: {summaries.vision_path}")
        
        # Load and inspect vision
        vision = PatientTimelineVision.load(summaries.vision_path)
        print(f"Events: {len(vision.events)}")
        print(f"Edges: {vision.count_edges()}")
        
        # Show first few events
        print("\nFirst 5 events:")
        for event_id in list(vision.events.keys())[:5]:
            event = vision.events[event_id]
            print(f"  - {event.event_id}: {event.event_type} @ {event.timestamp}")
            print(f"    {event.preview[:100]}...")
        
        # Show connascence summary by type
        connascence_counts = {}
        for event in vision.events.values():
            for conn_type, targets in event.connascence.items():
                if conn_type not in connascence_counts:
                    connascence_counts[conn_type] = 0
                connascence_counts[conn_type] += len(targets)
        
        if connascence_counts:
            print("\nConnascence summary:")
            for conn_type, count in sorted(connascence_counts.items()):
                print(f"  - {conn_type}: {count} edges")
    
    print("\n" + "=" * 80)
    print("Test complete! ✅")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

