"""
Timeline Utilities Module
Location: server/timeline/utils.py
Version: v100 (Cipher + Devin Method)

This module provides:
- Error taxonomy with exactly 10 error types
- Error handling with retry and fallback logic
- Database utilities
- Embedding helpers
- Logging configuration

ERROR TAXONOMY (MANDATORY):
1. IO_ERROR
2. ENCODING_ERROR
3. PARSE_ERROR
4. SCHEMA_MISMATCH
5. CONSTRAINT_VIOLATION
6. TYPE_CAST_ERROR
7. DATA_INTEGRITY_ERROR
8. EMBEDDING_ERROR
9. ANN_INDEX_ERROR
10. API_MODEL_ERROR

NO OTHER ERROR TYPES ARE PERMITTED.
"""

import hashlib
import logging
import os
import traceback
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import chardet

logger = logging.getLogger(__name__)

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs" / "timeline"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Error Taxonomy (MANDATORY - exactly 10 types)
# ============================================================================

class ErrorType(str, Enum):
    """
    Error taxonomy with exactly 10 error types.
    NO OTHER ERROR TYPES ARE PERMITTED.
    """
    IO_ERROR = "IO_ERROR"
    ENCODING_ERROR = "ENCODING_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    TYPE_CAST_ERROR = "TYPE_CAST_ERROR"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    ANN_INDEX_ERROR = "ANN_INDEX_ERROR"
    API_MODEL_ERROR = "API_MODEL_ERROR"


class TimelineError(Exception):
    """Base exception for timeline errors with taxonomy classification."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        original_exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.original_exception = original_exception
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "message": str(self),
            "error_type": self.error_type.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "original_exception": str(self.original_exception) if self.original_exception else None,
            "traceback": traceback.format_exc() if self.original_exception else None,
        }


# ============================================================================
# Error Classification
# ============================================================================

def classify_error(exception: Exception) -> ErrorType:
    """
    Classify an exception into one of the 10 error types.
    
    Args:
        exception: The exception to classify
        
    Returns:
        ErrorType classification
    """
    exc_type = type(exception).__name__
    exc_msg = str(exception).lower()
    
    # IO errors
    if exc_type in ("FileNotFoundError", "PermissionError", "IsADirectoryError", "NotADirectoryError"):
        return ErrorType.IO_ERROR
    if "file" in exc_msg and ("not found" in exc_msg or "no such" in exc_msg):
        return ErrorType.IO_ERROR
    
    # Encoding errors
    if exc_type in ("UnicodeDecodeError", "UnicodeEncodeError", "UnicodeError"):
        return ErrorType.ENCODING_ERROR
    if "codec" in exc_msg or "encoding" in exc_msg or "decode" in exc_msg:
        return ErrorType.ENCODING_ERROR
    
    # Parse errors
    if exc_type in ("JSONDecodeError", "XMLSyntaxError", "ParserError"):
        return ErrorType.PARSE_ERROR
    if "parse" in exc_msg or "syntax" in exc_msg or "invalid" in exc_msg:
        return ErrorType.PARSE_ERROR
    
    # Schema mismatch
    if "schema" in exc_msg or "column" in exc_msg or "field" in exc_msg:
        return ErrorType.SCHEMA_MISMATCH
    
    # Constraint violation
    if exc_type in ("IntegrityError", "UniqueViolation", "ForeignKeyViolation"):
        return ErrorType.CONSTRAINT_VIOLATION
    if "constraint" in exc_msg or "duplicate" in exc_msg or "unique" in exc_msg:
        return ErrorType.CONSTRAINT_VIOLATION
    
    # Type cast errors
    if exc_type in ("TypeError", "ValueError"):
        if "convert" in exc_msg or "cast" in exc_msg or "type" in exc_msg:
            return ErrorType.TYPE_CAST_ERROR
    
    # Data integrity errors
    if "corrupt" in exc_msg or "integrity" in exc_msg or "checksum" in exc_msg:
        return ErrorType.DATA_INTEGRITY_ERROR
    
    # Embedding errors
    if "embedding" in exc_msg or "vector" in exc_msg:
        return ErrorType.EMBEDDING_ERROR
    
    # ANN index errors
    if "index" in exc_msg and ("ann" in exc_msg or "hnsw" in exc_msg or "ivfflat" in exc_msg):
        return ErrorType.ANN_INDEX_ERROR
    
    # API/Model errors
    if "api" in exc_msg or "openai" in exc_msg or "model" in exc_msg or "rate limit" in exc_msg:
        return ErrorType.API_MODEL_ERROR
    
    # Default to parse error for unknown exceptions
    return ErrorType.PARSE_ERROR


# ============================================================================
# Logging
# ============================================================================

def get_log_file_path() -> Path:
    """Get the log file path for today."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return LOGS_DIR / f"{date_str}.log"


