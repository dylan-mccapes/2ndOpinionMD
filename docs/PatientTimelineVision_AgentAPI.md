# PatientTimelineVision Agent API

**Version:** 1.0  
**Metaphor:** IDE for Patient Data  
**Principle:** Graph navigation for reasoning, not data retrieval

---

## EXECUTIVE SUMMARY

Agents interact with PatientTimelineVision using **IDE-like navigation primitives**:

- **Jump to Definition** → "What is this event?"
- **Find References** → "What mentions this event?"
- **Trace Upstream** → "What caused this?" (backward causality)
- **Inspect Downstream** → "What did this cause?" (forward impact)
- **Show Call Stack** → "How did we get here?" (provenance chain)
- **Find Usages** → "Where else does this pattern occur?"

These primitives enable **structured reasoning** instead of black-box RAG retrieval.

---

## IDE METAPHOR MAPPING

```
┌─────────────────────────────────────────────────────────────────────┐
│               IDE OPERATION → GRAPH OPERATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  IDE: Go to Definition (F12)                                        │
│  PTV: ptv.get_event(event_id) → Load full node details             │
│                                                                     │
│  IDE: Find All References (Shift+F12)                               │
│  PTV: ptv.find_references(event_id) → Follow REFERENCES edges      │
│                                                                     │
│  IDE: Go to Implementation                                          │
│  PTV: ptv.trace_upstream(event_id, CAUSAL_LIKELY) → Why?           │
│                                                                     │
│  IDE: Find Usages                                                   │
│  PTV: ptv.inspect_downstream(event_id, CAUSAL_LIKELY) → Impact?    │
│                                                                     │
│  IDE: Call Hierarchy (show stack)                                   │
│  PTV: ptv.get_provenance_chain(event_id) → How derived?            │
│                                                                     │
│  IDE: Type Hierarchy (show inheritance)                             │
│  PTV: ptv.find_similar_events(event_id) → SIMILARITY edges         │
│                                                                     │
│  IDE: Code Lens (inline context)                                    │
│  PTV: ptv.get_inline_context(event_id) → 1-hop neighbors           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## QUERY PRIMITIVES

### Primitive 1: `get_event()` — Jump to Definition

```python
def get_event(event_id: str) -> EventNode:
    """
    Load full details of a single event (like F12 in IDE).
    
    Returns:
        EventNode with all fields (structured, text, annotations, provenance)
    
    Example:
        event = ptv.get_event("evt_100")
        # EventNode(
        #   event_id="evt_100",
        #   node_type=MEASUREMENT,
        #   event_subtype="CRP",
        #   structured={"value": 65, "unit": "mg/L"},
        #   annotations={
        #     "M4_FlareSignals": {"flare_signal_strength": 0.85},
        #     "M1_Terrain": {"terrain_band": "elevated_chronic"}
        #   },
        #   discovered_by=["PTVBuilder", "M4_FlareSignals", "M1_Terrain"]
        # )
    """
    cur.execute("""
        SELECT 
            event_id, patient_id, node_type, event_subtype,
            timestamp, structured, text, annotations,
            discovered_by, status, source_type, source_system
        FROM ptv.event_node
        WHERE event_id = %s
    """, (event_id,))
    
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Event {event_id} not found")
    
    return EventNode(
        event_id=row[0],
        patient_id=row[1],
        node_type=NodeType(row[2]),
        event_subtype=row[3],
        timestamp=row[4],
        structured=row[5],
        text=row[6],
        annotations=row[7],
        discovered_by=row[8],
        status=NodeStatus(row[9]),
        source_type=SourceType(row[10]),
        source_system=row[11],
    )
```

---

### Primitive 2: `find_references()` — Find All References

```python
def find_references(
    event_id: str,
    max_depth: int = 2,
    min_strength: float = 0.5,
) -> List[EventReference]:
    """
    Find all events that reference this event (like Shift+F12 in IDE).
    
    Follows REFERENCES edges bidirectionally.
    
    Args:
        event_id: Target event
        max_depth: How many hops to traverse (default: 2)
        min_strength: Minimum edge strength (default: 0.5)
    
    Returns:
        List of EventReference objects with edge metadata
    
    Example:
        refs = ptv.find_references("evt_100")
        # [
        #   EventReference(
        #     event=EventNode(event_id="evt_note_123", ...),
        #     edge=Edge(type=REFERENCES, strength=1.0),
        #     path_length=1,
        #     explanation="Rheum note mentions CRP=65"
        #   ),
        #   EventReference(
        #     event=EventNode(event_id="evt_decision_200", ...),
        #     edge=Edge(type=CARE_PLAN_LINK, strength=0.9),
        #     path_length=2,
        #     explanation="Decision to increase MTX based on CRP"
        #   )
        # ]
    """
    references = []
    visited = set()
    
    def traverse(current_id: str, depth: int, path: List[str]):
        if depth > max_depth or current_id in visited:
            return
        visited.add(current_id)
        
        # Find edges where current event is source or target
        cur.execute("""
            SELECT 
                CASE WHEN source_event_id = %s THEN target_event_id 
                     ELSE source_event_id END as related_id,
                relationship_type,
                strength,
                confidence,
                annotations
            FROM ptv.event_edge
            WHERE (source_event_id = %s OR target_event_id = %s)
              AND relationship_type IN ('references', 'care_plan_link')
              AND strength >= %s
        """, (current_id, current_id, current_id, min_strength))
        
        for row in cur.fetchall():
            related_id, rel_type, strength, confidence, annotations = row
            
            # Load related event
            related_event = get_event(related_id)
            
            references.append(EventReference(
                event=related_event,
                edge=Edge(
                    relationship_type=RelationshipType(rel_type),
                    strength=strength,
                    confidence=confidence,
                    annotations=annotations,
                ),
                path_length=depth,
                path=path + [related_id],
                explanation=annotations.get("explanation", ""),
            ))
            
            # Recurse
            if depth < max_depth:
                traverse(related_id, depth + 1, path + [related_id])
    
    traverse(event_id, 1, [event_id])
    return references
