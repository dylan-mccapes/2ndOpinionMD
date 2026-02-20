"""
Anonymization Agent for Query Logging

Purpose: Convert clinical queries to anonymized summaries for logging
Model: GPT-4.1 (gpt-4o)
Mode: Non-blocking, parallel with embedding query
Output: Anonymized query string for logs (no PII, no PHI)

Privacy Principle:
- Queries contain patient data (symptoms, conditions, demographics)
- URL params expose queries in logs, reverse proxies, analytics
- POST body prevents URL logging BUT we still need visibility
- Solution: Anonymize queries before logging (category + type, no details)

Example:
- Input: "34 year old male with chest pain and shortness of breath for 3 days"
- Output: "symptom_query: cardiopulmonary_assessment adult_male"
"""

import logging
from typing import Optional
import asyncio

# Use shared rate-limited LLM client
from server.llm.llm_client import chat_completion_async

logger = logging.getLogger(__name__)

ANONYMIZATION_SYSTEM_PROMPT = """You are a query anonymization agent for medical logs.

Your task: Convert clinical queries into brief, anonymized categorical summaries.

Rules:
1. Remove ALL patient-specific details (age, gender if specific, symptoms, conditions)
2. Preserve query TYPE and CATEGORY only
3. Output format: "{category}: {subcategory} {modifiers}"
4. Keep it short (5-10 words max)
5. No PII, no PHI, no specific medical details

Categories:
- symptom_query (symptom assessment)
- condition_query (disease/condition lookup)
- treatment_query (medication/therapy options)
- diagnostic_query (test interpretation)
- guideline_query (clinical guideline lookup)
- coding_query (ICD/CPT/SNOMED coding)
- research_query (literature search)
- general_query (other clinical questions)

Examples:

Input: "34 year old male with chest pain and shortness of breath for 3 days"
Output: "symptom_query: cardiopulmonary_assessment adult"

Input: "What are the treatment options for stage 3 chronic kidney disease?"
Output: "treatment_query: chronic_kidney_disease stage_3"

Input: "ICD-10 code for rheumatoid arthritis with lung involvement"
Output: "coding_query: ICD10 autoimmune_rheumatic"

Input: "Latest guidelines for hypertension management in elderly patients"
Output: "guideline_query: hypertension elderly"

Input: "Interpret elevated troponin in patient with normal EKG"
Output: "diagnostic_query: cardiac_biomarkers troponin"

Output ONLY the anonymized query string. No explanation. No preamble."""


async def anonymize_query_for_logging(query: str, timeout: float = 2.0) -> str:
    """
    Anonymize a clinical query for logging purposes.
    
    Args:
        query: The original clinical query (may contain PII/PHI)
        timeout: Max time to wait for anonymization (non-blocking)
    
    Returns:
        Anonymized query string (safe for logs)
        Falls back to "query_received" if anonymization fails/times out
    """
    try:
        # Run anonymization with timeout (non-blocking, parallel with embedding)
        response = await asyncio.wait_for(
            chat_completion_async(
                model="gpt-4o",  # GPT-4.1 (faster, cheaper than 4-turbo)
                messages=[
                    {"role": "system", "content": ANONYMIZATION_SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.0,  # Deterministic categorization
                max_tokens=50,    # Short output only
            ),
            timeout=timeout
        )
        
        anonymized = response["choices"][0]["message"]["content"].strip()
        
        # Validate output (should be short, no sensitive patterns)
        if len(anonymized) > 100:
            # Too long, likely didn't follow instructions
            logger.warning(f"Anonymization output too long ({len(anonymized)} chars), using fallback")
            return "query_received: categorization_failed"
        
        return anonymized
        
    except asyncio.TimeoutError:
        logger.debug(f"Anonymization timeout after {timeout}s, using fallback")
        return "query_received: anonymization_timeout"
        
    except Exception as e:
        logger.warning(f"Anonymization error: {e}, using fallback")
        return "query_received: anonymization_error"


def anonymize_query_sync(query: str) -> str:
    """
    Synchronous wrapper for anonymization (for non-async contexts).
    Uses asyncio.run() to execute the async function.
    """
    try:
        return asyncio.run(anonymize_query_for_logging(query))
    except Exception as e:
        logger.warning(f"Sync anonymization error: {e}, using fallback")
        return "query_received: sync_anonymization_error"


# Example usage in endpoint:
#
# @router.post("/ask_stream")
# async def ask_stream(request: Request, body: AskStreamRequest, pool: Any = Depends(resolve_pg_pool)):
#     # Start anonymization in parallel (non-blocking)
#     anon_task = asyncio.create_task(anonymize_query_for_logging(body.q))
#     
#     # Continue with main retrieval path (not blocked by anonymization)
#     # ... do embedding, retrieval, etc ...
#     
#     # Get anonymized query when ready (or use fallback if still running)
#     try:
#         anon_query = await asyncio.wait_for(anon_task, timeout=0.5)
#     except asyncio.TimeoutError:
#         anon_query = "query_received: anonymization_still_processing"
#     
#     # Log with anonymized query (privacy-safe)
#     logger.info(f"Query: {anon_query}, endpoint: /ask_stream, sources: {len(db_sources)}, limit: {limit}")

