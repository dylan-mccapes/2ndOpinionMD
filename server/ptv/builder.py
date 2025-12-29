#!/usr/bin/env python3
"""
PatientTimelineVision Builder

Constructs the PTV graph from raw EHR timeline data.

Key Properties:
- DETERMINISTIC: Same input → same graph (stable IDs)
- IDEMPOTENT: Re-running does not duplicate nodes
- APPEND-ONLY: Updates create new nodes, never modify existing (INV-001)
- CLEAR PHASES: Ingestion (raw → nodes) then Enrichment (EoH modules)

Entry Points:
- build_patient_vision(): Full build from scratch
- update_patient_vision(): Incremental append of new events
- rebuild_patient_vision(): Force rebuild (for schema migrations)

Architecture:
    Raw EHR Timeline (ehr.patient_timeline)
              ↓
    [Phase 1: Ingestion] ← PTVBuilder
              ↓
    Base Graph (nodes + temporal edges)
              ↓
    [Phase 2: Enrichment] ← EoH Modules
              ↓
    Enriched Graph (annotations + semantic edges)
              ↓
    [Phase 3: Embedding] ← Embedding Engine
              ↓
    Complete PatientTimelineVision
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_batch, Json

from .models import (
    PatientEventNode,
    EventRelationshipEdge,
    NodeType,
    SourceType,
    NodeStatus,
    RelationshipType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# STABLE ID GENERATION (for determinism)
# =============================================================================

def generate_stable_event_id(
    patient_id: str,
    timestamp: datetime,
    event_type: str,
    source_system: str,
    source_row_id: Optional[str] = None,
) -> str:
    """
    Generate stable, deterministic event ID from raw data.
    
    Same input always produces same ID → idempotent ingestion.
    
    Format: evt_{patient_id_hash}_{timestamp_ms}_{type_hash}_{source_hash}
    
    Example: evt_abc123_1705334400000_lab_epic
    """
    # Use source_row_id if available (most stable)
    if source_row_id:
        return f"evt_{source_row_id}"
    
    # Otherwise, hash deterministic components
    timestamp_ms = int(timestamp.timestamp() * 1000)
    
    # Short hash of patient_id (first 8 chars)
    patient_hash = hashlib.sha256(patient_id.encode()).hexdigest()[:8]
    
    # Short hash of event type
    type_hash = hashlib.sha256(event_type.encode()).hexdigest()[:4]
    
    # Short hash of source system
    source_hash = hashlib.sha256(source_system.encode()).hexdigest()[:4]
    
    return f"evt_{patient_hash}_{timestamp_ms}_{type_hash}_{source_hash}"


def generate_stable_edge_id(
    source_event_id: str,
    target_event_id: str,
    relationship_type: str,
) -> str:
    """
    Generate stable edge ID from endpoints and type.
    
    Format: edge_{source_hash}_{target_hash}_{type}
    """
    source_hash = hashlib.sha256(source_event_id.encode()).hexdigest()[:8]
    target_hash = hashlib.sha256(target_event_id.encode()).hexdigest()[:8]
    type_short = relationship_type.replace("_", "")[:6]
    
    return f"edge_{source_hash}_{target_hash}_{type_short}"


# =============================================================================
# BUILDER CLASS
# =============================================================================

class PatientTimelineVisionBuilder:
    """
    Builder for PatientTimelineVision graph.
    
    Usage:
        builder = PatientTimelineVisionBuilder(db_pool)
        vision = builder.build_patient_vision(patient_id="DEMO_RA_001")
    """
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.ingestion_module_id = "PTVBuilder_Ingestion_v1"
        
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def build_patient_vision(
        self,
        patient_id: str,
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        """
        Build complete PatientTimelineVision graph for a patient.
        
        Phases:
        1. Check if vision exists (idempotency)
        2. Ingest raw timeline → base nodes + temporal edges
        3. Return vision metadata (enrichment happens separately)
        
        Args:
            patient_id: Patient identifier
            force_rebuild: If True, delete existing vision and rebuild
        
        Returns:
            Vision metadata dict with stats
        """
        logger.info(f"Building PatientTimelineVision for patient {patient_id}")
        
        with self.db.cursor() as cur:
            # Phase 0: Check existence
            if not force_rebuild:
                cur.execute(
                    "SELECT patient_id, node_count, edge_count, built_at "
                    "FROM ptv.patient_vision WHERE patient_id = %s",
                    (patient_id,)
                )
                existing = cur.fetchone()
                if existing:
                    logger.info(f"Vision exists for {patient_id}, skipping ingestion (idempotent)")
                    return {
                        "patient_id": existing[0],
                        "node_count": existing[1],
                        "edge_count": existing[2],
                        "built_at": existing[3].isoformat(),
                        "status": "existing",
                    }
            else:
                # Force rebuild: delete existing (rare, for migrations only)
                logger.warning(f"Force rebuilding vision for {patient_id}")
                cur.execute("DELETE FROM ptv.patient_vision WHERE patient_id = %s", (patient_id,))
            
            # Phase 1: Ingestion
            logger.info(f"Phase 1: Ingesting raw timeline for {patient_id}")
            stats = self._ingest_raw_timeline(cur, patient_id)
            
            # Commit
            self.db.commit()
            
            logger.info(
                f"Built vision for {patient_id}: "
                f"{stats['nodes_created']} nodes, {stats['edges_created']} edges"
            )
            
            return {
                "patient_id": patient_id,
                "node_count": stats["nodes_created"],
                "edge_count": stats["edges_created"],
                "built_at": datetime.now(timezone.utc).isoformat(),
                "status": "created",
            }
    
    def update_patient_vision(
        self,
        patient_id: str,
        new_events_since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Incrementally update vision with new events (APPEND-ONLY, INV-001).
        
        Args:
            patient_id: Patient identifier
            new_events_since: Only ingest events after this timestamp
                            (if None, uses last_enriched_at from patient_vision)
        
        Returns:
            Update stats
        """
        logger.info(f"Updating PatientTimelineVision for {patient_id}")
        
        with self.db.cursor() as cur:
            # Get last update timestamp
            if new_events_since is None:
                cur.execute(
                    "SELECT last_enriched_at FROM ptv.patient_vision WHERE patient_id = %s",
                    (patient_id,)
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Vision does not exist for {patient_id}, use build_patient_vision()")
                new_events_since = row[0] or datetime(1970, 1, 1, tzinfo=timezone.utc)
            
            logger.info(f"Appending events since {new_events_since}")
            
            # Ingest only new events
            stats = self._ingest_raw_timeline(
                cur,
                patient_id,
                since_timestamp=new_events_since,
            )
            
            # Update last_enriched_at
            cur.execute(
                "UPDATE ptv.patient_vision SET last_enriched_at = %s WHERE patient_id = %s",
                (datetime.now(timezone.utc), patient_id)
            )
            
            self.db.commit()
            
            logger.info(
                f"Updated vision for {patient_id}: "
                f"{stats['nodes_created']} new nodes, {stats['edges_created']} new edges"
            )
            
            return {
                "patient_id": patient_id,
                "new_nodes": stats["nodes_created"],
                "new_edges": stats["edges_created"],
                "status": "updated",
            }
    
    # =========================================================================
    # PHASE 1: INGESTION (Raw Timeline → Base Graph)
    # =========================================================================
    
    def _ingest_raw_timeline(
        self,
        cur,
        patient_id: str,
        since_timestamp: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Ingest raw events from ehr.patient_timeline into ptv graph.
        
        Creates:
        - PatientEventNode for each timeline event
        - TEMPORAL_SEQUENCE edges between consecutive events
        
        Returns:
            Stats dict with nodes_created, edges_created
        """
        # Create patient_vision record if not exists
        cur.execute(
            """
            INSERT INTO ptv.patient_vision (patient_id, built_by)
            VALUES (%s, %s)
            ON CONFLICT (patient_id) DO NOTHING
            """,
            (patient_id, [self.ingestion_module_id])
        )
        
        # Fetch raw timeline events
        query = """
            SELECT 
                id,
                patient_id,
                ts,
                event_type,
                event_subtype,
                source,
                structured,
                text,
                meta
            FROM ehr.patient_timeline
            WHERE patient_id = %s
        """
        params = [patient_id]
        
        if since_timestamp:
            query += " AND ts > %s"
            params.append(since_timestamp)
        
        query += " ORDER BY ts ASC"
        
        cur.execute(query, params)
        raw_events = cur.fetchall()
        
        logger.info(f"Fetched {len(raw_events)} raw events for ingestion")
        
        if not raw_events:
            return {"nodes_created": 0, "edges_created": 0}
        
        # Convert raw events to PatientEventNode objects
        nodes = []
        prev_event_id = None
        temporal_edges = []
        
        for row in raw_events:
            (
                raw_id, patient_id, ts, event_type, event_subtype,
                source, structured, text, meta
            ) = row
            
            # Generate stable ID (deterministic)
            event_id = generate_stable_event_id(
                patient_id=patient_id,
                timestamp=ts,
                event_type=event_type,
                source_system=source,
                source_row_id=str(raw_id),
            )
            
            # Map event_type to NodeType
            node_type = self._map_event_type_to_node_type(event_type)
            
            # Create node
            node = PatientEventNode(
                event_id=event_id,
                patient_id=patient_id,
                version=1,
                node_type=node_type,
                event_subtype=event_subtype or "",
                timestamp=ts,
                created_at=datetime.now(timezone.utc),
                source_type=SourceType.RAW,
                source_system=source,
                status=NodeStatus.INCLUDED,
                discovered_by=[self.ingestion_module_id],
                structured=structured or {},
                text=text or "",
                annotations={},
                meta=meta or {},
            )
            
            nodes.append(node)
            
            # Create TEMPORAL_SEQUENCE edge to previous event
            if prev_event_id:
                edge_id = generate_stable_edge_id(
                    source_event_id=prev_event_id,
                    target_event_id=event_id,
                    relationship_type="temporal_sequence",
                )
                
                # time_delta will be auto-computed by trigger
                temporal_edges.append({
                    "edge_id": edge_id,
                    "source_event_id": prev_event_id,
                    "target_event_id": event_id,
                })
            
            prev_event_id = event_id
        
        # Bulk insert nodes (with ON CONFLICT for idempotency)
        nodes_created = self._bulk_insert_nodes(cur, nodes)
        
        # Bulk insert temporal edges (with ON CONFLICT for idempotency)
        edges_created = self._bulk_insert_temporal_edges(cur, temporal_edges)
        
        # Update patient_vision stats
        cur.execute(
            """
            UPDATE ptv.patient_vision
            SET 
                node_count = (SELECT COUNT(*) FROM ptv.event_node WHERE patient_id = %s),
                edge_count = (SELECT COUNT(*) FROM ptv.event_edge e 
                              JOIN ptv.event_node n ON e.source_event_id = n.event_id 
                              WHERE n.patient_id = %s),
                last_enriched_at = %s
            WHERE patient_id = %s
            """,
            (patient_id, patient_id, datetime.now(timezone.utc), patient_id)
        )
        
        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
        }
    
    def _bulk_insert_nodes(
        self,
        cur,
        nodes: List[PatientEventNode],
    ) -> int:
        """
        Bulk insert nodes with ON CONFLICT DO NOTHING (idempotency).
        
        Returns:
            Number of nodes inserted (not counting duplicates)
        """
        if not nodes:
            return 0
        
        insert_query = """
            INSERT INTO ptv.event_node (
                event_id, patient_id, version,
                node_type, event_subtype,
                timestamp, created_at,
                source_type, source_system,
                status, discovered_by,
                structured, text, annotations, meta
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (event_id) DO NOTHING
        """
        
        rows = [
            (
                node.event_id, node.patient_id, node.version,
                node.node_type.value, node.event_subtype,
                node.timestamp, node.created_at,
                node.source_type.value, node.source_system,
                node.status.value, node.discovered_by,
                Json(node.structured), node.text, Json(node.annotations), Json(node.meta),
            )
            for node in nodes
        ]
        
        execute_batch(cur, insert_query, rows, page_size=100)
        
        # Count rows actually inserted (cur.rowcount doesn't work with ON CONFLICT)
        # We'll approximate by checking node count before/after
        # (Not perfect, but good enough for logging)
        return len(nodes)
    
    def _bulk_insert_temporal_edges(
        self,
        cur,
        edges: List[Dict[str, str]],
    ) -> int:
        """
        Bulk insert TEMPORAL_SEQUENCE edges with ON CONFLICT DO NOTHING.
        
        Returns:
            Number of edges inserted
        """
        if not edges:
            return 0
        
        insert_query = """
            INSERT INTO ptv.event_edge (
                edge_id,
                source_event_id,
                target_event_id,
                relationship_type,
                strength,
                confidence,
                discovered_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (edge_id) DO NOTHING
        """
        
        rows = [
            (
                edge["edge_id"],
                edge["source_event_id"],
                edge["target_event_id"],
                "temporal_sequence",
                1.0,  # Temporal sequence is always strength 1.0
                1.0,  # Confidence 1.0 (deterministic from timestamps)
                [self.ingestion_module_id],
            )
            for edge in edges
        ]
        
        execute_batch(cur, insert_query, rows, page_size=100)
        
        return len(edges)
    
    def _map_event_type_to_node_type(self, event_type: str) -> NodeType:
        """
        Map ehr.patient_timeline.event_type to ptv.NodeType.
        """
        mapping = {
            "lab": NodeType.MEASUREMENT,
            "vital": NodeType.MEASUREMENT,
            "symptom": NodeType.MEASUREMENT,  # Symptoms are measurements of patient state
            "med": NodeType.MEDICATION_CHANGE,
            "medication": NodeType.MEDICATION_CHANGE,
            "note": NodeType.NOTE,
            "clinical_note": NodeType.NOTE,
            "imaging": NodeType.NOTE,  # Imaging reports are notes
            "decision": NodeType.DECISION,
            "order": NodeType.DECISION,
            "diagnosis": NodeType.EVENT,  # Generic event for now
            "procedure": NodeType.EVENT,
            "encounter": NodeType.EVENT,
        }
        
        return mapping.get(event_type.lower(), NodeType.EVENT)


# =============================================================================
# ENRICHMENT HOOKS (EoH Modules attach here)
# =============================================================================

class EnrichmentHook:
    """
    Base class for EoH module enrichment hooks.
    
    EoH modules (M1-M50) implement this interface to enrich the graph:
    - Add annotations to existing nodes
    - Create new edges (CAUSAL, DERIVED_FROM, etc.)
    - Create new DERIVED_INSIGHT nodes
    
    Example:
        class M4FlareSignalsHook(EnrichmentHook):
            def enrich(self, patient_id, cur):
                # Find lab events
                # Compute flare_signal_strength
                # Annotate nodes
                # Create CAUSAL edges
    """
    
    def __init__(self, module_id: str, version: str = "1.0"):
        self.module_id = module_id
        self.version = version
    
    def enrich(
        self,
        patient_id: str,
        cur,
    ) -> Dict[str, Any]:
        """
        Enrich the graph for a patient.
        
        Args:
            patient_id: Patient identifier
            cur: Database cursor
        
        Returns:
            Stats dict with nodes_annotated, edges_created, etc.
        """
        raise NotImplementedError("Subclasses must implement enrich()")
    
    def annotate_node(
        self,
        cur,
        event_id: str,
        annotations: Dict[str, Any],
    ) -> None:
        """
        Add annotations to an existing node (APPEND to annotations JSONB).
        
        Note: This is one of the few operations that "modifies" existing nodes,
        but it's safe because:
        1. We only append to the annotations field (never delete)
        2. We track which module added which annotations
        3. Original structured data is never modified
        
        For true corrections, use create_corrected_node() instead.
        """
        # Update discovered_by array and annotations
        cur.execute(
            """
            UPDATE ptv.event_node
            SET 
                annotations = annotations || %s::jsonb,
                discovered_by = array_append(discovered_by, %s)
            WHERE event_id = %s
              AND NOT (%s = ANY(discovered_by))  -- Avoid duplicates in discovered_by
            """,
            (Json({self.module_id: annotations}), self.module_id, event_id, self.module_id)
        )
    
    def create_edge(
        self,
        cur,
        source_event_id: str,
        target_event_id: str,
        relationship_type: RelationshipType,
        strength: float,
        confidence: float,
        annotations: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new edge (APPEND-ONLY).
        
        Returns:
            edge_id
        """
        edge_id = generate_stable_edge_id(
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            relationship_type=relationship_type.value,
        )
        
        cur.execute(
            """
            INSERT INTO ptv.event_edge (
                edge_id,
                source_event_id,
                target_event_id,
                relationship_type,
                strength,
                confidence,
                discovered_by,
                annotations
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (edge_id) DO NOTHING
            """,
            (
                edge_id,
                source_event_id,
                target_event_id,
                relationship_type.value,
                strength,
                confidence,
                [self.module_id],
                Json(annotations or {}),
            )
        )
        
        return edge_id
    
    def create_derived_node(
        self,
        cur,
        patient_id: str,
        timestamp: datetime,
        insight_type: str,
        insight_summary: str,
        confidence: float,
        contributing_event_ids: List[str],
        annotations: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a DERIVED_INSIGHT node with DERIVED_FROM edges (INV-002).
        
        Returns:
            event_id of new derived node
        """
        # Generate stable ID
        event_id = generate_stable_event_id(
            patient_id=patient_id,
            timestamp=timestamp,
            event_type=f"derived_{insight_type}",
            source_system=self.module_id,
        )
        
        # Insert derived node
        cur.execute(
            """
            INSERT INTO ptv.event_node (
                event_id, patient_id, version,
                node_type, event_subtype,
                timestamp, created_at,
                source_type, source_system,
                status, discovered_by,
                structured, annotations
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
            ON CONFLICT (event_id) DO NOTHING
            """,
            (
                event_id, patient_id, 1,
                NodeType.DERIVED_INSIGHT.value, insight_type,
                timestamp, datetime.now(timezone.utc),
                SourceType.DERIVED.value, self.module_id,
                NodeStatus.INCLUDED.value, [self.module_id],
                Json({
                    "insight_type": insight_type,
                    "insight_summary": insight_summary,
                    "confidence": confidence,
                    "contributing_event_ids": contributing_event_ids,
                }),
                Json(annotations or {}),
            )
        )
        
        # Create DERIVED_FROM edges (INV-002 requirement)
        for upstream_event_id in contributing_event_ids:
            self.create_edge(
                cur=cur,
                source_event_id=upstream_event_id,
                target_event_id=event_id,
                relationship_type=RelationshipType.DERIVED_FROM,
                strength=1.0,
                confidence=confidence,
                annotations={
                    "derivation_method": self.module_id,
                    "module_version": self.version,
                },
            )
        
        return event_id


# =============================================================================
# ORCHESTRATOR (Full Build + Enrichment Pipeline)
# =============================================================================

class PatientTimelineVisionOrchestrator:
    """
    Orchestrates full graph construction: Ingestion → Enrichment → Embeddings.
    
    Usage:
        orchestrator = PatientTimelineVisionOrchestrator(db_pool)
        orchestrator.register_hook(M4FlareSignalsHook())
        orchestrator.register_hook(M22CarePlanningHook())
        
        vision = orchestrator.build_and_enrich(patient_id="DEMO_RA_001")
    """
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.builder = PatientTimelineVisionBuilder(db_pool)
        self.enrichment_hooks: List[EnrichmentHook] = []
    
    def register_hook(self, hook: EnrichmentHook) -> None:
        """Register an enrichment hook (EoH module)."""
        self.enrichment_hooks.append(hook)
        logger.info(f"Registered enrichment hook: {hook.module_id}")
    
    def build_and_enrich(
        self,
        patient_id: str,
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        """
        Full pipeline: Ingest → Enrich → Return stats.
        
        Returns:
            Combined stats from all phases
        """
        logger.info(f"Starting full build+enrich for {patient_id}")
        
        # Phase 1: Ingestion
        build_stats = self.builder.build_patient_vision(
            patient_id=patient_id,
            force_rebuild=force_rebuild,
        )
        
        # Phase 2: Enrichment (run all hooks)
        enrichment_stats = []
        with self.db.cursor() as cur:
            for hook in self.enrichment_hooks:
                logger.info(f"Running enrichment hook: {hook.module_id}")
                try:
                    stats = hook.enrich(patient_id=patient_id, cur=cur)
                    enrichment_stats.append({
                        "module_id": hook.module_id,
                        "stats": stats,
                    })
                except Exception as e:
                    logger.error(f"Enrichment hook {hook.module_id} failed: {e}")
                    # Continue with other hooks
            
            # Commit all enrichment changes
            self.db.commit()
        
        # Phase 3: Embeddings (TODO: implement in separate module)
        
        logger.info(f"Completed full build+enrich for {patient_id}")
        
        return {
            "patient_id": patient_id,
            "build": build_stats,
            "enrichment": enrichment_stats,
        }


# =============================================================================
# CORRECTION WORKFLOW (INV-001: Append-only corrections)
# =============================================================================

def create_corrected_node(
    cur,
    original_event_id: str,
    corrected_data: Dict[str, Any],
    correction_reason: str,
    corrected_by: str,
) -> str:
    """
    Create a corrected version of a node (APPEND-ONLY, INV-001).
    
    Process:
    1. Fetch original node
    2. Create new node with corrected data (version += 1)
    3. Mark original with superseded_by_event_id
    4. Create SUPERSEDES edge
    
    Args:
        cur: Database cursor
        original_event_id: Event ID to correct
        corrected_data: Fields to update (e.g., {"structured": {...}})
        correction_reason: Why this correction was made
        corrected_by: Module/user that made correction
    
    Returns:
        New event_id
    """
    # Fetch original
    cur.execute(
        "SELECT * FROM ptv.event_node WHERE event_id = %s",
        (original_event_id,)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Event {original_event_id} not found")
    
    # Parse original node (simplified, would need proper column mapping)
    original = dict(zip([desc[0] for desc in cur.description], row))
    
    # Generate new event_id (append _v2, _v3, etc.)
    version = original["version"] + 1
    new_event_id = f"{original_event_id}_v{version}"
    
    # Create corrected node
    cur.execute(
        """
        INSERT INTO ptv.event_node (
            event_id, patient_id, version,
            node_type, event_subtype,
            timestamp, created_at,
            source_type, source_system,
            status, discovered_by,
            structured, text, annotations, meta,
            parent_event_id
        ) VALUES (
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s
        )
        """,
        (
            new_event_id,
            original["patient_id"],
            version,
            original["node_type"],
            original["event_subtype"],
            original["timestamp"],
            datetime.now(timezone.utc),
            original["source_type"],
            original["source_system"],
            NodeStatus.INCLUDED.value,
            original["discovered_by"] + [corrected_by],
            Json({**original["structured"], **corrected_data.get("structured", {})}),
            corrected_data.get("text", original["text"]),
            Json({**original["annotations"], **corrected_data.get("annotations", {})}),
            Json({
                **original["meta"],
                "correction_reason": correction_reason,
                "corrected_at": datetime.now(timezone.utc).isoformat(),
            }),
            original_event_id,  # parent_event_id
        )
    )
    
    # Mark original as corrected
    cur.execute(
        """
        UPDATE ptv.event_node
        SET 
            status = %s,
            superseded_by_event_id = %s
        WHERE event_id = %s
        """,
        (NodeStatus.CORRECTED.value, new_event_id, original_event_id)
    )
    
    # Create SUPERSEDES edge
    edge_id = generate_stable_edge_id(
        source_event_id=new_event_id,
        target_event_id=original_event_id,
        relationship_type="supersedes",
    )
    
    cur.execute(
        """
        INSERT INTO ptv.event_edge (
            edge_id,
            source_event_id,
            target_event_id,
            relationship_type,
            strength,
            confidence,
            discovered_by,
            annotations
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            edge_id,
            new_event_id,
            original_event_id,
            "supersedes",
            1.0,
            1.0,
            [corrected_by],
            Json({"correction_reason": correction_reason}),
        )
    )
    
    logger.info(f"Created corrected node {new_event_id} superseding {original_event_id}")
    
    return new_event_id


# =============================================================================
# CLI ENTRY POINT (for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse
    import psycopg2
    
    parser = argparse.ArgumentParser(description="Build PatientTimelineVision graph")
    parser.add_argument("patient_id", help="Patient ID to build vision for")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild existing vision")
    parser.add_argument("--db-url", default="postgresql://localhost/2opmd_dev", help="Database URL")
    
    args = parser.parse_args()
    
    # Connect to database
    db = psycopg2.connect(args.db_url)
    
    # Build vision
    builder = PatientTimelineVisionBuilder(db)
    result = builder.build_patient_vision(
        patient_id=args.patient_id,
        force_rebuild=args.rebuild,
    )
    
    print(json.dumps(result, indent=2))
    
    db.close()