```

---

### Primitive 3: `trace_upstream()` — Trace Causes (Backward)

```python
def trace_upstream(
    event_id: str,
    edge_types: List[RelationshipType] = None,
    max_depth: int = 3,
    min_confidence: float = 0.6,
) -> CausalChain:
    """
    Trace backward to find what caused this event (like "Show Call Stack").
    
    Follows CAUSAL_LIKELY, CAUSAL_POSSIBLE, PROVENANCE, DERIVED_FROM edges backward.
    
    Args:
        event_id: Target event (effect)
        edge_types: Types of edges to follow (default: all causal types)
        max_depth: Maximum hops backward (default: 3)
        min_confidence: Minimum edge confidence (default: 0.6)
    
    Returns:
        CausalChain object with all paths from causes to this event
    
    Example:
        chain = ptv.trace_upstream("evt_med_200")
        # CausalChain(
        #   target=EventNode(event_id="evt_med_200", event_subtype="MTX increase"),
        #   paths=[
        #     CausalPath(
        #       events=[
        #         EventNode(event_id="evt_100", event_subtype="CRP=65"),
        #         EventNode(event_id="evt_101", event_subtype="ESR=82"),
        #         EventNode(event_id="evt_risk_001", event_subtype="flare_risk"),
        #         EventNode(event_id="evt_med_200", event_subtype="MTX increase")
        #       ],
        #       edges=[...],
        #       total_strength=0.85,
        #       explanation="CRP+ESR elevation → flare risk → MTX increase"
        #     )
        #   ]
        # )
    """
    if edge_types is None:
        edge_types = [
            RelationshipType.CAUSAL_LIKELY,
            RelationshipType.CAUSAL_POSSIBLE,
            RelationshipType.PROVENANCE,
            RelationshipType.DERIVED_FROM,
        ]
    
    paths = []
    
    def traverse_backward(current_id: str, depth: int, path: List[EventNode], edges: List[Edge]):
        if depth > max_depth:
            return
        
        # Find incoming edges (causes)
        cur.execute("""
            SELECT 
                source_event_id,
                relationship_type,
                strength,
                confidence,
                annotations,
                time_delta
            FROM ptv.event_edge
            WHERE target_event_id = %s
              AND relationship_type = ANY(%s)
              AND confidence >= %s
            ORDER BY strength DESC
        """, (current_id, [et.value for et in edge_types], min_confidence))
        
        causes = cur.fetchall()
        
        if not causes:
            # Reached root cause; save path
            paths.append(CausalPath(
                events=list(reversed(path)),
                edges=list(reversed(edges)),
                total_strength=min(e.strength for e in edges) if edges else 1.0,
                explanation=generate_explanation(path, edges),
            ))
            return
        
        for cause_row in causes:
            cause_id, rel_type, strength, confidence, annotations, time_delta = cause_row
            
            # Load cause event
            cause_event = get_event(cause_id)
            
            edge = Edge(
                relationship_type=RelationshipType(rel_type),
                strength=strength,
                confidence=confidence,
                annotations=annotations,
                time_delta=time_delta,
            )
            
            # Recurse backward
            traverse_backward(
                cause_id,
                depth + 1,
                path + [cause_event],
                edges + [edge],
            )
    
    target_event = get_event(event_id)
    traverse_backward(event_id, 1, [target_event], [])
    
    return CausalChain(
        target=target_event,
        paths=paths,
    )