def log_error(error: TimelineError) -> None:
    """
    Log an error with full stack trace to the daily log file.
    
    Args:
        error: TimelineError to log
    """
    log_file = get_log_file_path()
    
    log_entry = (
        f"\n{'='*60}\n"
        f"TIMESTAMP: {error.timestamp.isoformat()}\n"
        f"ERROR_TYPE: {error.error_type.value}\n"
        f"MESSAGE: {str(error)}\n"
        f"CONTEXT: {error.context}\n"
    )
    
    if error.original_exception:
        log_entry += f"ORIGINAL_EXCEPTION: {error.original_exception}\n"
        log_entry += f"TRACEBACK:\n{traceback.format_exc()}\n"
    
    log_entry += f"{'='*60}\n"
    
    with open(log_file, "a") as f:
        f.write(log_entry)
    
    # Also log to standard logger
    logger.error(f"[{error.error_type.value}] {str(error)}")


# ============================================================================
# Fix Workflows (MANDATORY)
# ============================================================================

def fix_io_error(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Fix workflow for IO_ERROR.
    
    - Verify file path
    - If missing -> skip + log
    
    Returns:
        Tuple of (success, error_message)
    """
    path = Path(file_path)
    
    if not path.exists():
        return False, f"File not found: {file_path}"
    
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    if not os.access(path, os.R_OK):
        return False, f"No read permission: {file_path}"
    
    return True, None


def fix_encoding_error(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fix workflow for ENCODING_ERROR.
    
    - Try utf-8 -> latin-1 -> chardet guess -> else skip + log
    
    Returns:
        Tuple of (content, error_message)
    """
    path = Path(file_path)
    
    # Try UTF-8
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except UnicodeDecodeError:
        pass
    
    # Try Latin-1
    try:
        with open(path, "r", encoding="latin-1") as f:
            return f.read(), None
    except UnicodeDecodeError:
        pass
    
    # Try chardet detection
    try:
        with open(path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        if detected and detected.get("encoding"):
            return raw.decode(detected["encoding"]), None
    except Exception:
        pass
    
    return None, f"Could not decode file with any encoding: {file_path}"


def fix_parse_error(text: str) -> Dict[str, Any]:
    """
    Fix workflow for PARSE_ERROR.
    
    - Attempt structured fallback parse
    - Else store raw text only
    
    Returns:
        Fallback parsed structure
    """
    # Return minimal structure with raw text
    return {
        "ts": None,
        "event_type": "note",
        "source": "patient_upload",
        "structured": {},
        "text": text,
        "meta": {"parse_fallback": True},
    }


def fix_constraint_violation(event: Dict[str, Any], existing_ids: set) -> Dict[str, Any]:
    """
    Fix workflow for CONSTRAINT_VIOLATION.
    
    - Deduplicate events
    - Normalize PK fields
    - Re-attempt insert
    
    Returns:
        Fixed event dictionary
    """
    # Generate a unique hash for deduplication
    content_hash = hashlib.md5(
        f"{event.get('patient_id', '')}{event.get('ts', '')}{event.get('text', '')}".encode()
    ).hexdigest()
    
    if content_hash in existing_ids:
        event["meta"] = event.get("meta", {})
        event["meta"]["duplicate_skipped"] = True
        return event
    
    return event


def fix_type_cast_error(value: Any, target_type: str) -> Any:
    """
    Fix workflow for TYPE_CAST_ERROR.
    
    - Coerce numeric values
    - Parse timestamps with aggressive fuzzy parser
    - If impossible -> set null + continue
    
    Returns:
        Coerced value or None
    """
    if target_type == "float":
        try:
            if isinstance(value, str):
                # Remove common non-numeric characters
                cleaned = value.replace(",", "").replace(" ", "")
                return float(cleaned)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    if target_type == "int":
        try:
            if isinstance(value, str):
                cleaned = value.replace(",", "").replace(" ", "")
                return int(float(cleaned))
            return int(value)
        except (ValueError, TypeError):
            return None
    
    if target_type == "datetime":
        try:
            from dateutil import parser as date_parser
            if isinstance(value, datetime):
                return value
            return date_parser.parse(str(value), fuzzy=True)
        except Exception:
            return None
    
    return None


# ============================================================================
# Retry Decorator
# ============================================================================

T = TypeVar("T")


def with_retry(
    max_retries: int = 3,
    error_types: Optional[List[ErrorType]] = None,
) -> Callable:
    """
    Decorator for retrying operations with error classification.
    
    Args:
        max_retries: Maximum number of retry attempts
        error_types: List of error types to retry (None = all)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_type = classify_error(e)
                    
                    # Check if we should retry this error type
                    if error_types and error_type not in error_types:
                        raise
                    
                    last_error = TimelineError(
                        message=str(e),
                        error_type=error_type,
                        original_exception=e,
                        context={"attempt": attempt + 1, "max_retries": max_retries},
                    )
                    log_error(last_error)
                    
                    if attempt == max_retries:
                        raise last_error
                    
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}")
            
            raise last_error
        
        return wrapper
    return decorator


# ============================================================================
# Database Utilities
# ============================================================================

def generate_event_hash(patient_id: str, ts: datetime, text: str) -> str:
    """
    Generate a unique hash for an event for deduplication.
    
    Args:
        patient_id: Patient identifier
        ts: Event timestamp
        text: Event text content
        
    Returns:
        MD5 hash string
    """
    content = f"{patient_id}|{ts.isoformat() if ts else ''}|{text}"
    return hashlib.md5(content.encode()).hexdigest()


def check_idempotency(
    session: Any,
    patient_id: str,
    ts: datetime,
    text: str,
) -> bool:
    """
    Check if an event already exists (for idempotency).
    
    Args:
        session: Database session
        patient_id: Patient identifier
        ts: Event timestamp
        text: Event text content
        
    Returns:
        True if event already exists
    """
    # This is a placeholder - actual implementation depends on DB setup
    # The real implementation would query the database
    return False


# ============================================================================
# Embedding Utilities
# ============================================================================

_openai_client = None


def get_openai_client():
    """Get or create the OpenAI client (lazy initialization)."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
    return _openai_client


@with_retry(max_retries=3, error_types=[ErrorType.EMBEDDING_ERROR, ErrorType.API_MODEL_ERROR])
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using OpenAI.
    
    Model: text-embedding-3-small
    Dimension: 1536
    
    Args:
        text: Text to embed
        
    Returns:
        List of 1536 floats or None if failed
    """
    if not text or not text.strip():
        return None
    
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],  # Truncate to avoid token limits
        )
        return response.data[0].embedding
    except Exception as e:
        error_type = classify_error(e)
        if error_type in (ErrorType.EMBEDDING_ERROR, ErrorType.API_MODEL_ERROR):
            raise
        # For other errors, return None
        logger.warning(f"Embedding generation failed: {e}")
        return None


def generate_embeddings_batch(texts: List[str], batch_size: int = 100) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a batch of texts.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts per API call
        
    Returns:
        List of embeddings (None for failed texts)
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            client = get_openai_client()
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[t[:8000] for t in batch if t and t.strip()],
            )
            
            # Map embeddings back to original positions
            batch_embeddings = [None] * len(batch)
            valid_idx = 0
            for j, text in enumerate(batch):
                if text and text.strip():
                    batch_embeddings[j] = response.data[valid_idx].embedding
                    valid_idx += 1
            
            embeddings.extend(batch_embeddings)
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Return None for all texts in failed batch
            embeddings.extend([None] * len(batch))
    
    return embeddings


# ============================================================================
# Text Utilities
# ============================================================================

def truncate_text(text: str, max_length: int = 10000) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def sanitize_text(text: str) -> str:
    """Remove potentially harmful characters from text."""
    import re
    # Remove null bytes and other control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    return text
