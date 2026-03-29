"""
Timeline Enrichment Synthesis Agent

This agent performs high-context graph enrichment after gap retrieval.
It synthesizes:
- New connascence edges
- Event metadata corrections
- Graph structure improvements

Design: High context (90% cap), judgment-based, opportunistic.
"""

import json
import logging
import textwrap
from typing import Any, Dict, List

from server.api.stream_config import EOH_TIMELINE_SUMMARIZER_MODEL
from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.eoh.timeline_summarizer import (
    _safe_get_choice_content,
    chat_completion_async,
    DateTimeJSONEncoder,
)

logger = logging.getLogger(__name__)


TIMELINE_ENRICHMENT_SYNTHESIS_SYSTEM_PROMPT = textwrap.dedent("""
    You are a precise timeline enrichment synthesis agent (GPT-5.1 equivalent).
    
    Your task: Synthesize graph enrichments after gap retrieval, using high context.
    
    **What you receive:**
    - patient_timeline_vision: Current graph state
    - gap_analysis: What the gap agent identified
    - gap_retrieval_results: Additional events/rows retrieved via TS queries
    - timeline_snapshot: High-level event summary
    
    **What you output (JSON):**
    ```json
    {
      "enrichment_summary": "High-level summary of what changed",
      "new_edges": [
        {
          "source_event_id": "...",
          "target_event_id": "...",
          "connascence_type": "temporal|diagnostic|treatment|causal|lab_trend|symptom_cluster",
          "strength": 0.0-1.0,
          "reasoning": "Why this edge is correct"
        }
      ],
      "metadata_updates": [
        {
          "event_id": "...",
          "updates": {"timestamp": "2023-05-15", "annotations": {...}},
          "reasoning": "Why this correction is necessary"
        }
      ],
      "graph_quality_assessment": {
        "before_edges": 0,
        "after_edges": 100,
        "coverage": "good|fair|poor",
        "remaining_gaps": "Description of what's still missing"
      }
    }
    ```
    
    **Instructions:**
    1. Review current graph + gap analysis + retrieved results.
    2. Infer new connascence edges based on full context (high confidence only).
    3. Correct obviously wrong metadata (timestamps, types, etc).
    4. Assess graph quality honestly (don't overstate improvements).
    5. Use judgment: what would a competent operator do?
    
    **Connascence Types (Rubric):**
    - **temporal**: Events within 7-30 days (strength by proximity)
    - **diagnostic**: Lab/symptom supports diagnosis (strength by directness)
    - **treatment**: Medication → response within 30 days (strength by causality)
    - **causal**: Direct causation (procedure → complication, med → adverse event)
    - **lab_trend**: Same test over time showing progression
    - **symptom_cluster**: Co-occurring symptoms forming recognized pattern
    
    **Design Principle:**
    - Like cells: fix what's obviously wrong, maintain homeostasis
    - Opportunistic: don't force perfection
    - Honest: if context is insufficient, say so
    - Judgment-based: precision over completeness
    
    **Context Budget:**
    You have high context (90% cap). Use it for synthesis, not exhaustive enumeration.
""")


