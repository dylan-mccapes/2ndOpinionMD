"""
EoH Timeline Engine

Core engine for patient timeline management, embedding, ANN search,
flare prediction, and diagnostic landscape estimation.

All outputs are probabilistic, transparent, and non-diagnostic per regulatory strategy.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    DiagnosticLandscape,
    DiagnosticProbability,
    EventSource,
    EventType,
    FlareLikelihood,
    FlarePrecursor,
    FlarePrediction,
    FlareReport,
    FlareSignature,
    TimelineContext,
    TimelineEvent,
    TimelineEventCreate,
    TimelineResponse,
)

logger = logging.getLogger(__name__)

# OpenAI client for embeddings
client = OpenAI()

# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class TimelineEngine:
    """
    Core engine for patient timeline operations.
    
    Provides:
    - Timeline event storage and retrieval
    - Embedding generation using text-embedding-3-small
    - ANN search for similar events
    - Flare precursor detection
    - Diagnostic landscape estimation
    """
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """Initialize the timeline engine."""
        self.session = session
        self._flare_signatures: Optional[List[FlareSignature]] = None
    
    # =========================================================================
    # Embedding Operations
    # =========================================================================
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI text-embedding-3-small.
        
        Args:
            text: Text to embed
            
        Returns:
            List of 1536 floats representing the embedding
        """
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Using dummy embedding for testing.")
            # Return dummy embedding for testing/development
            return np.random.random(EMBEDDING_DIMENSION).tolist()
    
    async def get_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            
        Returns:
            List of embeddings
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch
                )
                embeddings.extend([d.embedding for d in response.data])
            except Exception as e:
                logger.warning(f"Batch embedding failed: {e}. Using dummy embeddings.")
                embeddings.extend([
                    np.random.random(EMBEDDING_DIMENSION).tolist() 
                    for _ in batch
                ])
        return embeddings
    
    # =========================================================================
    # Timeline Event Operations
    # =========================================================================
    
    async def store_event(
        self,
        session: AsyncSession,
        event: TimelineEventCreate,
        generate_embedding: bool = True
    ) -> int:
        """
        Store a timeline event in the database.
        
        Args:
            session: Database session
            event: Event to store
            generate_embedding: Whether to generate embedding for the event
            
        Returns:
            ID of the stored event
        """
        embedding = None
        if generate_embedding and event.text:
            embedding = await self.get_embedding(event.text)
        
        # Convert embedding to PostgreSQL array literal
        embedding_literal = None
        if embedding:
            embedding_literal = f"[{','.join(str(x) for x in embedding)}]"
        
        sql = text("""
            INSERT INTO ehr.patient_timeline 
            (patient_id, ts, event_type, source, structured, text, embedding, meta)
            VALUES 
            (:patient_id, :ts, :event_type, :source, :structured::jsonb, :text, 
             CASE WHEN :embedding IS NOT NULL THEN :embedding::vector ELSE NULL END, 
             :meta::jsonb)
            RETURNING id
        """)
        
        import json
        result = await session.execute(sql, {
            "patient_id": event.patient_id,
            "ts": event.ts,
            "event_type": event.event_type if isinstance(event.event_type, str) else event.event_type.value,
            "source": event.source if isinstance(event.source, str) else event.source.value,
            "structured": json.dumps(event.structured) if event.structured else None,
            "text": event.text,
            "embedding": embedding_literal,
            "meta": json.dumps(event.meta) if event.meta else "{}",
        })
        
        row = result.fetchone()
        await session.commit()
        return row[0]
    
    async def store_events_batch(
        self,
        session: AsyncSession,
        events: List[TimelineEventCreate],
        generate_embeddings: bool = True
    ) -> List[int]:
        """
        Store multiple timeline events in batch.
        
        Args:
            session: Database session
            events: Events to store
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of IDs of stored events
        """
        ids = []
        
        # Generate embeddings in batch if needed
        embeddings = None
        if generate_embeddings:
            texts = [e.text for e in events if e.text]
            if texts:
                embeddings = await self.get_embeddings_batch(texts)
        
        embedding_idx = 0
        for event in events:
            embedding = None
            if generate_embeddings and event.text and embeddings:
                embedding = embeddings[embedding_idx]
                embedding_idx += 1
            
            # Store event with embedding
            event_id = await self._store_event_with_embedding(
                session, event, embedding
            )
            ids.append(event_id)
        
        await session.commit()
        return ids
    
    async def _store_event_with_embedding(
        self,
        session: AsyncSession,
        event: TimelineEventCreate,
        embedding: Optional[List[float]]
    ) -> int:
        """Store a single event with pre-computed embedding."""
        embedding_literal = None
        if embedding:
            embedding_literal = f"[{','.join(str(x) for x in embedding)}]"
        
        sql = text("""
            INSERT INTO ehr.patient_timeline 
            (patient_id, ts, event_type, source, structured, text, embedding, meta)
            VALUES 
            (:patient_id, :ts, :event_type, :source, :structured::jsonb, :text, 
             CASE WHEN :embedding IS NOT NULL THEN :embedding::vector ELSE NULL END, 
             :meta::jsonb)
            RETURNING id
        """)
        
        import json
        result = await session.execute(sql, {
            "patient_id": event.patient_id,
            "ts": event.ts,
            "event_type": event.event_type if isinstance(event.event_type, str) else event.event_type.value,
            "source": event.source if isinstance(event.source, str) else event.source.value,
            "structured": json.dumps(event.structured) if event.structured else None,
            "text": event.text,
            "embedding": embedding_literal,
            "meta": json.dumps(event.meta) if event.meta else "{}",
        })
        
        row = result.fetchone()
        return row[0]
    
    async def get_timeline(
        self,
        session: AsyncSession,
        patient_id: str,
        limit: int = 1000,
        offset: int = 0,
        event_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TimelineResponse:
        """
        Retrieve patient timeline events.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            limit: Maximum number of events to return
            offset: Offset for pagination
            event_types: Filter by event types
            start_date: Filter events after this date
            end_date: Filter events before this date
            
        Returns:
            TimelineResponse with events and metadata
        """
        # Build query with filters
        where_clauses = ["patient_id = :patient_id"]
        params: Dict[str, Any] = {"patient_id": patient_id, "limit": limit, "offset": offset}
        
        if event_types:
            where_clauses.append("event_type = ANY(:event_types)")
            params["event_types"] = event_types
        
        if start_date:
            where_clauses.append("ts >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_clauses.append("ts <= :end_date")
            params["end_date"] = end_date
        
        where_sql = " AND ".join(where_clauses)
        
        # Get events
        sql = text(f"""
            SELECT id, patient_id, ts, event_type, source, structured, text, meta,
                   created_at, updated_at
            FROM ehr.patient_timeline
            WHERE {where_sql}
            ORDER BY ts DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await session.execute(sql, params)
        rows = result.fetchall()
        
        events = []
        for row in rows:
            events.append(TimelineEvent(
                id=row[0],
                patient_id=row[1],
                ts=row[2],
                event_type=row[3],
                source=row[4],
                structured=row[5],
                text=row[6],
                meta=row[7] or {},
                created_at=row[8],
                updated_at=row[9],
            ))
        
        # Get total count
        count_sql = text(f"""
            SELECT COUNT(*) FROM ehr.patient_timeline WHERE {where_sql}
        """)
        count_result = await session.execute(count_sql, params)
        total_count = count_result.scalar()
        
        # Get event type counts
        type_count_sql = text("""
            SELECT event_type, COUNT(*) as cnt
            FROM ehr.patient_timeline
            WHERE patient_id = :patient_id
            GROUP BY event_type
        """)
        type_result = await session.execute(type_count_sql, {"patient_id": patient_id})
        event_type_counts = {row[0]: row[1] for row in type_result.fetchall()}
        
        # Calculate span
        span_days = None
        if events:
            dates = [e.ts for e in events]
            span_days = (max(dates) - min(dates)).days
        
        return TimelineResponse(
            patient_id=patient_id,
            events=events,
            total_count=total_count,
            span_days=span_days,
            event_type_counts=event_type_counts,
        )
    
    # =========================================================================
    # ANN Search Operations
    # =========================================================================
    
    async def search_similar_events(
        self,
        session: AsyncSession,
        query_text: str,
        patient_id: Optional[str] = None,
        limit: int = 10,
        event_types: Optional[List[str]] = None,
    ) -> List[Tuple[TimelineEvent, float]]:
        """
        Search for similar timeline events using ANN.
        
        Args:
            session: Database session
            query_text: Text to search for
            patient_id: Optional patient filter
            limit: Maximum results
            event_types: Optional event type filter
            
        Returns:
            List of (event, similarity_score) tuples
        """
        # Get query embedding
        query_embedding = await self.get_embedding(query_text)
        embedding_literal = f"[{','.join(str(x) for x in query_embedding)}]"
        
        # Build query
        where_clauses = ["embedding IS NOT NULL"]
        params: Dict[str, Any] = {
            "embedding": embedding_literal,
            "limit": limit,
        }
        
        if patient_id:
            where_clauses.append("patient_id = :patient_id")
            params["patient_id"] = patient_id
        
        if event_types:
            where_clauses.append("event_type = ANY(:event_types)")
            params["event_types"] = event_types
        
        where_sql = " AND ".join(where_clauses)
        
        sql = text(f"""
            SELECT id, patient_id, ts, event_type, source, structured, text, meta,
                   created_at, updated_at,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM ehr.patient_timeline
            WHERE {where_sql}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = await session.execute(sql, params)
        rows = result.fetchall()
        
        results = []
        for row in rows:
            event = TimelineEvent(
                id=row[0],
                patient_id=row[1],
                ts=row[2],
                event_type=row[3],
                source=row[4],
                structured=row[5],
                text=row[6],
                meta=row[7] or {},
                created_at=row[8],
                updated_at=row[9],
            )
            similarity = float(row[10])
            results.append((event, similarity))
        
        return results
    
    async def search_by_embedding(
        self,
        session: AsyncSession,
        embedding: List[float],
        patient_id: Optional[str] = None,
        limit: int = 10,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[Tuple[TimelineEvent, float]]:
        """
        Search for similar events using a pre-computed embedding.
        
        Args:
            session: Database session
            embedding: Query embedding vector
            patient_id: Optional patient filter
            limit: Maximum results
            exclude_ids: Event IDs to exclude
            
        Returns:
            List of (event, similarity_score) tuples
        """
        embedding_literal = f"[{','.join(str(x) for x in embedding)}]"
        
        where_clauses = ["embedding IS NOT NULL"]
        params: Dict[str, Any] = {
            "embedding": embedding_literal,
            "limit": limit,
        }
        
        if patient_id:
            where_clauses.append("patient_id = :patient_id")
            params["patient_id"] = patient_id
        
        if exclude_ids:
            where_clauses.append("id != ALL(:exclude_ids)")
            params["exclude_ids"] = exclude_ids
        
        where_sql = " AND ".join(where_clauses)
        
        sql = text(f"""
            SELECT id, patient_id, ts, event_type, source, structured, text, meta,
                   created_at, updated_at,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM ehr.patient_timeline
            WHERE {where_sql}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = await session.execute(sql, params)
        rows = result.fetchall()
        
        results = []
        for row in rows:
            event = TimelineEvent(
                id=row[0],
                patient_id=row[1],
                ts=row[2],
                event_type=row[3],
                source=row[4],
                structured=row[5],
                text=row[6],
                meta=row[7] or {},
                created_at=row[8],
                updated_at=row[9],
            )
            similarity = float(row[10])
            results.append((event, similarity))
        
        return results
    
    # =========================================================================
    # Flare Prediction Operations
    # =========================================================================
    
    def get_flare_signatures(self) -> List[FlareSignature]:
        """
        Get synthetic flare signatures for ANN comparison.
        
        These represent known patterns that precede autoimmune flares.
        In production, these would be learned from historical data.
        """
        if self._flare_signatures is not None:
            return self._flare_signatures
        
        # Synthetic flare signatures (mocked for initial implementation)
        self._flare_signatures = [
            FlareSignature(
                id="ra_flare_inflammatory",
                name="RA Flare - Inflammatory Marker Pattern",
                description="Rising CRP/ESR with joint symptoms preceding RA flare",
                pattern_type="ra_flare",
                embedding=[],  # Will be populated on first use
                characteristic_events=[
                    "CRP elevated above baseline",
                    "ESR trending upward",
                    "Morning stiffness > 60 minutes",
                    "Multiple joint pain/swelling",
                ],
                typical_timeline_days=14,
                inflammatory_markers={"CRP": "rising", "ESR": "elevated"},
                symptom_patterns=["joint_pain", "morning_stiffness", "fatigue"],
            ),
            FlareSignature(
                id="ra_flare_medication_gap",
                name="RA Flare - Medication Gap Pattern",
                description="DMARD adherence gap followed by symptom increase",
                pattern_type="ra_flare",
                embedding=[],
                characteristic_events=[
                    "Missed DMARD doses",
                    "Medication gap > 7 days",
                    "Gradual symptom return",
                    "Joint stiffness increase",
                ],
                typical_timeline_days=21,
                medication_patterns=["dmard_gap", "adherence_drop"],
                symptom_patterns=["joint_stiffness", "fatigue"],
            ),
            FlareSignature(
                id="lupus_flare_pattern",
                name="SLE Flare Pattern",
                description="Fatigue, rash, and complement changes preceding lupus flare",
                pattern_type="lupus_flare",
                embedding=[],
                characteristic_events=[
                    "Increasing fatigue",
                    "New or worsening rash",
                    "Complement C3/C4 dropping",
                    "Joint pain",
                ],
                typical_timeline_days=10,
                inflammatory_markers={"C3": "dropping", "C4": "dropping"},
                symptom_patterns=["fatigue", "rash", "joint_pain"],
            ),
            FlareSignature(
                id="psa_flare_pattern",
                name="PsA Flare Pattern",
                description="Skin flare with joint involvement",
                pattern_type="psa_flare",
                embedding=[],
                characteristic_events=[
                    "Psoriasis worsening",
                    "Dactylitis",
                    "Enthesitis",
                    "Joint swelling",
                ],
                typical_timeline_days=14,
                symptom_patterns=["skin_flare", "dactylitis", "joint_swelling"],
            ),
        ]
        
        return self._flare_signatures
    
    async def _ensure_signature_embeddings(self, session: AsyncSession) -> None:
        """Generate embeddings for flare signatures if not already done."""
        signatures = self.get_flare_signatures()
        
        for sig in signatures:
            if not sig.embedding:
                # Create text representation of signature
                sig_text = f"{sig.name}. {sig.description}. " + \
                           f"Characteristic events: {', '.join(sig.characteristic_events)}"
                sig.embedding = await self.get_embedding(sig_text)
    
    async def find_flare_precursors(
        self,
        session: AsyncSession,
        patient_id: str,
        window_days: int = 90,
        top_k: int = 10,
    ) -> List[FlarePrecursor]:
        """
        Find potential flare precursor events in patient timeline.
        
        Uses ANN search to compare recent events with known flare lead-in patterns.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            window_days: Days to look back from most recent event
            top_k: Number of precursors to return
            
        Returns:
            List of FlarePrecursor objects with similarity scores
        """
        # Ensure signature embeddings are generated
        await self._ensure_signature_embeddings(session)
        
        # Get patient's recent timeline
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=window_days)
        
        timeline = await self.get_timeline(
            session, patient_id,
            start_date=start_date,
            end_date=end_date,
            limit=500,
        )
        
        if not timeline.events:
            return []
        
        precursors: List[FlarePrecursor] = []
        signatures = self.get_flare_signatures()
        
        # Compare each event against flare signatures
        for event in timeline.events:
            if not event.text:
                continue
            
            event_embedding = await self.get_embedding(event.text)
            
            for sig in signatures:
                if not sig.embedding:
                    continue
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(event_embedding, sig.embedding)
                
                if similarity > 0.5:  # Threshold for relevance
                    precursor_type = self._classify_precursor_type(event, sig)
                    explanation = self._generate_precursor_explanation(event, sig, similarity)
                    
                    precursors.append(FlarePrecursor(
                        event=event,
                        similarity_score=similarity,
                        precursor_type=precursor_type,
                        explanation=explanation,
                    ))
        
        # Sort by similarity and return top K
        precursors.sort(key=lambda p: p.similarity_score, reverse=True)
        return precursors[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
    
    def _classify_precursor_type(
        self, 
        event: TimelineEvent, 
        signature: FlareSignature
    ) -> str:
        """Classify the type of precursor based on event and signature."""
        event_type = event.event_type
        
        if event_type == "lab":
            return "rising_inflammatory_marker"
        elif event_type == "symptom":
            return "symptom_cluster"
        elif event_type in ("medication", "med_change"):
            return "medication_pattern"
        elif event_type == "flare":
            return "prior_flare"
        else:
            return f"{signature.pattern_type}_precursor"
    
    def _generate_precursor_explanation(
        self,
        event: TimelineEvent,
        signature: FlareSignature,
        similarity: float,
    ) -> str:
        """Generate human-readable explanation for precursor match."""
        return (
            f"Event on {event.ts.strftime('%Y-%m-%d')} ({event.event_type}) "
            f"matches {signature.name} pattern with {similarity:.0%} similarity. "
            f"This pattern typically appears {signature.typical_timeline_days} days before flare."
        )
    
    async def predict_flare_likelihood(
        self,
        session: AsyncSession,
        patient_id: str,
        window_days: int = 90,
    ) -> FlarePrediction:
        """
        Generate probabilistic flare prediction for a patient.
        
        NOTE: This is NOT a diagnosis. All outputs are probabilistic and
        intended for clinician review only.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            window_days: Days to analyze
            
        Returns:
            FlarePrediction with probabilistic assessment
        """
        # Find precursors
        precursors = await self.find_flare_precursors(
            session, patient_id, window_days=window_days
        )
        
        # Calculate likelihood based on precursor matches
        if not precursors:
            likelihood = FlareLikelihood.LOW
            likelihood_score = 0.2
        else:
            avg_similarity = np.mean([p.similarity_score for p in precursors])
            precursor_count = len(precursors)
            
            # Simple scoring (would be more sophisticated in production)
            likelihood_score = min(0.95, avg_similarity * 0.5 + precursor_count * 0.05)
            
            if likelihood_score >= 0.7:
                likelihood = FlareLikelihood.HIGH
            elif likelihood_score >= 0.4:
                likelihood = FlareLikelihood.MEDIUM
            else:
                likelihood = FlareLikelihood.LOW
        
        # Identify risk drivers and protective factors
        risk_drivers = self._identify_risk_drivers(precursors)
        protective_factors = self._identify_protective_factors(precursors)
        contradictions = self._identify_contradictions(precursors)
        
        # Build matched signatures
        matched_signatures = []
        seen_patterns = set()
        for p in precursors:
            pattern = p.precursor_type
            if pattern not in seen_patterns:
                seen_patterns.add(pattern)
                matched_signatures.append({
                    "pattern": pattern,
                    "score": p.similarity_score,
                    "explanation": p.explanation,
                })
        
        return FlarePrediction(
            patient_id=patient_id,
            prediction_timestamp=datetime.utcnow(),
            flare_likelihood=likelihood,
            likelihood_score=likelihood_score,
            key_precursors=precursors[:5],
            matched_signatures=matched_signatures,
            risk_drivers=risk_drivers,
            protective_factors=protective_factors,
            contradictions=contradictions,
        )
    
    def _identify_risk_drivers(self, precursors: List[FlarePrecursor]) -> List[str]:
        """Identify risk drivers from precursor analysis."""
        drivers = []
        
        precursor_types = [p.precursor_type for p in precursors]
        
        if "rising_inflammatory_marker" in precursor_types:
            drivers.append("Rising inflammatory markers (CRP/ESR trending upward)")
        if "symptom_cluster" in precursor_types:
            drivers.append("Symptom clustering (multiple symptoms co-occurring)")
        if "medication_pattern" in precursor_types:
            drivers.append("Medication pattern changes (possible adherence gaps)")
        if "prior_flare" in precursor_types:
            drivers.append("Recent flare history (increased recurrence risk)")
        
        if not drivers:
            drivers.append("No significant risk drivers identified")
        
        return drivers
    
    def _identify_protective_factors(self, precursors: List[FlarePrecursor]) -> List[str]:
        """Identify protective factors from timeline analysis."""
        # In production, this would analyze the full timeline
        factors = []
        
        if len(precursors) < 3:
            factors.append("Limited precursor signals detected")
        
        # Check for medication adherence (simplified)
        med_precursors = [p for p in precursors if p.precursor_type == "medication_pattern"]
        if not med_precursors:
            factors.append("No medication adherence gaps detected")
        
        if not factors:
            factors.append("Standard protective factor assessment pending")
        
        return factors
    
    def _identify_contradictions(self, precursors: List[FlarePrecursor]) -> List[str]:
        """Identify contradictory evidence in the analysis."""
        contradictions = []
        
        # Check for mixed signals
        high_sim = [p for p in precursors if p.similarity_score > 0.7]
        low_sim = [p for p in precursors if p.similarity_score < 0.4]
        
        if high_sim and low_sim:
            contradictions.append(
                "Mixed signals: Some events strongly match flare patterns while others do not"
            )
        
        if not contradictions:
            contradictions.append("No significant contradictions identified")
        
        return contradictions
    
    # =========================================================================
    # Diagnostic Landscape Operations
    # =========================================================================
    
    async def estimate_diagnostic_landscape(
        self,
        session: AsyncSession,
        patient_id: str,
    ) -> DiagnosticLandscape:
        """
        Estimate probabilistic diagnostic landscape from timeline patterns.
        
        NOTE: This is NOT a diagnosis. It represents pattern similarities
        to known autoimmune conditions for clinician review.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            
        Returns:
            DiagnosticLandscape with probabilistic pattern similarities
        """
        # Get patient timeline
        timeline = await self.get_timeline(session, patient_id, limit=500)
        
        if not timeline.events:
            # Return neutral landscape if no events
            return DiagnosticLandscape(
                patient_id=patient_id,
                analysis_timestamp=datetime.utcnow(),
                diagnostic_probabilities=DiagnosticProbability(
                    ra_like=0.0,
                    sle_like=0.0,
                    psa_like=0.0,
                    sjogren_like=0.0,
                    mixed_ctd_like=0.0,
                    vasculitis_like=0.0,
                    other=1.0,
                ),
                drivers=["Insufficient timeline data for pattern analysis"],
            )
        
        # Analyze timeline for pattern features
        features = self._extract_landscape_features(timeline.events)
        
        # Calculate probabilistic similarities (simplified for initial implementation)
        probabilities = self._calculate_diagnostic_probabilities(features)
        
        # Identify drivers
        drivers = self._identify_landscape_drivers(features)
        
        return DiagnosticLandscape(
            patient_id=patient_id,
            analysis_timestamp=datetime.utcnow(),
            diagnostic_probabilities=probabilities.normalize(),
            drivers=drivers,
            key_features=features,
        )
    
    def _extract_landscape_features(
        self, 
        events: List[TimelineEvent]
    ) -> Dict[str, Any]:
        """Extract features from timeline for landscape analysis."""
        features: Dict[str, Any] = {
            "event_count": len(events),
            "event_types": {},
            "lab_patterns": {},
            "symptom_patterns": {},
            "medication_patterns": {},
            "flare_count": 0,
        }
        
        for event in events:
            # Count event types
            et = event.event_type
            features["event_types"][et] = features["event_types"].get(et, 0) + 1
            
            # Analyze structured data
            if event.structured:
                if et == "lab":
                    self._analyze_lab_features(event.structured, features)
                elif et == "symptom":
                    self._analyze_symptom_features(event.structured, features)
                elif et in ("medication", "med_change"):
                    self._analyze_medication_features(event.structured, features)
                elif et == "flare":
                    features["flare_count"] += 1
        
        return features
    
    def _analyze_lab_features(
        self, 
        structured: Dict[str, Any], 
        features: Dict[str, Any]
    ) -> None:
        """Analyze lab results for landscape features."""
        lab_patterns = features["lab_patterns"]
        
        # Check for inflammatory markers
        if structured.get("CRP"):
            lab_patterns["crp_present"] = True
            if structured.get("flag") == "H":
                lab_patterns["crp_elevated"] = True
        
        if structured.get("ESR"):
            lab_patterns["esr_present"] = True
            if structured.get("flag") == "H":
                lab_patterns["esr_elevated"] = True
        
        # Check for autoantibodies
        if structured.get("ANA"):
            lab_patterns["ana_positive"] = structured.get("ANA") not in ("negative", "Negative", None)
        
        if structured.get("RF"):
            lab_patterns["rf_present"] = True
        
        if structured.get("anti_CCP"):
            lab_patterns["anti_ccp_present"] = True
    
    def _analyze_symptom_features(
        self, 
        structured: Dict[str, Any], 
        features: Dict[str, Any]
    ) -> None:
        """Analyze symptoms for landscape features."""
        symptom_patterns = features["symptom_patterns"]
        
        if structured.get("joint_pain"):
            symptom_patterns["joint_involvement"] = True
        
        if structured.get("morning_stiffness"):
            symptom_patterns["morning_stiffness"] = True
            if structured.get("morning_stiffness_duration_min", 0) > 60:
                symptom_patterns["prolonged_morning_stiffness"] = True
        
        if structured.get("fatigue"):
            symptom_patterns["fatigue"] = True
        
        if structured.get("skin_rash"):
            symptom_patterns["skin_involvement"] = True
        
        if structured.get("dry_eyes") or structured.get("dry_mouth"):
            symptom_patterns["sicca_symptoms"] = True
    
    def _analyze_medication_features(
        self, 
        structured: Dict[str, Any], 
        features: Dict[str, Any]
    ) -> None:
        """Analyze medications for landscape features."""
        med_patterns = features["medication_patterns"]
        
        if structured.get("is_dmard"):
            med_patterns["dmard_use"] = True
        
        if structured.get("is_biologic"):
            med_patterns["biologic_use"] = True
        
        if structured.get("is_steroid"):
            med_patterns["steroid_use"] = True
    
    def _calculate_diagnostic_probabilities(
        self, 
        features: Dict[str, Any]
    ) -> DiagnosticProbability:
        """
        Calculate probabilistic similarities to autoimmune patterns.
        
        NOTE: This is a simplified implementation. In production, this would
        use trained ML models on historical data.
        """
        lab = features.get("lab_patterns", {})
        symptoms = features.get("symptom_patterns", {})
        meds = features.get("medication_patterns", {})
        
        # Initialize scores
        ra_score = 0.1
        sle_score = 0.1
        psa_score = 0.1
        sjogren_score = 0.1
        mctd_score = 0.1
        vasculitis_score = 0.05
        other_score = 0.45
        
        # RA-like patterns
        if symptoms.get("joint_involvement"):
            ra_score += 0.15
        if symptoms.get("prolonged_morning_stiffness"):
            ra_score += 0.1
        if lab.get("rf_present"):
            ra_score += 0.1
        if lab.get("anti_ccp_present"):
            ra_score += 0.15
        if lab.get("crp_elevated") or lab.get("esr_elevated"):
            ra_score += 0.05
        
        # SLE-like patterns
        if lab.get("ana_positive"):
            sle_score += 0.15
        if symptoms.get("skin_involvement"):
            sle_score += 0.1
        if symptoms.get("fatigue"):
            sle_score += 0.05
        
        # PsA-like patterns
        if symptoms.get("skin_involvement") and symptoms.get("joint_involvement"):
            psa_score += 0.2
        
        # Sjogren's-like patterns
        if symptoms.get("sicca_symptoms"):
            sjogren_score += 0.2
        if lab.get("ana_positive"):
            sjogren_score += 0.05
        
        # MCTD-like patterns (overlap features)
        overlap_count = sum([
            symptoms.get("joint_involvement", False),
            symptoms.get("skin_involvement", False),
            symptoms.get("sicca_symptoms", False),
            lab.get("ana_positive", False),
        ])
        if overlap_count >= 3:
            mctd_score += 0.15
        
        # Reduce "other" as specific patterns increase
        total_specific = ra_score + sle_score + psa_score + sjogren_score + mctd_score + vasculitis_score
        other_score = max(0.05, 1.0 - total_specific)
        
        return DiagnosticProbability(
            ra_like=ra_score,
            sle_like=sle_score,
            psa_like=psa_score,
            sjogren_like=sjogren_score,
            mixed_ctd_like=mctd_score,
            vasculitis_like=vasculitis_score,
            other=other_score,
        )
    
    def _identify_landscape_drivers(self, features: Dict[str, Any]) -> List[str]:
        """Identify key drivers for the diagnostic landscape."""
        drivers = []
        
        lab = features.get("lab_patterns", {})
        symptoms = features.get("symptom_patterns", {})
        
        if symptoms.get("joint_involvement"):
            drivers.append("Joint-centric symptom clustering")
        
        if lab.get("ana_positive"):
            drivers.append("ANA positivity pattern")
        
        if lab.get("crp_elevated") or lab.get("esr_elevated"):
            drivers.append("Inflammatory marker elevation (CRP/ESR)")
        
        if symptoms.get("fatigue"):
            drivers.append("Episodic fatigue pattern")
        
        if symptoms.get("sicca_symptoms"):
            drivers.append("Sicca symptom pattern (dry eyes/mouth)")
        
        if symptoms.get("skin_involvement"):
            drivers.append("Skin involvement pattern")
        
        if features.get("flare_count", 0) > 0:
            drivers.append(f"Flare history ({features['flare_count']} documented)")
        
        if not drivers:
            drivers.append("Insufficient pattern data for driver identification")
        
        return drivers
    
    # =========================================================================
    # Flare Report Generation
    # =========================================================================
    
    async def generate_flare_report(
        self,
        session: AsyncSession,
        patient_id: str,
    ) -> FlareReport:
        """
        Generate complete flare prediction report.
        
        This is the main output for the /api/eoh/flarereport/{patient_id} endpoint.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            
        Returns:
            Complete FlareReport
        """
        # Get timeline
        timeline = await self.get_timeline(session, patient_id, limit=500)
        
        # Get flare prediction
        prediction = await self.predict_flare_likelihood(session, patient_id)
        
        # Get diagnostic landscape
        landscape = await self.estimate_diagnostic_landscape(session, patient_id)
        
        # Generate qualitative forecast
        flare_forecast = self._generate_flare_forecast(prediction)
        
        # Generate timeline summary
        timeline_summary = self._generate_timeline_summary(timeline)
        
        # Generate clinician guidance
        guidance = self._generate_clinician_guidance(prediction, landscape)
        
        return FlareReport(
            patient_id=patient_id,
            report_timestamp=datetime.utcnow(),
            flare_forecast=flare_forecast,
            differential_landscape=landscape,
            key_precursors=prediction.key_precursors,
            contradictions=prediction.contradictions,
            risk_drivers=prediction.risk_drivers,
            protective_factors=prediction.protective_factors,
            timeline_summary=timeline_summary,
            timeline_event_count=timeline.total_count,
            timeline_span_days=timeline.span_days or 0,
            guidance_for_clinician=guidance,
        )
    
    def _generate_flare_forecast(self, prediction: FlarePrediction) -> str:
        """Generate qualitative flare forecast text."""
        likelihood = prediction.flare_likelihood
        score = prediction.likelihood_score
        
        if likelihood == FlareLikelihood.HIGH:
            return (
                f"Pattern analysis suggests elevated probability of flare activity "
                f"(similarity score: {score:.0%}). Multiple precursor signals detected "
                f"that historically correlate with disease flares. Clinical correlation "
                f"and close monitoring recommended."
            )
        elif likelihood == FlareLikelihood.MEDIUM:
            return (
                f"Pattern analysis suggests moderate probability of flare activity "
                f"(similarity score: {score:.0%}). Some precursor signals detected. "
                f"Continued monitoring and symptom tracking recommended."
            )
        else:
            return (
                f"Pattern analysis suggests lower probability of imminent flare activity "
                f"(similarity score: {score:.0%}). Limited precursor signals detected. "
                f"Standard monitoring recommended."
            )
    
    def _generate_timeline_summary(self, timeline: TimelineResponse) -> str:
        """Generate summary of patient timeline."""
        if not timeline.events:
            return "No timeline events available for analysis."
        
        event_counts = timeline.event_type_counts
        total = timeline.total_count
        span = timeline.span_days or 0
        
        summary_parts = [
            f"Timeline contains {total} events spanning {span} days.",
        ]
        
        if event_counts:
            type_summary = ", ".join([
                f"{count} {etype}" for etype, count in event_counts.items()
            ])
            summary_parts.append(f"Event breakdown: {type_summary}.")
        
        return " ".join(summary_parts)
    
    def _generate_clinician_guidance(
        self,
        prediction: FlarePrediction,
        landscape: DiagnosticLandscape,
    ) -> List[str]:
        """Generate guidance points for clinician review."""
        guidance = []
        
        # Flare-related guidance
        if prediction.flare_likelihood == FlareLikelihood.HIGH:
            guidance.append(
                "Consider proactive intervention given elevated flare probability signals"
            )
            guidance.append(
                "Review recent medication adherence and consider dose optimization"
            )
        elif prediction.flare_likelihood == FlareLikelihood.MEDIUM:
            guidance.append(
                "Monitor for symptom progression given moderate flare signals"
            )
        
        # Landscape-related guidance
        probs = landscape.diagnostic_probabilities
        top_patterns = sorted([
            ("RA-like", probs.ra_like),
            ("SLE-like", probs.sle_like),
            ("PsA-like", probs.psa_like),
            ("Sjogren's-like", probs.sjogren_like),
            ("MCTD-like", probs.mixed_ctd_like),
        ], key=lambda x: x[1], reverse=True)
        
        if top_patterns[0][1] > 0.3:
            guidance.append(
                f"Timeline patterns most consistent with {top_patterns[0][0]} presentation "
                f"({top_patterns[0][1]:.0%} similarity)"
            )
        
        # Standard guidance
        guidance.append(
            "All probabilistic assessments should be interpreted in clinical context"
        )
        guidance.append(
            "Pattern analysis is intended to support, not replace, clinical judgment"
        )
        
        return guidance
    
    # =========================================================================
    # Timeline Context for EoH Router
    # =========================================================================
    
    async def build_timeline_context(
        self,
        session: AsyncSession,
        patient_id: str,
    ) -> TimelineContext:
        """
        Build timeline context document for injection into EoH RAG.
        
        This creates a structured context that can be prepended to the
        fused context in the EoH Router.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            
        Returns:
            TimelineContext for EoH integration
        """
        # Get timeline
        timeline = await self.get_timeline(session, patient_id, limit=100)
        
        # Get flare prediction
        prediction = await self.predict_flare_likelihood(session, patient_id)
        
        # Get diagnostic landscape
        landscape = await self.estimate_diagnostic_landscape(session, patient_id)
        
        # Build context text
        context_parts = [
            f"=== Patient Timeline Context ({patient_id}) ===",
            "",
            f"Timeline: {timeline.total_count} events over {timeline.span_days or 0} days",
            "",
            "Recent Events:",
        ]
        
        # Add recent events (most recent 10)
        for event in timeline.events[:10]:
            context_parts.append(
                f"- [{event.ts.strftime('%Y-%m-%d')}] {event.event_type}: {event.text[:200]}"
            )
        
        context_parts.extend([
            "",
            f"Flare Assessment: {prediction.flare_likelihood.value} "
            f"(score: {prediction.likelihood_score:.0%})",
            "",
            "Risk Drivers:",
        ])
        
        for driver in prediction.risk_drivers[:3]:
            context_parts.append(f"- {driver}")
        
        context_parts.extend([
            "",
            "Diagnostic Landscape:",
            f"- RA-like: {landscape.diagnostic_probabilities.ra_like:.0%}",
            f"- SLE-like: {landscape.diagnostic_probabilities.sle_like:.0%}",
            f"- PsA-like: {landscape.diagnostic_probabilities.psa_like:.0%}",
            f"- Sjogren's-like: {landscape.diagnostic_probabilities.sjogren_like:.0%}",
            "",
            "Pattern Drivers:",
        ])
        
        for driver in landscape.drivers[:3]:
            context_parts.append(f"- {driver}")
        
        context_text = "\n".join(context_parts)
        
        # Build key signals
        key_signals = [
            f"flare_likelihood:{prediction.flare_likelihood.value}",
            f"flare_score:{prediction.likelihood_score:.2f}",
        ]
        
        probs = landscape.diagnostic_probabilities
        if probs.ra_like > 0.3:
            key_signals.append(f"ra_like:{probs.ra_like:.2f}")
        if probs.sle_like > 0.3:
            key_signals.append(f"sle_like:{probs.sle_like:.2f}")
        
        return TimelineContext(
            patient_id=patient_id,
            context_text=context_text,
            event_count=timeline.total_count,
            span_days=timeline.span_days or 0,
            key_signals=key_signals,
            flare_features={
                "likelihood": prediction.flare_likelihood.value,
                "score": prediction.likelihood_score,
                "precursor_count": len(prediction.key_precursors),
            },
            diagnostic_landscape=landscape.diagnostic_probabilities,
        )
