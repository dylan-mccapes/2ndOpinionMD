"""
ANN Index Builder
Location: server/ann/index_builder.py
Version: v100 (Cipher + Devin Method)

This module manages HNSW index building and maintenance for pgvector.

ANN Engine: pgvector HNSW
Distance metric: cosine
HNSW parameters:
- ef_search = 40
- ef_construction = 200
- M = 16

If index corruption detected:
- Rebuild full ANN index
- Log action

DO NOT change dimension, model, or HNSW params.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# HNSW Configuration (MANDATORY - DO NOT CHANGE)
# ============================================================================

HNSW_CONFIG = {
    "ef_search": 40,
    "ef_construction": 200,
    "m": 16,
    "distance_metric": "vector_cosine_ops",
    "vector_dimension": 1536,
}

# Index definitions
INDEX_DEFINITIONS = {
    "patient_timeline_embedding_idx": {
        "table": "ehr.patient_timeline",
        "column": "embedding",
        "type": "hnsw",
    },
}


# ============================================================================
# Index Management Functions
# ============================================================================

def get_create_index_sql(
    index_name: str,
    table_name: str,
    column_name: str,
    index_type: str = "hnsw",
) -> str:
    """
    Generate SQL for creating an HNSW index.
    
    Args:
        index_name: Name for the index
        table_name: Table to index
        column_name: Column containing vectors
        index_type: Index type (hnsw or ivfflat)
        
    Returns:
        SQL CREATE INDEX statement
    """
    if index_type == "hnsw":
        return f"""
CREATE INDEX IF NOT EXISTS {index_name}
ON {table_name}
USING hnsw ({column_name} {HNSW_CONFIG['distance_metric']})
WITH (
    m = {HNSW_CONFIG['m']},
    ef_construction = {HNSW_CONFIG['ef_construction']}
);
"""
    elif index_type == "ivfflat":
        return f"""
CREATE INDEX IF NOT EXISTS {index_name}
ON {table_name}
USING ivfflat ({column_name} {HNSW_CONFIG['distance_metric']})
WITH (lists = 100);
"""
    else:
        raise ValueError(f"Unknown index type: {index_type}")


def get_drop_index_sql(index_name: str) -> str:
    """
    Generate SQL for dropping an index.
    
    Args:
        index_name: Name of the index to drop
        
    Returns:
        SQL DROP INDEX statement
    """
    return f"DROP INDEX IF EXISTS {index_name};"


def get_set_ef_search_sql() -> str:
    """
    Generate SQL for setting ef_search parameter.
    
    Returns:
        SQL SET statement
    """
    return f"SET hnsw.ef_search = {HNSW_CONFIG['ef_search']};"


async def build_index(
    session: Any,
    index_name: str,
    table_name: str,
    column_name: str,
    index_type: str = "hnsw",
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Build or rebuild an ANN index.
    
    Args:
        session: Database session
        index_name: Name for the index
        table_name: Table to index
        column_name: Column containing vectors
        index_type: Index type (hnsw or ivfflat)
        force_rebuild: If True, drop and recreate index
        
    Returns:
        Result dictionary with status and timing
    """
    start_time = datetime.now(timezone.utc)
    result = {
        "index_name": index_name,
        "table_name": table_name,
        "column_name": column_name,
        "index_type": index_type,
        "status": "unknown",
        "start_time": start_time.isoformat(),
    }
    
    try:
        # Drop existing index if force rebuild
        if force_rebuild:
            logger.info(f"Dropping existing index {index_name}")
            drop_sql = get_drop_index_sql(index_name)
            await session.execute(drop_sql)
            await session.commit()
        
        # Create index
        logger.info(f"Creating index {index_name} on {table_name}.{column_name}")
        create_sql = get_create_index_sql(index_name, table_name, column_name, index_type)
        await session.execute(create_sql)
        await session.commit()
        
        # Set ef_search
        ef_sql = get_set_ef_search_sql()
        await session.execute(ef_sql)
        
        end_time = datetime.now(timezone.utc)
        result["status"] = "success"
        result["end_time"] = end_time.isoformat()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
        logger.info(f"Index {index_name} created successfully in {result['duration_seconds']:.2f}s")
        
    except Exception as e:
        logger.error(f"Failed to build index {index_name}: {e}")
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