async def synthesize_timeline_enrichment(
    client: Any,
    patient_timeline_vision: PatientTimelineVision,
    gap_analysis: Dict[str, Any],
    gap_retrieval_results: List[Dict[str, Any]],
    timeline_snapshot: Dict[str, Any],
    patient_id: str,
) -> Dict[str, Any]:
    """
    Synthesize graph enrichments using high context after gap retrieval.
    
    Args:
        client: OpenAI async client
        patient_timeline_vision: Current graph state (before enrichment)
        gap_analysis: Output from gap agent
        gap_retrieval_results: Additional rows retrieved via TS queries
        timeline_snapshot: High-level event summary
        patient_id: Patient ID for logging
    
    Returns:
        Enrichment synthesis report with new_edges, metadata_updates, quality assessment
    """
    print(f"\n{'='*80}")
    print(f"TIMELINE ENRICHMENT SYNTHESIS: {patient_id}")
    print(f"{'='*80}")
    print(f"Input state:")
    print(f"  Current events: {len(patient_timeline_vision.events)}")
    print(f"  Current edges: {patient_timeline_vision.count_edges()}")
    print(f"  Gap retrieval results: {len(gap_retrieval_results)} rows")
    print(f"  Opportunistic edges from gap analysis: {len(gap_analysis.get('opportunistic_edges', []))}")
    
    # Prepare compact vision (cap at 90% of context budget ~90K tokens for GPT-4)
    # Rough estimate: 1 token ~= 4 chars, so 90K tokens ~= 360K chars
    # Reserve ~100K chars for vision, ~150K for gap results, ~50K for prompts/output
    
    MAX_VISION_CHARS = 100000
    MAX_GAP_RESULTS_CHARS = 150000
    
    # Compact vision
    compact_vision = {
        "patient_id": patient_timeline_vision.patient_id,
        "event_count": len(patient_timeline_vision.events),
        "edge_count": patient_timeline_vision.count_edges(),
        "events": [],
        "edges": [],
    }
    
    vision_chars = 0
    for e in patient_timeline_vision.events.values():
        event_dict = {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "timestamp": e.timestamp,
            "preview": e.preview[:200],
            "discovered_by": e.discovered_by,
        }
        event_str = json.dumps(event_dict)
        if vision_chars + len(event_str) > MAX_VISION_CHARS:
            break
        compact_vision["events"].append(event_dict)
        vision_chars += len(event_str)
    
    for event in patient_timeline_vision.events.values():
        for conn_type, targets in event.connascence.items():
            for target_id in targets:
                edge_dict = {
                    "from": event.event_id,
                    "to": target_id,
                    "type": conn_type,
                }
                edge_str = json.dumps(edge_dict)
                if vision_chars + len(edge_str) > MAX_VISION_CHARS:
                    break
                compact_vision["edges"].append(edge_dict)
                vision_chars += len(edge_str)
    
    print(f"  Compact vision: {len(compact_vision['events'])} events, {len(compact_vision['edges'])} edges (~{vision_chars} chars)")
    
    # Compact gap results
    compact_gap_results = []
    gap_chars = 0
    for r in gap_retrieval_results:
        result_dict = {
            "id": str(r.get("id", "")),
            "event_type": r.get("event_type", ""),
            "ts": str(r.get("ts", "")),
            "title": r.get("title", "")[:150],
            "text": (r.get("text") or "")[:800],
        }
        result_str = json.dumps(result_dict)
        if gap_chars + len(result_str) > MAX_GAP_RESULTS_CHARS:
            break
        compact_gap_results.append(result_dict)
        gap_chars += len(result_str)
    
    print(f"  Compact gap results: {len(compact_gap_results)} rows (~{gap_chars} chars)")
    
    payload = {
        "patient_id": patient_id,
        "patient_timeline_vision": compact_vision,
        "gap_analysis": gap_analysis,
        "gap_retrieval_results": compact_gap_results,
        "timeline_snapshot": timeline_snapshot,
    }
    
    messages = [
        {"role": "system", "content": TIMELINE_ENRICHMENT_SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, cls=DateTimeJSONEncoder)},
    ]
    
    print(f"\nCalling timeline enrichment synthesis agent (high context)...")
    
    try:
        resp = await chat_completion_async(
            client=client,
            model=EOH_TIMELINE_SUMMARIZER_MODEL,
            messages=messages,
            max_tokens=8192,  # High token budget for synthesis
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        
        raw_content = _safe_get_choice_content(resp)
        result = json.loads(raw_content)
        
        print(f"\nSynthesis complete:")
        print(f"  New edges: {len(result.get('new_edges', []))}")
        print(f"  Metadata updates: {len(result.get('metadata_updates', []))}")
        
        quality = result.get("graph_quality_assessment", {})
        print(f"  Quality assessment:")
        print(f"    Before edges: {quality.get('before_edges', 0)}")
        print(f"    After edges: {quality.get('after_edges', 0)}")
        print(f"    Coverage: {quality.get('coverage', 'unknown')}")
        print(f"    Remaining gaps: {quality.get('remaining_gaps', 'N/A')[:150]}")
        
        print(f"\n  Summary: {result.get('enrichment_summary', 'N/A')[:300]}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse enrichment synthesis output: {e}")
        print(f"\n⚠️  Enrichment synthesis JSON parse failed: {e}")
        return {
            "enrichment_summary": "JSON parse failure",
            "new_edges": [],
            "metadata_updates": [],
            "graph_quality_assessment": {
                "before_edges": patient_timeline_vision.count_edges(),
                "after_edges": patient_timeline_vision.count_edges(),
                "coverage": "unknown",
                "remaining_gaps": "Synthesis failed",
            },
        }
    except Exception as e:
        logger.error(f"Enrichment synthesis failed: {e}")
        print(f"\n⚠️  Enrichment synthesis error: {e}")
        return {
            "enrichment_summary": f"Error: {e}",
            "new_edges": [],
            "metadata_updates": [],
            "graph_quality_assessment": {
                "before_edges": patient_timeline_vision.count_edges(),
                "after_edges": patient_timeline_vision.count_edges(),
                "coverage": "unknown",
                "remaining_gaps": "Synthesis error",
            },
        }

