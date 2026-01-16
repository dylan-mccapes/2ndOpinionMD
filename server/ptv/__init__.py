"""
PatientTimelineVision (PTV) Module

Authoritative knowledge graph for patient timelines.

Key Classes:
- PatientTimelineVisionBuilder: Ingest raw timeline → base graph
- EnrichmentHook: Base class for EoH module hooks
- PatientTimelineVisionOrchestrator: Full pipeline (ingest + enrich)

Usage:
    from server.ptv import PatientTimelineVisionBuilder
    
    builder = PatientTimelineVisionBuilder(db_pool)
    vision = builder.build_patient_vision(patient_id="DEMO_RA_001")
"""

from .builder import (
    PatientTimelineVisionBuilder,
    EnrichmentHook,
    PatientTimelineVisionOrchestrator,
    generate_stable_event_id,
    generate_stable_edge_id,
    create_corrected_node,
)

from .models import (
    PatientEventNode,
    EventRelationshipEdge,
    MeasurementNode,
    MedicationChangeNode,
    RiskSignalNode,
    DerivedInsightNode,
    NodeType,
    SourceType,
    NodeStatus,
    RelationshipType,
)

__all__ = [
    # Builder
    "PatientTimelineVisionBuilder",
    "EnrichmentHook",
    "PatientTimelineVisionOrchestrator",
    "generate_stable_event_id",
    "generate_stable_edge_id",
    "create_corrected_node",
    
    # Models
    "PatientEventNode",
    "EventRelationshipEdge",
    "MeasurementNode",
    "MedicationChangeNode",
    "RiskSignalNode",
    "DerivedInsightNode",
    
    # Enums
    "NodeType",
    "SourceType",
    "NodeStatus",
    "RelationshipType",
]