```

---

### Primitive 4: `inspect_downstream()` — Inspect Effects (Forward)

```python
def inspect_downstream(
    event_id: str,
    edge_types: List[RelationshipType] = None,
    max_depth: int = 3,
    min_confidence: float = 0.6,
) -> ImpactTree:
    """
    Inspect forward to find what this event caused (like "Find Usages").
    
    Follows CAUSAL_LIKELY, CAUSAL_POSSIBLE edges forward.
    
    Args:
        event_id: Source event (cause)
        edge_types: Types of edges to follow
        max_depth: Maximum hops forward
        min_confidence: Minimum edge confidence
    
    Returns:
        ImpactTree showing all downstream effects
    
    Example:
        tree = ptv.inspect_downstream("evt_100")
        # ImpactTree(
        #   source=EventNode(event_id="evt_100", event_subtype="CRP=65"),
        #   impacts=[
        #     Impact(
        #       event=EventNode(event_id="evt_risk_001", event_subtype="flare_risk_high"),
        #       edge=Edge(type=PROVENANCE, strength=0.9),
        #       depth=1,
        #       downstream_count=3  # This impact has 3 downstream effects
        #     ),
        #     Impact(
        #       event=EventNode(event_id="evt_med_200", event_subtype="MTX increase"),
        #       edge=Edge(type=CAUSAL_LIKELY, strength=0.85),
        #       depth=2
        #     )
        #   ]
        # )
    """
    if edge_types is None:
        edge_types = [
            RelationshipType.CAUSAL_LIKELY,
            RelationshipType.CAUSAL_POSSIBLE,
            RelationshipType.PROVENANCE,
        ]
    
    impacts = []
    
    def traverse_forward(current_id: str, depth: int):
        if depth > max_depth:
            return
        
        # Find outgoing edges (effects)
        cur.execute("""
            SELECT 
                target_event_id,
                relationship_type,
                strength,
                confidence,
                annotations,
                time_delta
            FROM ptv.event_edge
            WHERE source_event_id = %s
              AND relationship_type = ANY(%s)
              AND confidence >= %s
            ORDER BY strength DESC
        """, (current_id, [et.value for et in edge_types], min_confidence))
        
        effects = cur.fetchall()
        
        for effect_row in effects:
            effect_id, rel_type, strength, confidence, annotations, time_delta = effect_row
            
            # Load effect event
            effect_event = get_event(effect_id)
            
            edge = Edge(
                relationship_type=RelationshipType(rel_type),
                strength=strength,
                confidence=confidence,
                annotations=annotations,
                time_delta=time_delta,
            )
            
            # Count downstream effects
            downstream_count = count_downstream(effect_id, depth + 1, max_depth)
            
            impacts.append(Impact(
                event=effect_event,
                edge=edge,
                depth=depth,
                downstream_count=downstream_count,
            ))
            
            # Recurse forward
            traverse_forward(effect_id, depth + 1)
    
    source_event = get_event(event_id)
    traverse_forward(event_id, 1)
    
    return ImpactTree(
        source=source_event,
        impacts=impacts,
    )
```

---

### Primitive 5: `get_provenance_chain()` — Show Call Stack

```python
def get_provenance_chain(event_id: str) -> ProvenanceChain:
    """
    Get full provenance chain showing how event was derived (like "Call Stack").
    
    Follows DERIVED_FROM edges backward to root sources.
    
    Args:
        event_id: Target event (usually DERIVED_INSIGHT)
    
    Returns:
        ProvenanceChain with all source events and modules
    
    Example:
        chain = ptv.get_provenance_chain("evt_flare_2024Q1")
        # ProvenanceChain(
        #   target=EventNode(event_id="evt_flare_2024Q1", node_type=DERIVED_INSIGHT),
        #   sources=[
        #     ProvenanceSource(
        #       event=EventNode(event_id="evt_100", event_subtype="CRP=65"),
        #       module="M5_FlareWindowing",
        #       contribution=0.35,
        #       derivation_method="ml_model_v2"
        #     ),
        #     ProvenanceSource(
        #       event=EventNode(event_id="evt_101", event_subtype="ESR=82"),
        #       module="M5_FlareWindowing",
        #       contribution=0.30
        #     )
        #   ],
        #   derivation_graph=<DAG showing full derivation>
        # )
    """
    target_event = get_event(event_id)
    
    # Find all DERIVED_FROM edges
    cur.execute("""
        SELECT 
            source_event_id,
            strength,
            confidence,
            annotations,
            discovered_by
        FROM ptv.event_edge
        WHERE target_event_id = %s
          AND relationship_type = 'derived_from'
        ORDER BY strength DESC
    """, (event_id,))
    
    sources = []
    for row in cur.fetchall():
        source_id, strength, confidence, annotations, discovered_by = row
        
        source_event = get_event(source_id)
        
        sources.append(ProvenanceSource(
            event=source_event,
            module=annotations.get("module_name", "unknown"),
            contribution=strength,
            derivation_method=annotations.get("derivation_method", "unknown"),
            confidence=confidence,
        ))
    
    return ProvenanceChain(
        target=target_event,
        sources=sources,
        total_sources=len(sources),
    )