async def check_index_health(
    session: Any,
    index_name: str,
) -> Dict[str, Any]:
    """
    Check the health of an ANN index.
    
    Args:
        session: Database session
        index_name: Name of the index to check
        
    Returns:
        Health status dictionary
    """
    result = {
        "index_name": index_name,
        "exists": False,
        "healthy": False,
        "details": {},
    }
    
    try:
        # Check if index exists
        check_sql = """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE indexname = :index_name;
        """
        row = await session.execute(check_sql, {"index_name": index_name})
        index_info = row.fetchone()
        
        if index_info:
            result["exists"] = True
            result["details"]["definition"] = index_info[1]
            
            # Check if it's an HNSW index
            if "hnsw" in index_info[1].lower():
                result["details"]["type"] = "hnsw"
                result["healthy"] = True
            elif "ivfflat" in index_info[1].lower():
                result["details"]["type"] = "ivfflat"
                result["healthy"] = True
            else:
                result["details"]["type"] = "unknown"
        
    except Exception as e:
        logger.error(f"Failed to check index health: {e}")
        result["error"] = str(e)
    
    return result


async def rebuild_if_corrupted(
    session: Any,
    index_name: str,
    table_name: str,
    column_name: str,
) -> Dict[str, Any]:
    """
    Check index health and rebuild if corrupted.
    
    Per v100 spec:
    - If index corruption detected: Rebuild full ANN index
    - Log action
    
    Args:
        session: Database session
        index_name: Name of the index
        table_name: Table containing the index
        column_name: Column containing vectors
        
    Returns:
        Result dictionary
    """
    logger.info(f"Checking index {index_name} for corruption")
    
    health = await check_index_health(session, index_name)
    
    if not health["exists"] or not health["healthy"]:
        logger.warning(f"Index {index_name} is missing or unhealthy, rebuilding")
        return await build_index(
            session,
            index_name,
            table_name,
            column_name,
            force_rebuild=True,
        )
    
    logger.info(f"Index {index_name} is healthy")
    return {
        "index_name": index_name,
        "status": "healthy",
        "action": "none",
    }


# ============================================================================
# Synchronous Versions (for non-async contexts)
# ============================================================================

def build_index_sync(
    connection: Any,
    index_name: str,
    table_name: str,
    column_name: str,
    index_type: str = "hnsw",
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Synchronous version of build_index.
    
    Args:
        connection: Database connection (psycopg2)
        index_name: Name for the index
        table_name: Table to index
        column_name: Column containing vectors
        index_type: Index type (hnsw or ivfflat)
        force_rebuild: If True, drop and recreate index
        
    Returns:
        Result dictionary with status and timing
    """
    start_time = datetime.now(timezone.utc)
    result = {
        "index_name": index_name,
        "table_name": table_name,
        "column_name": column_name,
        "index_type": index_type,
        "status": "unknown",
        "start_time": start_time.isoformat(),
    }
    
    try:
        cursor = connection.cursor()
        
        # Drop existing index if force rebuild
        if force_rebuild:
            logger.info(f"Dropping existing index {index_name}")
            drop_sql = get_drop_index_sql(index_name)
            cursor.execute(drop_sql)
            connection.commit()
        
        # Create index
        logger.info(f"Creating index {index_name} on {table_name}.{column_name}")
        create_sql = get_create_index_sql(index_name, table_name, column_name, index_type)
        cursor.execute(create_sql)
        connection.commit()
        
        # Set ef_search
        ef_sql = get_set_ef_search_sql()
        cursor.execute(ef_sql)
        
        cursor.close()
        
        end_time = datetime.now(timezone.utc)
        result["status"] = "success"
        result["end_time"] = end_time.isoformat()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
        logger.info(f"Index {index_name} created successfully in {result['duration_seconds']:.2f}s")
        
    except Exception as e:
        logger.error(f"Failed to build index {index_name}: {e}")
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


# ============================================================================
# CLI Support
# ============================================================================

def get_all_index_sql() -> str:
    """
    Get SQL for creating all required indexes.
    
    Returns:
        Combined SQL for all indexes
    """
    sql_parts = []
    
    for index_name, config in INDEX_DEFINITIONS.items():
        sql_parts.append(get_create_index_sql(
            index_name,
            config["table"],
            config["column"],
            config["type"],
        ))
    
    # Add ef_search setting
    sql_parts.append(get_set_ef_search_sql())
    
    return "\n".join(sql_parts)


if __name__ == "__main__":
    # Print SQL for manual execution
    print("-- ANN Index Creation SQL")
    print("-- Generated by server/ann/index_builder.py")
    print(f"-- HNSW Config: ef_search={HNSW_CONFIG['ef_search']}, ef_construction={HNSW_CONFIG['ef_construction']}, M={HNSW_CONFIG['m']}")
    print()
    print(get_all_index_sql())
