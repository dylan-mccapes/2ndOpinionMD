"""
ANN Utilities Module
Location: server/ann/utils.py
Version: v100 (Cipher + Devin Method)

This module provides utilities for ANN operations including:
- Vector similarity calculations
- Embedding validation
- Query helpers
- Result formatting

Embedding Model: text-embedding-3-small
Vector dimension: 1536 (MUST match schema)
Distance metric: cosine
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration (MANDATORY - DO NOT CHANGE)
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIMENSION = 1536
DISTANCE_METRIC = "cosine"


# ============================================================================
# Vector Operations
# ============================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity (0 to 1, where 1 is identical)
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
    
    # Convert to numpy for efficient computation
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine distance between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine distance (0 to 2, where 0 is identical)
    """
    return 1.0 - cosine_similarity(vec1, vec2)


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate Euclidean distance between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Euclidean distance
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
    
    a = np.array(vec1)
    b = np.array(vec2)
    
    return float(np.linalg.norm(a - b))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    Normalize a vector to unit length.
    
    Args:
        vec: Vector to normalize
        
    Returns:
        Normalized vector
    """
    a = np.array(vec)
    norm = np.linalg.norm(a)
    
    if norm == 0:
        return vec
    
    return (a / norm).tolist()


# ============================================================================
# Embedding Validation
# ============================================================================

def validate_embedding(embedding: Optional[List[float]]) -> Tuple[bool, Optional[str]]:
    """
    Validate an embedding vector.
    
    Args:
        embedding: Embedding vector to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if embedding is None:
        return False, "Embedding is None"
    
    if not isinstance(embedding, (list, tuple)):
        return False, f"Embedding must be a list, got {type(embedding)}"
    
    if len(embedding) != VECTOR_DIMENSION:
        return False, f"Embedding dimension must be {VECTOR_DIMENSION}, got {len(embedding)}"
    
    # Check for NaN or Inf values
    for i, val in enumerate(embedding):
        if not isinstance(val, (int, float)):
            return False, f"Embedding value at index {i} is not numeric: {type(val)}"
        if math.isnan(val) or math.isinf(val):
            return False, f"Embedding contains NaN or Inf at index {i}"
    
    return True, None


def validate_embeddings_batch(embeddings: List[Optional[List[float]]]) -> Dict[str, Any]:
    """
    Validate a batch of embeddings.
    
    Args:
        embeddings: List of embedding vectors
        
    Returns:
        Validation result with counts and errors
    """
    result = {
        "total": len(embeddings),
        "valid": 0,
        "invalid": 0,
        "null": 0,
        "errors": [],
    }
    
    for i, emb in enumerate(embeddings):
        if emb is None:
            result["null"] += 1
            continue
        
        is_valid, error = validate_embedding(emb)
        if is_valid:
            result["valid"] += 1
        else:
            result["invalid"] += 1
            result["errors"].append({"index": i, "error": error})
    
    return result


# ============================================================================
# Query Helpers
# ============================================================================

def format_vector_for_postgres(embedding: List[float]) -> str:
    """
    Format an embedding vector for PostgreSQL pgvector.
    
    Args:
        embedding: Embedding vector
        
    Returns:
        PostgreSQL vector literal string
    """
    return "[" + ",".join(str(v) for v in embedding) + "]"


def get_nearest_neighbors_sql(
    table_name: str = "ehr.patient_timeline",
    embedding_column: str = "embedding",
    limit: int = 10,
    where_clause: Optional[str] = None,
) -> str:
    """
    Generate SQL for nearest neighbor search.
    
    Args:
        table_name: Table to search
        embedding_column: Column containing embeddings
        limit: Number of results to return
        where_clause: Optional WHERE clause
        
    Returns:
        SQL query template (use :query_embedding parameter)
    """
    where = f"WHERE {where_clause} AND" if where_clause else "WHERE"
    
    return f"""
SELECT 
    id,
    patient_id,
    ts,
    event_type,
    source,
    structured,
    text,
    meta,
    {embedding_column} <=> :query_embedding AS distance
FROM {table_name}
{where} {embedding_column} IS NOT NULL
ORDER BY {embedding_column} <=> :query_embedding
LIMIT {limit};
"""


def get_patient_events_with_embeddings_sql(
    patient_id: str,
    table_name: str = "ehr.patient_timeline",
    limit: int = 1000,
) -> str:
    """
    Generate SQL for fetching patient events with embeddings.
    
    Args:
        patient_id: Patient identifier
        table_name: Table to query
        limit: Maximum events to return
        
    Returns:
        SQL query
    """
    return f"""
SELECT 
    id,
    patient_id,
    ts,
    event_type,
    source,
    structured,
    text,
    embedding,
    meta
FROM {table_name}
WHERE patient_id = :patient_id
ORDER BY ts DESC
LIMIT {limit};
"""


# ============================================================================
# Result Formatting
# ============================================================================

def format_ann_result(
    row: Any,
    include_embedding: bool = False,
) -> Dict[str, Any]:
    """
    Format a database row as an ANN result.
    
    Args:
        row: Database row (tuple or dict-like)
        include_embedding: Whether to include the embedding vector
        
    Returns:
        Formatted result dictionary
    """
    # Handle both tuple and dict-like rows
    if hasattr(row, "_mapping"):
        # SQLAlchemy Row
        data = dict(row._mapping)
    elif isinstance(row, dict):
        data = row
    else:
        # Assume tuple with standard column order
        data = {
            "id": row[0],
            "patient_id": row[1],
            "ts": row[2],
            "event_type": row[3],
            "source": row[4],
            "structured": row[5],
            "text": row[6],
            "meta": row[7] if len(row) > 7 else {},
            "distance": row[-1] if len(row) > 8 else None,
        }
    
    result = {
        "id": data.get("id"),
        "patient_id": data.get("patient_id"),
        "ts": data.get("ts").isoformat() if data.get("ts") else None,
        "event_type": data.get("event_type"),
        "source": data.get("source"),
        "structured": data.get("structured"),
        "text": data.get("text"),
        "meta": data.get("meta"),
    }
    
    if "distance" in data and data["distance"] is not None:
        result["distance"] = float(data["distance"])
        result["similarity"] = 1.0 - float(data["distance"])
    
    if include_embedding and "embedding" in data:
        result["embedding"] = data["embedding"]
    
    return result


def rank_results_by_relevance(
    results: List[Dict[str, Any]],
    query_embedding: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """
    Rank results by relevance (distance/similarity).
    
    Args:
        results: List of result dictionaries
        query_embedding: Optional query embedding for re-ranking
        
    Returns:
        Sorted results (most relevant first)
    """
    # If results have distance, sort by distance (ascending)
    if results and "distance" in results[0]:
        return sorted(results, key=lambda x: x.get("distance", float("inf")))
    
    # If results have similarity, sort by similarity (descending)
    if results and "similarity" in results[0]:
        return sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
    
    # No ranking info available
    return results


# ============================================================================
# Batch Operations
# ============================================================================

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_by_text(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate events by text content.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []
    
    for event in events:
        text = event.get("text", "")
        if text not in seen:
            seen.add(text)
            unique.append(event)
    
    return unique
