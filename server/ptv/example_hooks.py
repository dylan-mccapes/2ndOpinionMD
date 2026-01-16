#!/usr/bin/env python3
"""
Example Enrichment Hooks

Demonstrates how EoH modules integrate with PatientTimelineVision.

These are REFERENCE IMPLEMENTATIONS showing the pattern.
Real EoH modules (M1-M50) will implement similar hooks.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

from .builder import EnrichmentHook
from .models import RelationshipType


# =============================================================================
# EXAMPLE 1: Simple Annotation Hook (M1-style)
# =============================================================================

class ExampleTerrainHook(EnrichmentHook):
    """
    Example: M1 Terrain Analysis Hook
    
    Adds terrain_band annotations to all events based on temporal patterns.
    """
    
    def __init__(self):
        super().__init__(module_id="M1_Terrain_Example", version="1.0")
    
    def enrich(self, patient_id: str, cur) -> Dict[str, Any]:
        """
        Annotate all events with terrain_band classification.
        """
        # Fetch all included nodes
        cur.execute("""
            SELECT event_id, timestamp, structured
            FROM ptv.event_node
            WHERE patient_id = %s
              AND status = 'included'
            ORDER BY timestamp
        """, (patient_id,))
        
        events = cur.fetchall()
        nodes_annotated = 0
        
        for event_id, timestamp, structured in events:
            # Simplified terrain logic (real M1 is more complex)
            terrain_band = self._classify_terrain(structured)
            
            # Annotate node
            self.annotate_node(
                cur=cur,
                event_id=event_id,
                annotations={
                    "terrain_band": terrain_band,
                    "baseline_deviation": 0.0,  # Placeholder
                }
            )
            nodes_annotated += 1
        
        # Create TEMPORAL_WINDOW edges (group events in 7-day windows)
        edges_created = self._create_temporal_windows(cur, patient_id, events)
        
        return {
            "nodes_annotated": nodes_annotated,
            "temporal_window_edges_created": edges_created,
        }
    
    def _classify_terrain(self, structured: Dict[str, Any]) -> str:
        """Simplified terrain classification"""
        if not structured:
            return "baseline"
        
        # Example: if lab value is elevated, classify as elevated_chronic
        value = structured.get("value")
        if value and isinstance(value, (int, float)) and value > 50:
            return "elevated_chronic"
        
        return "baseline"
    
    def _create_temporal_windows(self, cur, patient_id: str, events: List) -> int:
        """Create TEMPORAL_WINDOW edges for events within 7 days of each other"""
        edges_created = 0
        
        for i, (event_id_i, ts_i, _) in enumerate(events):
            for event_id_j, ts_j, _ in events[i+1:]:
                # If within 7 days, create window edge
                if abs((ts_j - ts_i).days) <= 7:
                    try:
                        self.create_edge(
                            cur=cur,
                            source_event_id=event_id_i,
                            target_event_id=event_id_j,
                            relationship_type=RelationshipType.TEMPORAL_WINDOW,
                            strength=0.7,
                            confidence=1.0,
                            annotations={"window_size_days": 7}
                        )
                        edges_created += 1
                    except:
                        pass  # Edge may already exist
        
        return edges_created


# =============================================================================
# EXAMPLE 2: Causal Edge Creation Hook (M4-style)
# =============================================================================

class ExampleFlareSignalsHook(EnrichmentHook):
    """
    Example: M4 Flare Signals Hook
    
    1. Annotates labs with flare_signal_strength
    2. Creates CAUSAL edges to downstream treatment changes
    """
    
    def __init__(self):
        super().__init__(module_id="M4_FlareSignals_Example", version="1.0")
    
    def enrich(self, patient_id: str, cur) -> Dict[str, Any]:
        """
        Find inflammatory markers, compute signal strength, create causal edges.
        """
        # Step 1: Find inflammatory marker events
        cur.execute("""
            SELECT event_id, timestamp, structured
            FROM ptv.event_node
            WHERE patient_id = %s
              AND node_type = 'measurement'
              AND status = 'included'
              AND (
                  event_subtype ILIKE '%CRP%' 
                  OR event_subtype ILIKE '%ESR%'
                  OR structured->>'test_name' ILIKE '%CRP%'
                  OR structured->>'test_name' ILIKE '%ESR%'
              )
            ORDER BY timestamp
        """, (patient_id,))
        
        inflammatory_markers = cur.fetchall()
        nodes_annotated = 0
        edges_created = 0
        
        for event_id, timestamp, structured in inflammatory_markers:
            # Step 2: Compute flare signal strength
            signal_strength = self._compute_signal_strength(structured)
            
            if signal_strength > 0.5:
                # Step 3: Annotate node
                self.annotate_node(
                    cur=cur,
                    event_id=event_id,
                    annotations={
                        "flare_signal_strength": signal_strength,
                        "signal_components": {
                            "marker_elevation": True,
                            "trend": "increasing",
                        }
                    }
                )
                nodes_annotated += 1
                
                # Step 4: Find downstream medication changes (within 14 days)
                cur.execute("""
                    SELECT event_id
                    FROM ptv.event_node
                    WHERE patient_id = %s
                      AND node_type = 'medication_change'
                      AND timestamp > %s
                      AND timestamp < %s + INTERVAL '14 days'
                      AND status = 'included'
                """, (patient_id, timestamp, timestamp))
                
                for (target_event_id,) in cur.fetchall():
                    # Step 5: Create CAUSAL edge
                    try:
                        self.create_edge(
                            cur=cur,
                            source_event_id=event_id,
                            target_event_id=target_event_id,
                            relationship_type=RelationshipType.CAUSAL_LIKELY,
                            strength=0.85,
                            confidence=0.78,
                            annotations={
                                "causal_mechanism": "inflammatory marker elevation triggered treatment adjustment",
                                "time_to_action_days": (datetime.fromisoformat(str(timestamp)) - datetime.fromisoformat(str(timestamp))).days,
                            }
                        )
                        edges_created += 1
                    except:
                        pass  # Edge may already exist
        
        return {
            "nodes_annotated": nodes_annotated,
            "causal_edges_created": edges_created,
        }
    
    def _compute_signal_strength(self, structured: Dict[str, Any]) -> float:
        """
        Simplified flare signal calculation.
        Real M4 uses sophisticated ML models.
        """
        value = structured.get("value")
        if not value or not isinstance(value, (int, float)):
            return 0.0
        
        # Simple threshold-based scoring
        if value > 100:
            return 0.95
        elif value > 50:
            return 0.85
        elif value > 20:
            return 0.65
        else:
            return 0.3


# =============================================================================
# EXAMPLE 3: Derived Node Creation Hook (M5-style)
# =============================================================================

class ExampleFlareWindowingHook(EnrichmentHook):
    """
    Example: M5 Flare Windowing Hook
    
    Creates DERIVED_INSIGHT nodes representing flare episodes.
    Links upstream events with DERIVED_FROM edges.
    """
    
    def __init__(self):
        super().__init__(module_id="M5_FlareWindowing_Example", version="1.0")
    
    def enrich(self, patient_id: str, cur) -> Dict[str, Any]:
        """
        Detect flare windows and create composite DERIVED_INSIGHT nodes.
        """
        # Step 1: Find high-signal events (flare_signal_strength > 0.7)
        cur.execute("""
            SELECT event_id, timestamp
            FROM ptv.event_node
            WHERE patient_id = %s
              AND status = 'included'
              AND annotations->'M4_FlareSignals_Example'->>'flare_signal_strength' IS NOT NULL
              AND (annotations->'M4_FlareSignals_Example'->>'flare_signal_strength')::float > 0.7
            ORDER BY timestamp
        """, (patient_id,))
        
        high_signal_events = cur.fetchall()
        
        if not high_signal_events:
            return {"flare_episodes_created": 0}
        
        # Step 2: Group events into windows (simple: group events within 14 days)
        windows = self._group_into_windows(high_signal_events, window_days=14)
        
        derived_nodes_created = 0
        
        for window in windows:
            if len(window) < 2:
                continue  # Skip single-event windows
            
            # Step 3: Create DERIVED_INSIGHT node for flare episode
            window_start = window[0][1]  # timestamp of first event
            window_end = window[-1][1]   # timestamp of last event
            contributing_event_ids = [event_id for event_id, _ in window]
            
            derived_event_id = self.create_derived_node(
                cur=cur,
                patient_id=patient_id,
                timestamp=window_start,
                insight_type="flare_episode",
                insight_summary=f"Flare episode with {len(window)} high-signal events over {(window_end - window_start).days} days",
                confidence=0.88,
                contributing_event_ids=contributing_event_ids,
                annotations={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "severity": "moderate",
                    "constituent_count": len(window),
                }
            )
            
            derived_nodes_created += 1
        
        return {
            "flare_episodes_created": derived_nodes_created,
            "total_high_signal_events": len(high_signal_events),
        }
    
    def _group_into_windows(self, events: List, window_days: int) -> List[List]:
        """
        Group events into temporal windows.
        
        Simple algorithm: events within window_days of each other go in same window.
        """
        if not events:
            return []
        
        windows = []
        current_window = [events[0]]
        
        for event in events[1:]:
            event_id, timestamp = event
            last_timestamp = current_window[-1][1]
            
            if (timestamp - last_timestamp).days <= window_days:
                current_window.append(event)
            else:
                # Start new window
                windows.append(current_window)
                current_window = [event]
        
        # Add final window
        if current_window:
            windows.append(current_window)
        
        return windows


# =============================================================================
# EXAMPLE 4: Decision Node Creation Hook (M22-style)
# =============================================================================

class ExampleCarePlanningHook(EnrichmentHook):
    """
    Example: M22 Care Planning Hook
    
    Creates DECISION nodes and CARE_PLAN_LINK edges.
    """
    
    def __init__(self):
        super().__init__(module_id="M22_CarePlanning_Example", version="1.0")
    
    def enrich(self, patient_id: str, cur) -> Dict[str, Any]:
        """
        Detect implicit treatment decisions and create explicit DECISION nodes.
        """
        # Find medication changes (these are implicit decisions)
        cur.execute("""
            SELECT event_id, timestamp, structured
            FROM ptv.event_node
            WHERE patient_id = %s
              AND node_type = 'medication_change'
              AND status = 'included'
            ORDER BY timestamp
        """, (patient_id,))
        
        med_changes = cur.fetchall()
        decision_nodes_created = 0
        care_plan_edges_created = 0
        
        for med_event_id, timestamp, structured in med_changes:
            # Create explicit DECISION node
            drug_name = structured.get("drug_name", "unknown")
            action = structured.get("action", "change")
            
            decision_event_id = self.create_derived_node(
                cur=cur,
                patient_id=patient_id,
                timestamp=timestamp,
                insight_type="treatment_decision",
                insight_summary=f"Decision to {action} {drug_name}",
                confidence=0.90,
                contributing_event_ids=[med_event_id],
                annotations={
                    "decision_type": "treatment_change",
                    "drug_name": drug_name,
                    "action": action,
                }
            )
            
            decision_nodes_created += 1
            
            # Create CARE_PLAN_LINK edge from decision to medication change
            self.create_edge(
                cur=cur,
                source_event_id=decision_event_id,
                target_event_id=med_event_id,
                relationship_type=RelationshipType.CARE_PLAN_LINK,
                strength=1.0,
                confidence=0.95,
                annotations={
                    "plan_component": "medication_management",
                }
            )
            care_plan_edges_created += 1
        
        return {
            "decision_nodes_created": decision_nodes_created,
            "care_plan_edges_created": care_plan_edges_created,
        }


# =============================================================================
# REGISTRY (for easy testing)
# =============================================================================

EXAMPLE_HOOKS = {
    "terrain": ExampleTerrainHook,
    "flare_signals": ExampleFlareSignalsHook,
    "flare_windowing": ExampleFlareWindowingHook,
    "care_planning": ExampleCarePlanningHook,
}


def get_example_hook(name: str) -> EnrichmentHook:
    """Get an example hook by name"""
    hook_class = EXAMPLE_HOOKS.get(name)
    if not hook_class:
        raise ValueError(f"Unknown hook: {name}. Available: {list(EXAMPLE_HOOKS.keys())}")
    return hook_class()


# =============================================================================
# CLI FOR TESTING
# =============================================================================

if __name__ == "__main__":
    import argparse
    import psycopg2
    from .builder import PatientTimelineVisionOrchestrator
    
    parser = argparse.ArgumentParser(description="Test enrichment hooks")
    parser.add_argument("patient_id", help="Patient ID")
    parser.add_argument("--hooks", nargs="+", choices=list(EXAMPLE_HOOKS.keys()),
                      default=["terrain", "flare_signals"],
                      help="Which hooks to run")
    parser.add_argument("--db-url", default="postgresql://localhost/2opmd_dev")
    
    args = parser.parse_args()
    
    # Connect
    db = psycopg2.connect(args.db_url)
    
    # Create orchestrator
    orchestrator = PatientTimelineVisionOrchestrator(db)
    
    # Register selected hooks
    for hook_name in args.hooks:
        hook = get_example_hook(hook_name)
        orchestrator.register_hook(hook)
        print(f"Registered: {hook.module_id}")
    
    # Run full pipeline
    result = orchestrator.build_and_enrich(patient_id=args.patient_id)
    
    print("\nResults:")
    print(f"Patient: {result['patient_id']}")
    print(f"Build: {result['build']}")
    print(f"Enrichment:")
    for module_result in result['enrichment']:
        print(f"  - {module_result['module_id']}: {module_result['stats']}")
    
    db.close()

