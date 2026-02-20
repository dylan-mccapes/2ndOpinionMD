"""
Timeline Enrichment Gap Agent

This agent analyzes the current PatientTimelineVision graph and identifies:
- Where connascence edges are missing or weak
- Which events need deeper retrieval
- What TS queries would help enrich the graph

Design: Opportunistic, honest, judgment-based (like cells).
Constraint: No embeddings (cost).
"""

import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

from server.api.stream_config import EOH_TIMELINE_SUMMARIZER_MODEL
from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.eoh.timeline_summarizer import (
    _safe_get_choice_content,
    chat_completion_async,
    DateTimeJSONEncoder,
)

logger = logging.getLogger(__name__)


TIMELINE_ENRICHMENT_GAP_SYSTEM_PROMPT = textwrap.dedent("""
    You are a precise timeline enrichment gap analysis agent (GPT-5.1 equivalent).
    
    Your task: Analyze a patient timeline graph (PatientTimelineVision) and identify gaps
    where additional retrieval or connascence inference would meaningfully improve the graph.
    
    **What you receive:**
    - patient_timeline_vision: Current graph state (events, edges, metadata)
    - timeline_snapshot: High-level event counts and examples
    - existing_context: Events already retrieved during timeline summarization
    
    **What you output (JSON):**
    ```json
    {
      "needs_enrichment": true/false,
      "reasoning": "Why enrichment is needed (or not)",
      "opportunistic_edges": [
        {
          "source_event_id": "...",
          "target_event_id": "...",
          "connascence_type": "temporal|diagnostic|treatment|causal|lab_trend|symptom_cluster",
          "strength": 0.0-1.0,
          "reasoning": "Why this edge is obvious from existing context"
        }
      ],
      "gap_queries": {
        "ts_terms": ["term1", "term2"],
        "event_ids": ["event_123", "event_456"],
        "reasoning": "Why these queries would help"
      },
      "remediation_notes": [
        {
          "event_id": "...",
          "issue": "Wrong timestamp/missing metadata/etc",
          "fix": "What should change"
        }
      ]
    }
    ```
    
    **Instructions:**
    1. Review the current graph (events, edges, metadata).
    2. Identify obvious connascence from existing context (add to opportunistic_edges).
    3. Identify gaps where more retrieval would help (add to gap_queries).
    4. Identify obviously incorrect data (add to remediation_notes).
    5. Be honest: if the graph is good enough, say needs_enrichment=false.
    6. Use judgment: what would a competent operator do?
    
    **Constraints:**
    - Opportunistic only (don't force perfection)
    - Honest assessment (don't hallucinate gaps)
    - Judgment-based (like cells maintaining homeostasis)
    
    **Example reasoning:**
    - "MG diagnosis event links to AChR antibody lab (diagnostic connascence, strength 0.9)"
    - "Need TS query for 'pyridostigmine' to find medication response events"
    - "Event event_0123 has timestamp 'unknown' but context suggests 2023-05-15"
""")


async def analyze_timeline_enrichment_gaps(
    client: Any,
    patient_timeline_vision: PatientTimelineVision,
    timeline_snapshot: Dict[str, Any],
    existing_context: List[Dict[str, Any]],
    patient_id: str,
) -> Dict[str, Any]:
    """
    Analyze PatientTimelineVision and identify enrichment opportunities.
    
    Args:
        client: OpenAI async client
        patient_timeline_vision: Current graph state
        timeline_snapshot: High-level event counts/examples
        existing_context: Events already retrieved during summarization
        patient_id: Patient ID for logging
    
    Returns:
        Gap analysis report with opportunistic_edges, gap_queries, remediation_notes
    """
    print(f"\n{'='*80}")
    print(f"TIMELINE ENRICHMENT GAP ANALYSIS: {patient_id}")
    print(f"{'='*80}")
    print(f"Current graph state:")
    print(f"  Events: {len(patient_timeline_vision.events)}")
    print(f"  Edges: {patient_timeline_vision.count_edges()}")
    print(f"  Existing context rows: {len(existing_context)}")
    
    # Prepare compact vision for LLM (events + edges only, no full text)
    compact_vision = {
        "patient_id": patient_timeline_vision.patient_id,
        "event_count": len(patient_timeline_vision.events),
        "edge_count": patient_timeline_vision.count_edges(),
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "preview": e.preview[:100],  # First 100 chars only
                "discovered_by": e.discovered_by,
            }
            for e in list(patient_timeline_vision.events.values())[:200]  # Cap at 200 events
        ],
        "edges": [
            {
                "source_event_id": edge.source_event_id,
                "target_event_id": edge.target_event_id,
                "connascence_type": edge.connascence_type,
                "strength": edge.strength,
            }
            for edge in patient_timeline_vision.edges[:100]  # Cap at 100 edges
        ],
    }
    
    # Prepare compact context (title + snippet only)
    compact_context = [
        {
            "id": str(r.get("id", "")),
            "event_type": r.get("event_type", ""),
            "ts": str(r.get("ts", "")),
            "title": r.get("title", "")[:100],
            "snippet": (r.get("text") or r.get("snippet") or "")[:300],
        }
        for r in existing_context[:50]  # Cap at 50 context rows
    ]
    
    payload = {
        "patient_id": patient_id,
        "patient_timeline_vision": compact_vision,
        "timeline_snapshot": timeline_snapshot,
        "existing_context": compact_context,
    }
    
    messages = [
        {"role": "system", "content": TIMELINE_ENRICHMENT_GAP_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, cls=DateTimeJSONEncoder)},
    ]
    
    print(f"\nCalling timeline enrichment gap agent...")
    
    try:
        resp = await chat_completion_async(
            client=client,
            model=EOH_TIMELINE_SUMMARIZER_MODEL,
            messages=messages,
            max_tokens=4096,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        
        raw_content = _safe_get_choice_content(resp)
        result = json.loads(raw_content)
        
        print(f"\nGap analysis complete:")
        print(f"  Needs enrichment: {result.get('needs_enrichment', False)}")
        print(f"  Opportunistic edges found: {len(result.get('opportunistic_edges', []))}")
        print(f"  Gap queries (TS terms): {len(result.get('gap_queries', {}).get('ts_terms', []))}")
        print(f"  Gap queries (Event IDs): {len(result.get('gap_queries', {}).get('event_ids', []))}")
        print(f"  Remediation notes: {len(result.get('remediation_notes', []))}")
        print(f"  Reasoning: {result.get('reasoning', 'N/A')[:200]}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse gap analysis output: {e}")
        print(f"\n⚠️  Gap analysis JSON parse failed: {e}")
        return {
            "needs_enrichment": False,
            "reasoning": "JSON parse failure",
            "opportunistic_edges": [],
            "gap_queries": {"ts_terms": [], "event_ids": [], "reasoning": ""},
            "remediation_notes": [],
        }
    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        print(f"\n⚠️  Gap analysis error: {e}")
        return {
            "needs_enrichment": False,
            "reasoning": f"Error: {e}",
            "opportunistic_edges": [],
            "gap_queries": {"ts_terms": [], "event_ids": [], "reasoning": ""},
            "remediation_notes": [],
        }