```

---

### Primitive 6: `find_similar_events()` — Find Similar

```python
def find_similar_events(
    event_id: str,
    similarity_threshold: float = 0.7,
    max_results: int = 10,
) -> List[SimilarEvent]:
    """
    Find events similar to this one (like "Type Hierarchy").
    
    Uses SIMILARITY edges + embedding similarity.
    
    Args:
        event_id: Target event
        similarity_threshold: Minimum similarity score
        max_results: Max results to return
    
    Returns:
        List of similar events with similarity scores
    
    Example:
        similar = ptv.find_similar_events("evt_flare_2024Q1")
        # [
        #   SimilarEvent(
        #     event=EventNode(event_id="evt_flare_2023Q1", ...),
        #     similarity=0.88,
        #     shared_features=["crp_elevation", "joint_swelling", "march_timing"],
        #     explanation="Similar flare pattern in spring, same symptoms"
        #   ),
        #   SimilarEvent(
        #     event=EventNode(event_id="evt_flare_2024Q3", ...),
        #     similarity=0.82,
        #     shared_features=["crp_elevation", "joint_swelling"],
        #     explanation="Similar flare pattern but different timing"
        #   )
        # ]
    """
    similar = []
    
    # Method 1: Follow SIMILARITY edges (explicit graph relationships)
    cur.execute("""
        SELECT 
            CASE WHEN source_event_id = %s THEN target_event_id 
                 ELSE source_event_id END as similar_id,
            strength,
            annotations
        FROM ptv.event_edge
        WHERE (source_event_id = %s OR target_event_id = %s)
          AND relationship_type = 'similarity'
          AND strength >= %s
        ORDER BY strength DESC
        LIMIT %s
    """, (event_id, event_id, event_id, similarity_threshold, max_results))
    
    for row in cur.fetchall():
        similar_id, similarity, annotations = row
        
        similar_event = get_event(similar_id)
        
        similar.append(SimilarEvent(
            event=similar_event,
            similarity=similarity,
            shared_features=annotations.get("shared_features", []),
            explanation=annotations.get("explanation", ""),
        ))
    
    # Method 2: Embedding similarity (if explicit edges insufficient)
    if len(similar) < max_results:
        # Query embedding table
        cur.execute("""
            SELECT embedding 
            FROM ptv.node_embeddings
            WHERE event_id = %s
        """, (event_id,))
        
        target_embedding = cur.fetchone()
        if target_embedding:
            # Vector similarity search
            cur.execute("""
                SELECT 
                    e.event_id,
                    emb.embedding <=> %s AS distance
                FROM ptv.node_embeddings emb
                JOIN ptv.event_node e ON e.event_id = emb.event_id
                WHERE emb.event_id != %s
                  AND e.node_type = (SELECT node_type FROM ptv.event_node WHERE event_id = %s)
                ORDER BY distance
                LIMIT %s
            """, (target_embedding[0], event_id, event_id, max_results - len(similar)))
            
            for row in cur.fetchall():
                similar_id, distance = row
                similarity_score = 1.0 - distance  # Convert distance to similarity
                
                if similarity_score >= similarity_threshold:
                    similar_event = get_event(similar_id)
                    
                    similar.append(SimilarEvent(
                        event=similar_event,
                        similarity=similarity_score,
                        shared_features=[],  # Inferred from embeddings
                        explanation=f"Semantically similar (embedding distance={distance:.3f})",
                    ))
    
    return similar[:max_results]
```

---

### Primitive 7: `get_inline_context()` — Code Lens

```python
def get_inline_context(
    event_id: str,
    radius: int = 1,
) -> InlineContext:
    """
    Get immediate context around an event (like "Code Lens" in IDE).
    
    Returns 1-hop neighbors via strong edges.
    
    Args:
        event_id: Target event
        radius: How many hops (default: 1 for immediate neighbors)
    
    Returns:
        InlineContext with temporal, causal, and referential neighbors
    
    Example:
        context = ptv.get_inline_context("evt_100")
        # InlineContext(
        #   event=EventNode(event_id="evt_100", event_subtype="CRP=65"),
        #   temporal_neighbors={
        #     "before": [EventNode(event_id="evt_99", timestamp=..., subtype="Visit")],
        #     "after": [EventNode(event_id="evt_101", timestamp=..., subtype="ESR=82")]
        #   },
        #   causal_upstream=[
        #     EventNode(event_id="evt_med_gap", subtype="MTX hold")
        #   ],
        #   causal_downstream=[
        #     EventNode(event_id="evt_risk_001", subtype="flare_risk_high")
        #   ],
        #   references=[
        #     EventNode(event_id="evt_note_123", subtype="rheum_note")
        #   ]
        # )
    """
    event = get_event(event_id)
    
    # Temporal neighbors (TEMPORAL_SEQUENCE edges)
    cur.execute("""
        SELECT target_event_id FROM ptv.event_edge
        WHERE source_event_id = %s AND relationship_type = 'temporal_sequence'
        LIMIT 3
    """, (event_id,))
    after = [get_event(row[0]) for row in cur.fetchall()]
    
    cur.execute("""
        SELECT source_event_id FROM ptv.event_edge
        WHERE target_event_id = %s AND relationship_type = 'temporal_sequence'
        LIMIT 3
    """, (event_id,))
    before = [get_event(row[0]) for row in cur.fetchall()]
    
    # Causal upstream (causes)
    cur.execute("""
        SELECT source_event_id FROM ptv.event_edge
        WHERE target_event_id = %s 
          AND relationship_type IN ('causal_likely', 'causal_possible')
        LIMIT 5
    """, (event_id,))
    causal_upstream = [get_event(row[0]) for row in cur.fetchall()]
    
    # Causal downstream (effects)
    cur.execute("""
        SELECT target_event_id FROM ptv.event_edge
        WHERE source_event_id = %s 
          AND relationship_type IN ('causal_likely', 'causal_possible')
        LIMIT 5
    """, (event_id,))
    causal_downstream = [get_event(row[0]) for row in cur.fetchall()]
    
    # References
    cur.execute("""
        SELECT CASE WHEN source_event_id = %s THEN target_event_id ELSE source_event_id END
        FROM ptv.event_edge
        WHERE (source_event_id = %s OR target_event_id = %s)
          AND relationship_type = 'references'
        LIMIT 5
    """, (event_id, event_id, event_id))
    references = [get_event(row[0]) for row in cur.fetchall()]
    
    return InlineContext(
        event=event,
        temporal_neighbors={"before": before, "after": after},
        causal_upstream=causal_upstream,
        causal_downstream=causal_downstream,
        references=references,
    )
