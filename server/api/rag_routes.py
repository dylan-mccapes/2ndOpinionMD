# server/api/rag_routes.py
from __future__ import annotations

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response
import asyncpg

# Reuse your hybrid helpers
from server.vectordb.hybrid_query import ann_query, bm25_query, fuse

# Optional OpenAI for embeddings (dense ANN). We degrade gracefully if unset.
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------


def _normalize_db_url(url: Optional[str]) -> str:
    if not url:
        raise HTTPException(
            500,
            {
                "code": "db_not_configured",
                "message": "DATABASE_URL not configured",
            },
        )
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def _strip(s: Optional[str]) -> str:
    return (s or "").strip()


def _csv(s: Optional[str]) -> List[str]:
    s = _strip(s)
    if not s:
        return []
    return [t.strip().lower() for t in s.split(",") if t.strip()]


def _insert_dot_icd10(code: str) -> str:
    # I214 -> I21.4 ; E119 -> E11.9 ; handles up to 7 chars
    c = code.upper().replace(".", "")
    if len(c) >= 4 and c[0].isalpha() and c[1:3].isdigit():
        return f"{c[:3]}.{c[3:]}"
    return code.upper()


def _undot_icd10(code: str) -> str:
    return code.upper().replace(".", "")


ICD10_RX = re.compile(
    r"\b([A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?)\b",
    re.IGNORECASE,
)  # (excludes U)
LOINC_RX = re.compile(r"\b(\d{2,5}-\d)\b")
SNOMED_RX = re.compile(r"\b(\d{6,18})\b")  # very loose; we only use if "snomed" is mentioned
RXNORM_HINT = re.compile(r"\brxnorm\s*:\s*([0-9]{1,9})\b", re.IGNORECASE)

# Code-gating helpers
CODE_SOURCES = {"icd10cm", "icd11", "snomed"}
TOKEN_RX = re.compile(r"[A-Za-z]{4,}")


def _tokenize_for_codes(text: str) -> set:
    return {t.lower() for t in TOKEN_RX.findall(text or "")}


# ---------------------------------------------------------------------
# MKG-first expansion: light, fast SQL lookups you already have locally
# We intentionally target tables you *do* have (ehr_mimic4.*, rag_corpus sources)
# and degrade gracefully if a table is missing.
# ---------------------------------------------------------------------


