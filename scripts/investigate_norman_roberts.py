#!/usr/bin/env python3
"""
Run EoH Detective investigation on Norman Eric Roberts case.

Usage:
    python investigate_norman_roberts.py

Or with custom question:
    python investigate_norman_roberts.py "What are the key diagnostic challenges?"

Output will stream to stdout.
"""
import asyncio
import httpx
import sys
import json
from typing import Optional

BASE_URL = "http://localhost:8000"

async def run_detective_investigation(question: Optional[str] = None):
    """
    Run a full EoH Detective investigation on the Norman Roberts case.
    """
    if question is None:
        question = (
            "Perform a comprehensive diagnostic investigation of this complex case. "
            "Focus on: 1) Major clinical arcs and inflection points, "
            "2) Diagnostic mysteries or unexplained patterns, "
            "3) Treatment decisions that diverged from typical care paths, "
            "4) Any internal contradictions in the medical record."
        )
    
    url = f"{BASE_URL}/api/rag/eoh_detective_stream"
    
    payload = {
        "q": question,
        "patient_id": "NORMAN_ROBERTS",
        "sources": "norman_eric_roberts",
        "max_steps": 6,
        "limit": 20,
        "ctx_k": 64,
        "with_llm": True,
        "use_valyu": True,
        "valyu_raw": True,
        "research": 1,
        "enable_gap": 1,
    }
    
    print("=" * 80, file=sys.stderr)
    print("🔍 EoH DETECTIVE: Norman Eric Roberts Case Investigation", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Question: {question}\n", file=sys.stderr)
    print(f"Data source: 4,223 pages from medical record", file=sys.stderr)
    print(f"Summarizer model: gpt-4.1 (1M context, 80% cap)", file=sys.stderr)
    print(f"Max investigation steps: {payload['max_steps']}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(file=sys.stderr)
    
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                
                step_buffer = ""
                
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    
                    # Parse SSE format
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_name = data.get("event", "unknown")
                            
                            # Handle different event types
                            if event_name == "start":
                                print("\n🚀 Investigation started...\n", file=sys.stderr)
                            
                            elif event_name == "detective_step_start":
                                step_id = data.get("step_id", "?")
                                kind = data.get("kind", "?")
                                step_q = data.get("q", "")
                                print(f"\n{'─' * 80}", file=sys.stderr)
                                print(f"📋 STEP {step_id}: {kind}", file=sys.stderr)
                                print(f"{'─' * 80}", file=sys.stderr)
                                print(f"Q: {step_q[:200]}...\n" if len(step_q) > 200 else f"Q: {step_q}\n", file=sys.stderr)
                            
                            elif event_name == "llm_chunk":
                                # Stream LLM output to stdout
                                chunk = data.get("text", "")
                                step_buffer += chunk
                                print(chunk, end="", flush=True)
                            
                            elif event_name == "detective_step_end":
                                step_id = data.get("step_id", "?")
                                print(f"\n\n✓ Step {step_id} complete", file=sys.stderr)
                                step_buffer = ""
                            
                            elif event_name == "citations":
                                citations = data.get("citations", [])
                                print(f"\n📚 {len(citations)} citations found", file=sys.stderr)
                            
                            elif event_name == "detective_report":
                                print("\n\n" + "=" * 80, file=sys.stderr)
                                print("📊 FINAL DETECTIVE REPORT", file=sys.stderr)
                                print("=" * 80 + "\n", file=sys.stderr)
                                report = data.get("report", "")
                                print(report)
                            
                            elif event_name == "complete":
                                elapsed = data.get("elapsed_s", 0)
                                print(f"\n\n✅ Investigation complete in {elapsed:.1f}s", file=sys.stderr)
                            
                            elif event_name == "error":
                                error = data.get("error", "Unknown error")
                                detail = data.get("detail", "")
                                print(f"\n\n❌ ERROR: {error}", file=sys.stderr)
                                if detail:
                                    print(f"   {detail}", file=sys.stderr)
                        
                        except json.JSONDecodeError as e:
                            # Not JSON data, skip
                            pass
        
        except httpx.ConnectError:
            print("\n❌ ERROR: Could not connect to server at", BASE_URL, file=sys.stderr)
            print("\nMake sure the server is running:", file=sys.stderr)
            print("  cd server && uvicorn api.app_postgres:app --reload --port 8000\n", file=sys.stderr)
            sys.exit(1)
        
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)


async def run_simple_query(question: str):
    """
    Run a simple (non-detective) query against the Norman Roberts case.
    """
    url = f"{BASE_URL}/api/rag/eoh_stream"
    
    params = {
        "q": question,
        "sources": "norman_eric_roberts",
        "with_llm": 1,
        "limit": 20,
        "ctx_k": 64,
        "debug": 0,
    }
    
    print(f"🔍 Query: {question}\n", file=sys.stderr)
    
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("GET", url, params=params) as resp:
                resp.raise_for_status()
                
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("event") == "llm_chunk":
                                print(data.get("text", ""), end="", flush=True)
                        except json.JSONDecodeError:
                            pass
                
                print("\n")
        
        except httpx.ConnectError:
            print(f"\n❌ ERROR: Could not connect to server at {BASE_URL}", file=sys.stderr)
            sys.exit(1)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run EoH Detective investigation on Norman Eric Roberts case",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full detective investigation (default)
  python investigate_norman_roberts.py

  # Custom detective investigation
  python investigate_norman_roberts.py "What were the major medication changes?"

  # Simple query (faster, single-step)
  python investigate_norman_roberts.py --simple "Summarize the major diagnoses"
        """
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Custom investigation question (optional)"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Run a simple query instead of full detective investigation"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url.rstrip("/")
    
    if args.simple:
        question = args.question or "Summarize the major clinical events in this case"
        asyncio.run(run_simple_query(question))
    else:
        asyncio.run(run_detective_investigation(args.question))


if __name__ == "__main__":
    main()