```

---

## DEPTH-LIMITED TRAVERSAL

### Strategy: Breadth-First with Pruning

```python
class DepthLimitedTraversal:
    """
    Depth-limited graph traversal with intelligent pruning.
    
    Features:
    - BFS ensures shortest paths found first
    - Confidence-based pruning (skip low-confidence edges)
    - Strength-based pruning (skip weak relationships)
    - Cycle detection (don't revisit nodes)
    - Budget limiting (max nodes/edges to explore)
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        min_confidence: float = 0.6,
        min_strength: float = 0.5,
        max_nodes: int = 100,
    ):
        self.max_depth = max_depth
        self.min_confidence = min_confidence
        self.min_strength = min_strength
        self.max_nodes = max_nodes
        self.visited = set()
        self.nodes_explored = 0
    
    def traverse(
        self,
        start_id: str,
        edge_types: List[RelationshipType],
        direction: str = "forward",  # "forward" | "backward" | "bidirectional"
    ) -> List[Path]:
        """
        Traverse graph with depth/budget limits.
        
        Returns:
            List of Path objects (sequences of nodes + edges)
        """
        from collections import deque
        
        paths = []
        queue = deque([(start_id, [start_id], [], 0)])  # (current_id, path, edges, depth)
        
        while queue and self.nodes_explored < self.max_nodes:
            current_id, path, edges, depth = queue.popleft()
            
            if depth >= self.max_depth:
                # Save path and don't expand further
                paths.append(Path(nodes=path, edges=edges, depth=depth))
                continue
            
            if current_id in self.visited:
                continue
            
            self.visited.add(current_id)
            self.nodes_explored += 1
            
            # Find neighbors
            neighbors = self._find_neighbors(current_id, edge_types, direction)
            
            for neighbor_id, edge in neighbors:
                # Prune low-confidence or weak edges
                if edge.confidence < self.min_confidence or edge.strength < self.min_strength:
                    continue
                
                # Add to queue
                queue.append((
                    neighbor_id,
                    path + [neighbor_id],
                    edges + [edge],
                    depth + 1,
                ))
        
        return paths
    
    def _find_neighbors(self, node_id: str, edge_types: List[RelationshipType], direction: str):
        """Find neighbors based on direction and edge types."""
        if direction == "forward":
            # Outgoing edges
            query = """
                SELECT target_event_id, relationship_type, strength, confidence, annotations
                FROM ptv.event_edge
                WHERE source_event_id = %s AND relationship_type = ANY(%s)
            """
        elif direction == "backward":
            # Incoming edges
            query = """
                SELECT source_event_id, relationship_type, strength, confidence, annotations
                FROM ptv.event_edge
                WHERE target_event_id = %s AND relationship_type = ANY(%s)
            """
        else:  # bidirectional
            query = """
                SELECT 
                    CASE WHEN source_event_id = %s THEN target_event_id ELSE source_event_id END,
                    relationship_type, strength, confidence, annotations
                FROM ptv.event_edge
                WHERE (source_event_id = %s OR target_event_id = %s)
                  AND relationship_type = ANY(%s)
            """
        
        # Execute query (implementation details omitted for brevity)
        # Returns list of (neighbor_id, Edge) tuples
        pass
```

---

## REASONING PATH EXPLANATION

### Explanation Generator

```python
class ReasoningPathExplainer:
    """
    Generate human-readable explanations of reasoning paths.
    
    Converts graph paths into structured narratives.
    """
    
    def explain_path(self, path: CausalPath) -> str:
        """
        Generate explanation for a causal path.
        
        Example:
            Input: CausalPath with 4 events (CRP → flare risk → decision → MTX)
            Output: "CRP elevation (evt_100, value=65) triggered high flare risk 
                     (evt_risk_001, score=0.85, M7A), which led to the clinical 
                     decision (evt_decision_200) to increase methotrexate 
                     (evt_med_200, dose=20mg). Confidence: 0.85 (M4, M22)."
        """
        if not path.events:
            return "No path found."
        
        explanation_parts = []
        
        for i, event in enumerate(path.events[:-1]):
            next_event = path.events[i + 1]
            edge = path.edges[i]
            
            # Format event
            event_desc = self._format_event(event)
            
            # Format relationship
            rel_desc = self._format_relationship(edge)
            
            # Format next event
            next_desc = self._format_event(next_event)
            
            explanation_parts.append(f"{event_desc} {rel_desc} {next_desc}")
        
        # Add confidence and provenance
        modules = list(set(
            module 
            for edge in path.edges 
            for module in edge.annotations.get("discovered_by", [])
        ))
        
        explanation = " → ".join(explanation_parts)
        explanation += f" (Confidence: {path.total_strength:.2f}, Modules: {', '.join(modules)})"
        
        return explanation
    
    def _format_event(self, event: EventNode) -> str:
        """Format event as human-readable string."""
        if event.node_type == NodeType.MEASUREMENT:
            value = event.structured.get("value")
            unit = event.structured.get("unit", "")
            return f"{event.event_subtype}={value}{unit} ({event.event_id})"
        
        elif event.node_type == NodeType.MEDICATION_CHANGE:
            drug = event.structured.get("drug_name")
            action = event.structured.get("action")
            return f"{action} {drug} ({event.event_id})"
        
        elif event.node_type == NodeType.RISK_SIGNAL:
            signal_type = event.structured.get("signal_type")
            risk_level = event.structured.get("risk_level")
            return f"{signal_type}: {risk_level} ({event.event_id})"
        
        elif event.node_type == NodeType.DERIVED_INSIGHT:
            insight_type = event.structured.get("insight_type")
            summary = event.structured.get("insight_summary", "")
            return f"{insight_type} - {summary[:50]}... ({event.event_id})"
        
        else:
            return f"{event.node_type}/{event.event_subtype} ({event.event_id})"
    
    def _format_relationship(self, edge: Edge) -> str:
        """Format edge relationship as human-readable string."""
        rel_map = {
            RelationshipType.CAUSAL_LIKELY: "likely caused",
            RelationshipType.CAUSAL_POSSIBLE: "possibly caused",
            RelationshipType.PROVENANCE: "derived",
            RelationshipType.DERIVED_FROM: "was computed from",
            RelationshipType.REFERENCES: "is mentioned in",
            RelationshipType.CARE_PLAN_LINK: "triggered care plan for",
        }
        
        rel_text = rel_map.get(edge.relationship_type, "related to")
        
        # Add time delta if available
        if edge.time_delta:
            days = edge.time_delta.days
            if days == 0:
                time_text = "immediately"
            elif days == 1:
                time_text = "1 day later"
            else:
                time_text = f"{days} days later"
            rel_text = f"{rel_text} ({time_text})"
        
        return rel_text
    
    def explain_multi_path(self, chain: CausalChain) -> str:
        """
        Explain multiple causal paths (when there are multiple causes).
        
        Example:
            Input: CausalChain with 3 paths to MTX increase
            Output: "Methotrexate increase (evt_med_200) had multiple causes:
                     
                     Path 1 (strength=0.85): CRP elevation → flare risk → decision
                     Path 2 (strength=0.78): ESR elevation → flare risk → decision
                     Path 3 (strength=0.65): Prior flare history → increased baseline risk
                     
                     Primary contributing factors: CRP elevation (35%), ESR elevation (30%), 
                     prior flares (25%), disease activity trend (10%)."
        """
        if not chain.paths:
            return "No causal paths found."
        
        intro = f"Event {chain.target.event_id} ({self._format_event(chain.target)}) had multiple causes:\n\n"
        
        path_explanations = []
        for i, path in enumerate(chain.paths, 1):
            path_summary = " → ".join([
                event.event_subtype for event in path.events
            ])
            path_explanations.append(
                f"Path {i} (strength={path.total_strength:.2f}): {path_summary}"
            )
        
        paths_text = "\n".join(path_explanations)
        
        # Aggregate contributing factors
        factors = self._aggregate_contributing_factors(chain)
        factors_text = ", ".join([
            f"{name} ({contrib:.0%})" for name, contrib in factors.items()
        ])
        
        return f"{intro}{paths_text}\n\nPrimary contributing factors: {factors_text}"
    
    def _aggregate_contributing_factors(self, chain: CausalChain) -> Dict[str, float]:
        """Aggregate contribution of each factor across all paths."""
        contributions = {}
        total_strength = sum(path.total_strength for path in chain.paths)
        
        for path in chain.paths:
            weight = path.total_strength / total_strength if total_strength > 0 else 0
            
            # First event in path is the root cause
            if path.events:
                root_cause = path.events[0]
                factor_name = root_cause.event_subtype
                contributions[factor_name] = contributions.get(factor_name, 0) + weight
        
        return contributions
```

---

## INTEGRATION WITH EOH DETECTIVE

### Detective Query Pattern

```python
class DetectiveQueryAdapter:
    """
    Adapts PTV Agent API for EoH Detective streaming.
    
    EoH Detective asks investigative questions; PTV provides graph-backed answers.
    """
    
    def answer_detective_query(
        self,
        query: Dict[str, Any],
        patient_id: str,
    ) -> Dict[str, Any]:
        """
        Answer an EoH Detective query using PTV graph.
        
        Args:
            query: Detective query (from /api/rag/detective_stream)
                {
                    "step_id": "A1",
                    "kind": "terrain_risk",
                    "question_type": "A",
                    "q": "What are the major clinical arcs and inflection points?"
                }
            patient_id: Patient ID
        
        Returns:
            Answer with graph-backed evidence
        """
        kind = query.get("kind")
        question = query.get("q")
        
        if kind == "terrain_risk":
            return self._answer_terrain_query(patient_id)
        
        elif kind == "flare_vs_noise":
            return self._answer_flare_classification(patient_id, question)
        
        elif kind == "trajectory":
            return self._answer_trajectory_query(patient_id)
        
        elif kind == "diagnostic_landscape":
            return self._answer_diagnostic_query(patient_id)
        
        else:
            # Generic query: Use semantic search + graph traversal
            return self._answer_generic_query(patient_id, question)
    
    def _answer_terrain_query(self, patient_id: str) -> Dict[str, Any]:
        """
        Answer terrain risk query using PTV graph.
        
        Identifies:
        - Major clinical arcs (flare episodes, remission periods)
        - Inflection points (where trajectory changed)
        - Dominant active problems
        """
        # Find all DERIVED_INSIGHT nodes (arcs)
        cur.execute("""
            SELECT event_id, event_subtype, structured, timestamp, annotations
            FROM ptv.event_node
            WHERE patient_id = %s
              AND node_type = 'derived_insight'
              AND status = 'included'
            ORDER BY timestamp
        """, (patient_id,))
        
        arcs = []
        for row in cur.fetchall():
            event_id, subtype, structured, timestamp, annotations = row
            
            # Get inline context for this arc
            context = get_inline_context(event_id)
            
            arcs.append({
                "arc_id": event_id,
                "arc_type": subtype,
                "timestamp": timestamp.isoformat(),
                "summary": structured.get("insight_summary"),
                "severity": structured.get("severity", "unknown"),
                "constituent_events": len(context.causal_upstream),
                "downstream_impact": len(context.causal_downstream),
            })
        
        # Identify inflection points (where terrain changed significantly)
        inflection_points = []
        for i in range(1, len(arcs)):
            prev_arc = arcs[i-1]
            curr_arc = arcs[i]
            
            # Check if arc type changed (e.g., remission → flare)
            if prev_arc["arc_type"] != curr_arc["arc_type"]:
                inflection_points.append({
                    "timestamp": curr_arc["timestamp"],
                    "change": f"{prev_arc['arc_type']} → {curr_arc['arc_type']}",
                    "trigger_arc": curr_arc["arc_id"],
                })
        
        # Identify dominant active problems (recent high-severity arcs)
        recent_arcs = [arc for arc in arcs if arc["timestamp"] >= (datetime.now() - timedelta(days=90)).isoformat()]
        dominant_problems = [
            arc["arc_type"] for arc in recent_arcs if arc.get("severity") in ["moderate", "high", "critical"]
        ]
        
        return {
            "patient_id": patient_id,
            "major_arcs": arcs,
            "inflection_points": inflection_points,
            "dominant_problems": list(set(dominant_problems)),
            "provenance": "Derived from PatientTimelineVision graph (DERIVED_INSIGHT nodes)",
        }
    
    def _answer_flare_classification(self, patient_id: str, question: str) -> Dict[str, Any]:
        """
        Classify whether an episode is a true flare vs. noise.
        
        Uses:
        - Flare signal strength annotations (M4)
        - Temporal patterns (M5)
        - Comparison to prior flares (SIMILARITY edges)
        """
        # Extract episode reference from question (simplified)
        # In practice, would use NLP/semantic search
        
        # For now, get most recent potential flare
        cur.execute("""
            SELECT event_id, structured, annotations, timestamp
            FROM ptv.event_node
            WHERE patient_id = %s
              AND node_type = 'measurement'
              AND status = 'included'
              AND annotations->'M4_FlareSignals'->>'flare_signal_strength' IS NOT NULL
              AND (annotations->'M4_FlareSignals'->>'flare_signal_strength')::float > 0.7
            ORDER BY timestamp DESC
            LIMIT 1
        """, (patient_id,))
        
        potential_flare = cur.fetchone()
        if not potential_flare:
            return {"answer": "No recent high-signal events found."}
        
        event_id, structured, annotations, timestamp = potential_flare
        
        # Trace upstream to see if this is part of a composite flare episode
        chain = trace_upstream(event_id, max_depth=2)
        
        # Check if linked to DERIVED_INSIGHT (flare episode)
        is_part_of_episode = any(
            event.node_type == NodeType.DERIVED_INSIGHT 
            and event.event_subtype == "flare_episode"
            for path in chain.paths
            for event in path.events
        )
        
        # Find similar past events
        similar = find_similar_events(event_id, similarity_threshold=0.75)
        
        # Classification logic
        signal_strength = annotations["M4_FlareSignals"]["flare_signal_strength"]
        
        if is_part_of_episode and signal_strength > 0.8:
            classification = "TRUE_FLARE"
            confidence = 0.90
            reasoning = f"High signal strength ({signal_strength:.2f}) + part of validated flare episode"
        elif len(similar) >= 2 and signal_strength > 0.7:
            classification = "LIKELY_FLARE"
            confidence = 0.75
            reasoning = f"Similar to {len(similar)} prior flare events"
        elif signal_strength > 0.7:
            classification = "POSSIBLE_FLARE"
            confidence = 0.60
            reasoning = "High signal but no corroborating evidence"
        else:
            classification = "NOISE"
            confidence = 0.80
            reasoning = "Low signal strength, not consistent with prior flares"
        
        return {
            "event_id": event_id,
            "classification": classification,
            "confidence": confidence,
            "reasoning": reasoning,
            "signal_strength": signal_strength,
            "similar_past_events": len(similar),
            "part_of_episode": is_part_of_episode,
            "provenance": "Graph-based classification using M4, M5 annotations + SIMILARITY edges",
        }
```

---

## EXAMPLE: MULTI-STEP REASONING

### Use Case: "Why was biologic started?"

```python
def explain_biologic_start(patient_id: str, decision_event_id: str) -> Dict[str, Any]:
    """
    Full multi-step reasoning using PTV Agent API.
    
    Steps:
    1. Jump to definition (load decision event)
    2. Trace upstream (find causes)
    3. Inspect downstream (verify implementation)
    4. Find references (clinical documentation)
    5. Get provenance (which modules contributed)
    6. Generate explanation (structured narrative)
    """
    
    # Step 1: Jump to definition
    decision = ptv.get_event(decision_event_id)
    
    if decision.node_type != NodeType.DECISION:
        raise ValueError(f"Event {decision_event_id} is not a DECISION node")
    
    # Step 2: Trace upstream causes
    chain = ptv.trace_upstream(
        decision_event_id,
        edge_types=[RelationshipType.CAUSAL_LIKELY, RelationshipType.CARE_PLAN_LINK],
        max_depth=3,
    )
    
    # Step 3: Inspect downstream (was biologic actually started?)
    impact_tree = ptv.inspect_downstream(
        decision_event_id,
        edge_types=[RelationshipType.CARE_PLAN_LINK],
        max_depth=2,
    )
    
    # Verify implementation
    biologic_started = any(
        impact.event.node_type == NodeType.MEDICATION_CHANGE 
        and "biologic" in impact.event.structured.get("drug_class", "").lower()
        for impact in impact_tree.impacts
    )
    
    # Step 4: Find references (clinical notes)
    references = ptv.find_references(decision_event_id, max_depth=1)
    clinical_notes = [
        ref.event for ref in references if ref.event.node_type == NodeType.NOTE
    ]
    
    # Step 5: Get provenance
    provenance = ptv.get_provenance_chain(decision_event_id)
    
    # Step 6: Generate explanation
    explainer = ReasoningPathExplainer()
    
    explanation = {
        "decision": {
            "event_id": decision_event_id,
            "summary": decision.structured.get("decision_summary"),
            "timestamp": decision.timestamp.isoformat(),
        },
        "reasoning_paths": [],
        "verified_implementation": biologic_started,
        "clinical_documentation": [],
        "provenance": {
            "modules": provenance.sources if provenance else [],
        }
    }
    
    # Add each causal path
    for path in chain.paths:
        explanation["reasoning_paths"].append({
            "summary": explainer.explain_path(path),
            "strength": path.total_strength,
            "events": [
                {
                    "event_id": event.event_id,
                    "type": event.node_type.value,
                    "subtype": event.event_subtype,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in path.events
            ]
        })
    
    # Add clinical notes
    for note in clinical_notes:
        explanation["clinical_documentation"].append({
            "event_id": note.event_id,
            "timestamp": note.timestamp.isoformat(),
            "excerpt": note.text[:200] + "..." if len(note.text) > 200 else note.text,
        })
    
    return explanation

# Example output:
# {
#   "decision": {
#     "event_id": "evt_decision_500",
#     "summary": "Start TNF inhibitor (adalimumab)",
#     "timestamp": "2024-12-15T10:00:00Z"
#   },
#   "reasoning_paths": [
#     {
#       "summary": "CRP=65mg/L (evt_100) likely caused flare_risk=high (evt_risk_001, score=0.90, M7A), which triggered care plan for Start TNF inhibitor (evt_decision_500, M22). Confidence: 0.88 (M4, M7A, M22)",
#       "strength": 0.88,
#       "events": [...]
#     },
#     {
#       "summary": "MTX failure over 6 months (evt_med_history, M22) possibly caused increased baseline risk (evt_risk_baseline), which triggered care plan for Start TNF inhibitor. Confidence: 0.75",
#       "strength": 0.75,
#       "events": [...]
#     }
#   ],
#   "verified_implementation": true,
#   "clinical_documentation": [
#     {
#       "event_id": "evt_note_300",
#       "timestamp": "2024-12-15T11:00:00Z",
#       "excerpt": "Patient has persistent disease activity despite MTX 25mg weekly. CRP remains elevated. Discussed risks/benefits of biologic therapy. Patient agrees to start adalimumab..."
#     }
#   ],
#   "provenance": {
#     "modules": [
#       {"module": "M7A_Prognostics", "contribution": 0.40},
#       {"module": "M22_CarePlanning", "contribution": 0.35},
#       {"module": "M4_FlareSignals", "contribution": 0.25}
#     ]
#   }
# }
```

---

## SUMMARY: REASONING ERGONOMICS

```yaml
ergonomics_principles:
  - name: "IDE Metaphor"
    description: "Navigate like code: jump, reference, trace, inspect"
    benefit: "Familiar mental model for developers"
    
  - name: "Depth-Limited Traversal"
    description: "Max depth + confidence pruning prevents explosion"
    benefit: "Fast queries even on complex graphs"
    
  - name: "Structured Explanations"
    description: "Convert graph paths to human narratives"
    benefit: "Clinicians understand reasoning"
    
  - name: "Multi-Path Reasoning"
    description: "Show all contributing factors, not just strongest"
    benefit: "Complete picture, not cherry-picked"
    
  - name: "Provenance Tracking"
    description: "Every answer cites graph sources + modules"
    benefit: "Auditable, verifiable"
    
  - name: "Detective Integration"
    description: "Detective asks questions, PTV provides graph-backed answers"
    benefit: "Investigative workflow supported"
```

---

**END OF SPECIFICATION**

**Next:** Implement agent API module (`server/ptv/agent_api.py`)