async def _kg_expand(conn: asyncpg.Connection, q: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Returns a list of 'nodes' we treat as KG seeds:
    {system, code, title, weight, origin}
    """
    seeds: List[Dict[str, Any]] = []
    q_l = (q or "").lower()

    # 1) ICD-10-CM codes explicit in text, mapped via ehr_mimic4 dictionary (present in your DB)
    icd_codes = [m.group(1).upper() for m in ICD10_RX.finditer(q or "")]
    icd_codes = list(dict.fromkeys(icd_codes))[:25]  # dedupe & cap

    if icd_codes:
        undotted = [_undot_icd10(c) for c in icd_codes]
        try:
            rows = await conn.fetch(
                """
                SELECT icd_code, long_title
                FROM ehr_mimic4.d_icd_diagnoses
                WHERE icd_code = ANY($1)
                """,
                undotted,
            )
            for r in rows:
                dot = _insert_dot_icd10(r["icd_code"])
                seeds.append(
                    {
                        "system": "ICD-10-CM",
                        "code": dot,
                        "title": r["long_title"],
                        "weight": 2.0,
                        "origin": "ehr_mimic4.d_icd_diagnoses",
                    }
                )
        except Exception as e:
            logger.info("ICD10 lookup skipped (%s)", e)

    # 2) LOINC numbers in text → look up via RAG dictionary rows (source='loinc')
    loincs = [m.group(1) for m in LOINC_RX.finditer(q or "")]
    loincs = list(dict.fromkeys(loincs))[:25]
    if loincs:
        try:
            rows = await conn.fetch(
                """
                SELECT source_id, title
                FROM public.rag_corpus
                WHERE source = 'loinc'
                  AND (source_id = ANY($1) OR title ILIKE ANY($2))
                LIMIT 200
                """,
                loincs,
                [f"%{l}%" for l in loincs],
            )
            for r in rows:
                seeds.append(
                    {
                        "system": "LOINC",
                        "code": r["source_id"],
                        "title": r["title"],
                        "weight": 1.6,
                        "origin": "rag_corpus.loinc",
                    }
                )
        except Exception as e:
            logger.info("LOINC lookup skipped (%s)", e)

    # 3) RxNorm explicit rxcui or drug keywords → via rag_corpus (source='rxnorm')
    rxnorm_match = RXNORM_HINT.search(q or "")
    if rxnorm_match:
        rxcui = rxnorm_match.group(1)
        try:
            rows = await conn.fetch(
                """
                SELECT source_id, title
                FROM public.rag_corpus
                WHERE source='rxnorm' AND (source_id = $1 OR title ILIKE $2)
                LIMIT 50
                """,
                rxcui,
                f"%{rxcui}%",
            )
            for r in rows:
                seeds.append(
                    {
                        "system": "RxNorm",
                        "code": r["source_id"],
                        "title": r["title"],
                        "weight": 1.5,
                        "origin": "rag_corpus.rxnorm",
                    }
                )
        except Exception as e:
            logger.info("RxNorm rxcui lookup skipped (%s)", e)
    else:
        # common cardio meds if present in text
        drug_hints = []
        for tok in (
            "aspirin",
            "heparin",
            "clopidogrel",
            "ticagrelor",
            "atorvastatin",
            "rosuvastatin",
        ):
            if tok in q_l:
                drug_hints.append(tok)
        if drug_hints:
            try:
                rows = await conn.fetch(
                    """
                    SELECT source_id, title
                    FROM public.rag_corpus
                    WHERE source='rxnorm'
                      AND (title ILIKE ANY($1))
                    LIMIT 200
                    """,
                    [f"%{t}%" for t in drug_hints],
                )
                for r in rows:
                    seeds.append(
                        {
                            "system": "RxNorm",
                            "code": r["source_id"],
                            "title": r["title"],
                            "weight": 1.2,
                            "origin": "rag_corpus.rxnorm",
                        }
                    )
            except Exception as e:
                logger.info("RxNorm keyword lookup skipped (%s)", e)

    # 4) Symptom keywords → pull dictionary items from rag_corpus (SNOMED, HPO) if present
    symptom_toks = []
    for tok in (
        "chest pain",
        "dyspnea",
        "shortness of breath",
        "diaphoresis",
        "nausea",
        "arm pain",
        "jaw pain",
        "ecg",
        "st depression",
        "troponin",
    ):
        if tok in q_l:
            symptom_toks.append(tok)
    if symptom_toks:
        try:
            rows = await conn.fetch(
                """
                SELECT source, source_id, title
                FROM public.rag_corpus
                WHERE source IN ('snomed','hpo','medical_knowledge')
                  AND (title ILIKE ANY($1))
                LIMIT 200
                """,
                [f"%{t}%" for t in symptom_toks],
            )
            for r in rows:
                seeds.append(
                    {
                        "system": r["source"].upper(),
                        "code": r["source_id"],
                        "title": r["title"],
                        "weight": 1.0,
                        "origin": f"rag_corpus.{r['source']}",
                    }
                )
        except Exception as e:
            logger.info("Symptom dictionary lookup skipped (%s)", e)

    # Final: dedupe by (system, code, title)
    seen = set()
    out: List[Dict[str, Any]] = []
    for s in sorted(seeds, key=lambda x: (-float(x.get("weight", 1.0)), x.get("title", ""))):
        key = (s.get("system"), s.get("code"), s.get("title"))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= max(5, min(limit, 50)):
            break
    return out


def _compose_bm25_seed(q: str, kg_hits: List[Dict[str, Any]]) -> str:
    # join query + top KG titles/codes for better BM25 recall
    parts = [q]
    for it in kg_hits[:12]:
        for k in ("title", "code"):
            v = _strip(it.get(k))
            if v:
                parts.append(v)
    return "\n".join(parts)


async def _maybe_embed(text: str) -> Optional[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    try:
        client = OpenAI(api_key=api_key)
        emb = client.embeddings.create(model=model, input=[text]).data[0].embedding
        return emb  # type: ignore
    except Exception as e:
        logger.warning("Embedding failed; continuing with BM25-only (%s)", e)
        return None


def _filter_by_sources(items: List[Dict[str, Any]], sources: List[str]) -> List[Dict[str, Any]]:
    if not sources:
        return items
    S = set(sources)
    out = []
    for it in items:
        src = (it.get("source") or "").lower()
        if src in S:
            out.append(it)
    return out


def _apply_code_match_gating(matches: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Heuristic de-noising for ICD-10-CM / ICD-11 / SNOMED mapping rows.

    - Applies only to sources in CODE_SOURCES.
    - Requires:
        * minimal final fused score per source
        * non-trivial lexical overlap with the query
      and caps rows per code source.
    """
    if not matches:
        return matches

    q_tokens = _tokenize_for_codes(query)
    if not q_tokens:
        return matches

    per_source: Dict[str, List[Dict[str, Any]]] = {}
    others: List[Dict[str, Any]] = []

    for m in matches:
        src = (m.get("source") or "").lower()
        if src in CODE_SOURCES:
            per_source.setdefault(src, []).append(m)
        else:
            others.append(m)

    if not per_source:
        return matches

    MIN_SCORE = {
        "icd10cm": 0.35,
        "icd11": 0.35,
        "snomed": 0.35,
    }
    MAX_PER_SOURCE = {
        "icd10cm": 20,
        "icd11": 20,
        "snomed": 40,
    }

    filtered: List[Dict[str, Any]] = []

    for src, rows in per_source.items():
        min_score = MIN_SCORE.get(src, 0.0)
        max_n = MAX_PER_SOURCE.get(src, len(rows))

        rows_sorted = sorted(
            rows,
            key=lambda r: float((r.get("scores") or {}).get("final", 0.0)),
            reverse=True,
        )

        kept: List[Dict[str, Any]] = []
        for row in rows_sorted:
            score = float((row.get("scores") or {}).get("final", 0.0))
            if score < min_score:
                continue

            text_bits = [row.get("title") or "", row.get("text") or ""]
            meta = row.get("meta") or {}
            for k in ("long_title", "label", "preferred_term", "description"):
                v = meta.get(k)
                if v:
                    text_bits.append(str(v))

            doc_tokens = _tokenize_for_codes(" ".join(text_bits))
            if not (q_tokens & doc_tokens):
                continue

            kept.append(row)
            if len(kept) >= max_n:
                break

        # Fail-open: if everything filters out, keep the top row for that source.
        if not kept and rows_sorted:
            kept = rows_sorted[:1]

        filtered.extend(kept)

    all_rows = others + filtered
    all_rows_sorted = sorted(
        all_rows,
        key=lambda r: float((r.get("scores") or {}).get("final", 0.0)),
        reverse=True,
    )
    return all_rows_sorted


# ---------------------------------------------------------------------
# INTERNAL: handle rag ask (used by coding endpoint too)
# ---------------------------------------------------------------------


async def _handle_rag_ask(
    q: str,
    k: int = 60,
    sources_csv: Optional[str] = None,
    debug: int = 0,
) -> Dict[str, Any]:
    if not _strip(q):
        return {"kg_hits": [], "matches": [], "ai_response": {"text": None, "model": None}}

    database_url = _normalize_db_url(os.getenv("DATABASE_URL"))
    conn = await asyncpg.connect(dsn=database_url)
    try:
        # 1) MKG-first: pull fast KG seeds via SQL
        kg_hits = await _kg_expand(conn, q, limit=min(k, 60))

        # 2) Build lexical seed (q + KG titles/codes) and (optionally) dense embedding
        q_lex = _compose_bm25_seed(q, kg_hits)
        q_emb = await _maybe_embed(q_lex)

        # 3) Hybrid retrieval
        dense_items = []
        if q_emb is not None:
            dense_items = await ann_query(conn, q_emb, max(10, min(k * 3, 180)))
        bm25_items = await bm25_query(conn, q_lex, max(10, min(k * 3, 180)))
        fused_idx_scores: List[Tuple[int, float, float]] = fuse(dense_items, bm25_items)

        # Build id->row map and apply optional source filter after fuse
        id2 = {r["id"]: r for r in (dense_items + bm25_items)}
        matches: List[Dict[str, Any]] = []
        for _id, rrf_score, final_score in fused_idx_scores:
            row = id2.get(_id)
            if not row:
                continue
            row_out = {
                "id": row.get("id"),
                "source": row.get("source"),
                "source_id": row.get("source_id"),
                "title": row.get("title"),
                "text": row.get("text"),
                "meta": row.get("meta") or row.get("metadata") or {},
                "scores": {
                    "dense": float(
                        next(
                            (r.get("dense_score", 0.0) for r in dense_items if r.get("id") == _id),
                            0.0,
                        )
                    ),
                    "bm25": float(
                        next(
                            (r.get("bm25_score", 0.0) for r in bm25_items if r.get("id") == _id),
                            0.0,
                        )
                    ),
                    "rrf": float(rrf_score),
                    "final": float(final_score),
                },
            }
            matches.append(row_out)

        sources = _csv(sources_csv)
        if sources:
            matches = _filter_by_sources(matches, sources)

        # Code-map noise gating for ICD-10-CM / ICD-11 / SNOMED
        if matches:
            matches = _apply_code_match_gating(matches, q)

        matches = matches[: max(1, min(k, 200))]

        out = {
            "kg_hits": kg_hits,
            "matches": matches,
        }
        if debug:
            out["debug"] = {"q_lex": q_lex, "dense_used": q_emb is not None}
        return out
    finally:
        await conn.close()


# ---------------------------------------------------------------------
# HTTP Endpoint
# Body: {"q": "...", "limit": 60, "sources": "icd10cm,loinc", "debug": 0}
# ---------------------------------------------------------------------


@router.post("/ask")
async def rag_ask(
    payload: Dict[str, Any] = Body(...),
    format: str = Query("json", regex="^(json)$"),
):
    q = _strip(payload.get("q"))
    limit = int(payload.get("limit") or 60)
    sources = payload.get("sources")
    debug = int(payload.get("debug") or 0)

    res = await _handle_rag_ask(q=q, k=limit, sources_csv=sources, debug=debug)
    body = json.dumps(res, indent=2 if debug else None)
    return Response(content=body, media_type="application/json")
