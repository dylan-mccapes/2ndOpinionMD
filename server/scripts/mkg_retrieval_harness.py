#!/usr/bin/env python3
"""
MKG retrieval test harness: one user query -> semantic (embedding_local) + TS (websearch_to_tsquery)
against ``public.rag_corpus``, then optional synthesis with Ollama (default ``eoh-qwen3-14b``).

The harness supports an optional **router-driven query expansion** stage that calls the
``eoh-llama3.2-source-router`` model first to produce an expanded ``semantic_query`` for ANN
and a list of concrete ``ts_terms`` for per-term Postgres FTS retrieval. This mirrors the
``/ask_stream`` production pattern (``extract_qna_terms`` -> ``search_source_ts_for_terms``),
which dramatically improves TS recall on dense vocabularies (RxNorm, SNOMED, LOINC).

A separate ``--synth-model`` flag (or ``OLLAMA_SYNTH_MODEL`` env) lets the final synthesis
step use a heavier model, e.g. ``eoh-llama:70b``, without rerunning retrieval.

Default strategy:
  - source-router ON (eoh-llama3.2-source-router)
  - two-pass synthesis OFF (can be enabled via --two-pass-synth)
  - synthesis model defaults to eoh-qwen3-14b

Env (same as portal embed scripts):
  SYNC_DATABASE_URL or DATABASE_URL
  LOCAL_EMBED_MODEL — default BAAI/bge-base-en-v1.5
  OLLAMA_URL — default http://127.0.0.1:11434
  OLLAMA_MODEL — default eoh-qwen3-14b
  OLLAMA_SYNTH_MODEL — optional override for the synthesis step (e.g. eoh-llama:70b)
  OLLAMA_NUM_CTX — synthesis context size (default 61440, ~60% of 102400 Modelfile window)
  EOH_SOURCE_ROUTER_MODEL — default eoh-llama3.2-source-router

Examples::

  python server/scripts/mkg_retrieval_harness.py \\
    "type 2 diabetes metformin first line" --use-router --synth-model eoh-llama:70b

  python server/scripts/mkg_retrieval_harness.py \\
    "KDIGO CKD staging eGFR" --top-k 8 --no-llm

  python server/scripts/mkg_retrieval_harness.py \\
    "LOINC hemoglobin" --sources icd10cm,loinc --out /tmp/mkg_run.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.mkg.portalnode_pilot_sources import pilot_source_descriptions

# One SentenceTransformer per (model_name, device) per process — reloading every
# embed_query() call thrashed VRAM and slowed downstream Ollama generations.
_EMBED_LOCK = threading.Lock()
_EMBED_MODEL_CACHE: Dict[Tuple[str, str], Any] = {}


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def _dsn() -> str:
    for k in ("SYNC_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
        v = os.environ.get(k)
        if v and v.strip():
            _log("🔐", f"Using database URL from {k}")
            return v.strip()
    print("Set SYNC_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)


def _vec_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


def _ollama_chat(
    url: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    timeout: float,
    temperature: float,
    num_ctx: Optional[int] = None,
) -> str:
    import requests

    if num_ctx is None:
        num_ctx = max(2048, int(os.environ.get("OLLAMA_NUM_CTX", "61440")))
    else:
        num_ctx = max(2048, int(num_ctx))
    _log("🤖", f"Calling Ollama model={model} num_ctx={num_ctx} timeout={timeout:.0f}s")
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    r = requests.post(f"{url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return (data.get("message") or {}).get("content") or ""


def _overlap(semantic_ids: List[int], ts_ids: List[int]) -> Dict[str, Any]:
    sa, sb = set(semantic_ids), set(ts_ids)
    inter = sa & sb
    return {
        "semantic_only": sorted(sa - sb),
        "ts_only": sorted(sb - sa),
        "both": sorted(inter),
        "jaccard": (len(inter) / len(sa | sb)) if (sa | sb) else 0.0,
    }


def _compact_hit(row: Dict[str, Any], *, text_chars: int) -> Dict[str, Any]:
    text = row.get("text") or ""
    if len(text) > text_chars:
        text = text[: text_chars - 12] + "…[truncated]"
    return {
        "id": int(row["id"]),
        "source": row.get("source"),
        "source_id": row.get("source_id"),
        "title": row.get("title"),
        "text": text,
        "score": float(row.get("score") or 0.0),
    }


def ann_local(
    cur,
    emb_literal: str,
    top_k: int,
    *,
    sources: Optional[List[str]],
) -> List[Dict[str, Any]]:
    if sources:
        cur.execute(
            """
            SELECT id, source, source_id, title, text,
                   1 - (embedding_local <=> %s::vector) AS score
            FROM public.rag_corpus
            WHERE embedding_local IS NOT NULL
              AND source = ANY(%s)
            ORDER BY embedding_local <=> %s::vector
            LIMIT %s
            """,
            (emb_literal, sources, emb_literal, top_k),
        )
    else:
        cur.execute(
            """
            SELECT id, source, source_id, title, text,
                   1 - (embedding_local <=> %s::vector) AS score
            FROM public.rag_corpus
            WHERE embedding_local IS NOT NULL
            ORDER BY embedding_local <=> %s::vector
            LIMIT %s
            """,
            (emb_literal, emb_literal, top_k),
        )
    return list(cur.fetchall())


_TS_STOPWORDS = {
    "with", "from", "that", "this", "have", "what", "does", "when", "where",
    "should", "which", "their", "there", "about", "using", "type", "stage",
    "after", "will", "would", "could", "first", "second", "third", "patient",
    "patients", "clinical", "medical", "management", "treatment", "diagnosis",
}


def bm25_ts(cur, q: str, top_k: int, *, sources: Optional[List[str]]) -> List[Dict[str, Any]]:
    """TS retrieval with three-tier fallback for better recall.

    IMPORTANT: ts column is built by the rag_corpus_tsv_update trigger using
    'public.simple_unaccent' (no stemming).  Queries MUST use the same config —
    'english' config would stem terms (diabetes -> diabet) causing zero matches.

    Tier 1  - websearch_to_tsquery/simple_unaccent on full query (OR-friendly)
    Tier 2  - auto-extracted key terms OR-joined via websearch_to_tsquery
    Tier 3  - single highest-signal noun anchor
    """
    # Use the same FTS config the ts column was built with.
    # simple_unaccent = pg_catalog.simple + unaccent dict (lowercase, strip accents, no stemming).
    TS_CFG = "public.simple_unaccent"

    def _exec(tsq_fn: str, tsq_arg: str) -> List[Dict[str, Any]]:
        sql_base = (
            f"SELECT id, source, source_id, title, text, "
            f"ts_rank(ts, {tsq_fn}('{TS_CFG}', %s)) AS score "
            f"FROM public.rag_corpus "
            f"WHERE ts @@ {tsq_fn}('{TS_CFG}', %s)"
        )
        if sources:
            cur.execute(sql_base + " AND source = ANY(%s) ORDER BY score DESC LIMIT %s",
                        (tsq_arg, tsq_arg, sources, top_k))
        else:
            cur.execute(sql_base + " ORDER BY score DESC LIMIT %s",
                        (tsq_arg, tsq_arg, top_k))
        return list(cur.fetchall())

    # Tier 1: websearch_to_tsquery - OR-style matching over the full query
    rows = _exec("websearch_to_tsquery", q)
    if rows:
        return rows

    _log("🔤", "TS tier-1 miss; extracting key terms for OR-expansion")

    # Extract significant tokens (>=4 chars, alpha only, not stopwords)
    tokens = [re.sub(r"[^a-z]", "", w.lower()) for w in q.split()]
    key = [t for t in tokens if len(t) >= 4 and t not in _TS_STOPWORDS and t.isalpha()]

    # Tier 2: OR-join up to 8 key terms via websearch_to_tsquery
    if key:
        expanded = " OR ".join(key[:8])
        rows = _exec("websearch_to_tsquery", expanded)
        if rows:
            return rows

        # Tier 3: highest-signal single term (longest)
        anchor = sorted(key, key=len, reverse=True)[0]
        _log("🔤", f"TS tier-2 miss; trying single-term anchor: {anchor!r}")
        rows = _exec("websearch_to_tsquery", anchor)

    return rows


def bm25_ts_terms(
    cur,
    terms: List[str],
    top_k: int,
    *,
    sources: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Per-term TS retrieval (mirrors ``/ask_stream``'s ``search_source_ts_for_terms``).

    Runs one ``websearch_to_tsquery('public.simple_unaccent', term)`` per expanded term,
    then merges results by max ``ts_rank``. This dramatically cuts recall noise on dense
    code vocabularies (RxNorm, SNOMED, LOINC) versus a single OR-joined mega-query.
    """
    TS_CFG = "public.simple_unaccent"
    cleaned = [t.strip() for t in (terms or []) if t and t.strip()]
    if not cleaned:
        return []

    per_term_limit = max(3, top_k // max(1, len(cleaned)))
    sql_base = (
        f"SELECT id, source, source_id, title, text, "
        f"ts_rank(ts, websearch_to_tsquery('{TS_CFG}', %s)) AS score "
        f"FROM public.rag_corpus "
        f"WHERE ts @@ websearch_to_tsquery('{TS_CFG}', %s)"
    )
    if sources:
        sql = sql_base + " AND source = ANY(%s) ORDER BY score DESC LIMIT %s"
    else:
        sql = sql_base + " ORDER BY score DESC LIMIT %s"

    combined: Dict[Any, Dict[str, Any]] = {}
    for term in cleaned:
        try:
            if sources:
                cur.execute(sql, (term, term, sources, per_term_limit))
            else:
                cur.execute(sql, (term, term, per_term_limit))
            rows = list(cur.fetchall())
        except Exception as exc:  # noqa: BLE001
            _log("⚠️", f"TS per-term query failed for {term!r}: {exc}")
            continue
        for r in rows:
            rid = r["id"]
            score = float(r.get("score") or 0.0)
            existing = combined.get(rid)
            if existing is None or score > float(existing.get("score") or 0.0):
                combined[rid] = dict(r)

    merged = sorted(combined.values(), key=lambda r: float(r.get("score") or 0.0), reverse=True)
    return merged[:top_k]


def _norm_rag_source(row: Dict[str, Any]) -> str:
    return str(row.get("source") or "").strip().lower()


def _dedupe_hits_keep_best_score(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        rid = r.get("id")
        if rid is None:
            continue
        cur = by_id.get(rid)
        if cur is None or float(r.get("score") or 0.0) > float(cur.get("score") or 0.0):
            by_id[rid] = dict(r)
    return sorted(by_id.values(), key=lambda r: float(r.get("score") or 0.0), reverse=True)


def _truncate_lane_preserving_pins(
    sorted_rows: List[Dict[str, Any]],
    pinned_ids: set,
    cap: int,
) -> List[Dict[str, Any]]:
    if not sorted_rows:
        return []
    cap = max(int(cap), len(pinned_ids))
    pinned = [r for r in sorted_rows if r.get("id") in pinned_ids]
    rest = [r for r in sorted_rows if r.get("id") not in pinned_ids]
    pinned.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
    out = pinned + rest
    return out[:cap]


def ensure_source_coverage_retrieval(
    cur,
    emb_literal: str,
    sem_rows: List[Dict[str, Any]],
    ts_rows: List[Dict[str, Any]],
    *,
    required_sources: Optional[Sequence[str]],
    ts_terms: List[str],
    ts_query_fallback: str,
    top_k: int,
    min_ann_score: float,
    min_ts_score: float,
    per_source_fetch_limit: int = 16,
    per_source_ts_terms: Optional[Dict[str, List[str]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Ensure each required corpus ``source`` contributes at least one lane hit when a qualifying row exists.

    Qualifying rows must meet lane-specific score floors (ANN: cosine-style ``1 - distance``;
    TS: ``ts_rank``). If the global top-``top_k`` lanes omit a source, runs a targeted ANN/TS fetch
    for that source only and pins the best qualifying row into the corresponding lane.

    Returns updated ``(sem_rows, ts_rows, stats)``.
    """
    stats: Dict[str, Any] = {
        "enabled": True,
        "requested_sources": [],
        "min_ann_score": float(min_ann_score),
        "min_ts_score": float(min_ts_score),
        "per_source_fetch_limit": int(per_source_fetch_limit),
        "pinned_semantic_ids": [],
        "pinned_ts_ids": [],
        "satisfied_sources": [],
        "missing_sources": [],
        "extra_ann_fetches": 0,
        "extra_ts_fetches": 0,
    }
    if not required_sources:
        stats["enabled"] = False
        stats["skipped_reason"] = "no_required_sources"
        return sem_rows, ts_rows, stats

    req = []
    seen: set[str] = set()
    for s in required_sources:
        k = str(s or "").strip().lower()
        if k and k not in seen:
            seen.add(k)
            req.append(k)
    stats["requested_sources"] = list(req)
    if not req:
        stats["enabled"] = False
        stats["skipped_reason"] = "empty_required_sources"
        return sem_rows, ts_rows, stats

    sem_work = [dict(r) for r in sem_rows]
    ts_work = [dict(r) for r in ts_rows]
    pinned_sem_ids: set = set()
    pinned_ts_ids: set = set()
    satisfied: List[str] = []
    missing: List[str] = []

    def _best_sem(src: str) -> Optional[Dict[str, Any]]:
        rows = [
            r
            for r in sem_work
            if _norm_rag_source(r) == src and float(r.get("score") or 0.0) >= float(min_ann_score)
        ]
        if not rows:
            return None
        return max(rows, key=lambda r: float(r.get("score") or 0.0))

    def _best_ts(src: str) -> Optional[Dict[str, Any]]:
        rows = [
            r
            for r in ts_work
            if _norm_rag_source(r) == src and float(r.get("score") or 0.0) >= float(min_ts_score)
        ]
        if not rows:
            return None
        return max(rows, key=lambda r: float(r.get("score") or 0.0))

    ts_q = (ts_query_fallback or "").strip()

    for src in req:
        bs = _best_sem(src)
        bt = _best_ts(src)
        if bs:
            pinned_sem_ids.add(int(bs["id"]))
            satisfied.append(src)
            continue
        if bt:
            pinned_ts_ids.add(int(bt["id"]))
            satisfied.append(src)
            continue

        fetched_sem = ann_local(cur, emb_literal, per_source_fetch_limit, sources=[src])
        fetched_sem.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
        picked = None
        for r in fetched_sem:
            if float(r.get("score") or 0.0) >= float(min_ann_score):
                picked = dict(r)
                break
        if picked:
            sem_work.append(picked)
            pinned_sem_ids.add(int(picked["id"]))
            stats["extra_ann_fetches"] += 1
            satisfied.append(src)
            continue

        # Prefer source-specific ts_terms when the router supplied them.
        per_src_terms = (per_source_ts_terms or {}).get(src) if per_source_ts_terms else None
        if per_src_terms:
            fetched_ts = bm25_ts_terms(cur, per_src_terms, per_source_fetch_limit, sources=[src])
        elif ts_terms:
            fetched_ts = bm25_ts_terms(cur, ts_terms, per_source_fetch_limit, sources=[src])
        elif ts_q:
            fetched_ts = bm25_ts(cur, ts_q, per_source_fetch_limit, sources=[src])
        else:
            fetched_ts = []
        fetched_ts.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
        picked_ts = None
        for r in fetched_ts:
            if float(r.get("score") or 0.0) >= float(min_ts_score):
                picked_ts = dict(r)
                break
        if picked_ts:
            ts_work.append(picked_ts)
            pinned_ts_ids.add(int(picked_ts["id"]))
            stats["extra_ts_fetches"] += 1
            satisfied.append(src)
            continue

        missing.append(src)

    lane_cap = max(int(top_k), len(req))
    sem_dedup = _dedupe_hits_keep_best_score(sem_work)
    ts_dedup = _dedupe_hits_keep_best_score(ts_work)
    sem_out = _truncate_lane_preserving_pins(sem_dedup, pinned_sem_ids, lane_cap)
    ts_out = _truncate_lane_preserving_pins(ts_dedup, pinned_ts_ids, lane_cap)

    stats["pinned_semantic_ids"] = sorted(pinned_sem_ids)
    stats["pinned_ts_ids"] = sorted(pinned_ts_ids)
    stats["satisfied_sources"] = satisfied
    stats["missing_sources"] = missing
    stats["lane_cap"] = lane_cap
    return sem_out, ts_out, stats


# --------------------------------------------------------------------------- #
# Bayesian-prior lookup over rag_corpus
# --------------------------------------------------------------------------- #
#
# Per ``reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md`` §4–§7, population priors
# for the Beta–Bernoulli flare / progression / taper updates should come from
# MKG (or the cohort itself), versioned and provenance-stamped. Phase 1 of the
# pilot ships the *plumbing* but defaults to weak Beta priors when no
# population statistics are configured. The function below is the single place
# the chatbot / toolkit calls when it wants an MKG-informed prior — it returns
# either an MKG prior (with ``source: "mkg"``) or ``None``, never raises.
#
# MKG priors are stored next to the retrieval index in a small JSON sidecar
# table: ``public.mkg_bayes_priors`` (keyed by hypothesis_id × cohort_strata).
# When that table does not exist, this function returns ``None`` cleanly so
# the caller falls back to the strategy-doc default weak priors.

_MKG_PRIORS_TABLE = "public.mkg_bayes_priors"


def fetch_mkg_bayes_prior(
    hypothesis_id: str,
    *,
    cohort_strata: Optional[Dict[str, Any]] = None,
    dsn: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Look up a population prior for ``hypothesis_id`` in the MKG sidecar table.

    ``cohort_strata`` is a dict of stratum keys (``icd_family``, ``age_band``,
    ``sex``); only keys with non-null values are used, and lookup walks from
    most-specific (all keys) to least-specific (no keys) until a row matches.

    Returns a dict with ``family`` / ``alpha`` / ``beta`` / ``mu`` / ``sigma``
    fields plus ``source: "mkg"`` and provenance breadcrumbs, or ``None``.

    This function is **safe**: any DB error or missing table returns ``None``
    so callers can fall back to weak priors deterministically.
    """
    if not hypothesis_id:
        return None
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception:  # pragma: no cover
        return None

    target_dsn = dsn
    if not target_dsn:
        for k in ("SYNC_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
            v = os.environ.get(k)
            if v and v.strip():
                target_dsn = v.strip()
                break
    if not target_dsn:
        return None

    strata = {k: v for k, v in (cohort_strata or {}).items() if v is not None and str(v).strip()}
    candidates: List[Dict[str, Any]] = []
    keys = sorted(strata.keys())
    n = len(keys)
    # Walk from most-specific (all keys) to least-specific (none).
    for r in range(n, -1, -1):
        from itertools import combinations

        for combo in combinations(keys, r):
            candidates.append({k: strata[k] for k in combo})

    try:
        with psycopg.connect(target_dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '5s';")
                cur.execute(
                    "SELECT to_regclass(%s) IS NOT NULL AS exists", (_MKG_PRIORS_TABLE,)
                )
                exists = (cur.fetchone() or {}).get("exists")
                if not exists:
                    return None
                for cand in candidates:
                    sql = (
                        f"SELECT family, alpha, beta, mu, sigma, sigma_obs, source, notes, "
                        f"cohort_strata, version, updated_at "
                        f"FROM {_MKG_PRIORS_TABLE} "
                        f"WHERE hypothesis_id = %s AND cohort_strata = %s::jsonb "
                        f"ORDER BY updated_at DESC NULLS LAST LIMIT 1"
                    )
                    cur.execute(sql, (hypothesis_id, json.dumps(cand, sort_keys=True)))
                    row = cur.fetchone()
                    if row:
                        out = {
                            "family": str(row.get("family") or "beta"),
                            "alpha": (
                                float(row["alpha"])
                                if row.get("alpha") is not None
                                else None
                            ),
                            "beta": (
                                float(row["beta"]) if row.get("beta") is not None else None
                            ),
                            "mu": (
                                float(row["mu"]) if row.get("mu") is not None else None
                            ),
                            "sigma": (
                                float(row["sigma"]) if row.get("sigma") is not None else None
                            ),
                            "sigma_obs": (
                                float(row["sigma_obs"])
                                if row.get("sigma_obs") is not None
                                else None
                            ),
                            "source": str(row.get("source") or "mkg"),
                            "notes": (
                                f"MKG prior version={row.get('version')!r} "
                                f"strata={row.get('cohort_strata')!r} "
                                f"updated_at={row.get('updated_at')!r}"
                            ),
                        }
                        # Drop None entries so callers see a clean override dict.
                        return {k: v for k, v in out.items() if v is not None}
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"fetch_mkg_bayes_prior: {exc}")
        return None
    return None


def embed_query(model_name: str, text: str) -> Tuple[List[float], str]:
    from sentence_transformers import SentenceTransformer
    import torch

    device = os.environ.get("LOCAL_EMBED_DEVICE")
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    key = (model_name, device)
    with _EMBED_LOCK:
        st = _EMBED_MODEL_CACHE.get(key)
        if st is None:
            _log("🧠", f"Loading embedding model={model_name} on device={device} (process cache)")
            st = SentenceTransformer(model_name, device=device)
            _EMBED_MODEL_CACHE[key] = st
    _log("📐", f"Embedding query ({len(text)} chars)")
    v = st.encode(
        [text],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    return [float(x) for x in v.tolist()], device


def run_llm(
    *,
    query: str,
    semantic_hits: List[Dict[str, Any]],
    ts_hits: List[Dict[str, Any]],
    overlap: Dict[str, Any],
    source_reference: Dict[str, str],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    route_plan: Optional[Dict[str, Any]] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    extra_context_label: str = "patient_timeline_summary",
    num_ctx: Optional[int] = None,
) -> Dict[str, Any]:
    _log("🧾", "Preparing retrieval bundle for LLM analysis")
    bundle: Dict[str, Any] = {
        "user_query": query,
        "semantic_lane": "embedding_local + BGE (cosine) — query may be router-rewritten",
        "ts_lane": "websearch_to_tsquery('public.simple_unaccent', term) per expanded ts_term + ts_rank",
        "rag_source_reference": source_reference,
        "semantic_hits": semantic_hits,
        "ts_hits": ts_hits,
        "id_overlap": overlap,
    }
    if route_plan:
        bundle["router_plan"] = {
            k: route_plan.get(k)
            for k in (
                "model",
                "elapsed_sec",
                "question_type",
                "semantic_query",
                "ts_query",
                "ts_terms",
                "selected_sources",
                "selected_modules",
                "notes",
                "error",
            )
            if route_plan.get(k) is not None
        }
    if extra_context:
        # Hard cap so a long PTV summary cannot blow synthesis context.
        ec = dict(extra_context)
        for k, v in list(ec.items()):
            if isinstance(v, str) and len(v) > 8000:
                ec[k] = v[:8000] + "\n…[truncated]"
        bundle[extra_context_label] = ec
    has_extra = bool(extra_context)
    if has_extra:
        system = (
            "You are a rheumatology clinical decision support assistant.\n\n"
            f"You are given a patient trajectory summary in `{extra_context_label}` from an internal "
            "3-agent PTV analysis, plus relevant external medical knowledge hits (guidelines, drug "
            "information, and related evidence) from rag_corpus.\n\n"
            "Task: Produce a single, concise, professional clinical summary (maximum 650 words) of "
            "the patient's five-year FORWARD trajectory.\n\n"
            "Structure exactly as follows (use these exact section headings):\n"
            "1. **Trajectory Overview**\n"
            "2. **Flares & Treatment Changes**\n"
            "3. **Uncertainty Carriers**\n"
            "4. **Integrated Recommendation**\n\n"
            "Section requirements:\n"
            "- 1. Trajectory Overview: one paragraph summarizing the five-year course, including key "
            "trends in symptoms and function.\n"
            "- 2. Flares & Treatment Changes: list all flares with dates, any treatment escalations "
            "or de-escalations, and clinical rationale. Cite specific PTV event_ids.\n"
            "- 3. Uncertainty Carriers: highlight notable widenings (e.g., flare probability bands, "
            "missing data, CKD/creatinine trends) and implications.\n"
            "- 4. Integrated Recommendation: one short paragraph with a clear, evidence-backed "
            "monitoring/management suggestion grounded in both the PTV trajectory and external "
            "guideline evidence.\n\n"
            "Rules:\n"
            "1) Use formal but approachable clinical language.\n"
            "2) Always cite PTV event_ids when referencing specific patient events.\n"
            "3) Ground guideline/medical claims in provided rag_corpus evidence ids/sources.\n"
            "4) Do NOT mention retrieval methods, overlap scores, lane names, 'best hit', router, "
            "or internal tooling.\n"
            "5) Do not add generic disclaimers unless clinically required.\n"
            "6) Do not fabricate events, ids, drug facts, doses, or guideline statements."
        )
    else:
        system = (
            "You are a senior clinical informatics assistant. Produce a REPORT that directly answers "
            "the user's query using the JSON bundle (semantic lane + Postgres FTS lane + rag_source_reference). "
            "Write for a clinician: concise, actionable, and grounded only in evidence present in the hits.\n\n"
            "STYLE:\n"
            "- Lead with the answer — do not open with retrieval mechanics.\n"
            "- Synthesize across hits and sources; integrate conflicting signals instead of listing \"best hit\".\n"
            "- For therapy/guideline questions: state first-line and reasonable alternatives when supported; "
            "note monitoring, contraindications, or dose caveats only if they appear in the hits.\n"
            "- Mention lane agreement/divergence only briefly when it affects clinical confidence.\n\n"
            "OUTPUT MARKDOWN — use exactly these section headings:\n"
            "## Direct answer\n"
            "## Supporting evidence\n"
            "## Guideline / therapeutic highlights\n"
            "## Gaps, contradictions, or uncertainty\n\n"
            "RULES:\n"
            "1. When stating patient-agnostic facts tied to a chunk, cite its ``id`` from semantic_hits or ts_hits.\n"
            "2. Do NOT copy long passages verbatim — paraphrase and synthesize.\n"
            "3. If a lane is empty or clearly off-topic, say so in one short clause; do not pad.\n"
            "4. Stay under ~750 words unless the query clearly needs more.\n"
            "5. Do not mention internal pipeline names (BGE, router, overlap scores) unless needed for a caveat.\n"
            "6. Only reference ids present in the JSON.\n"
        )
    user = (
        "Answer the user's query using this retrieval bundle as your sole evidence base.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )[:50000]
    t0 = time.monotonic()
    text = _ollama_chat(
        ollama_url,
        model,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        timeout=timeout,
        temperature=temperature,
        num_ctx=num_ctx,
    )
    return {
        "model": model,
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "markdown": text,
        "had_extra_context": has_extra,
    }


def _pick_fallback_evidence(
    semantic_hits: List[Dict[str, Any]],
    ts_hits: List[Dict[str, Any]],
    *,
    k: int,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for lane, hits in (("semantic", semantic_hits), ("ts", ts_hits)):
        for h in hits:
            merged.append(
                {
                    "lane": lane,
                    "id": int(h.get("id")),
                    "source": h.get("source"),
                    "source_id": h.get("source_id"),
                    "title": h.get("title"),
                    "score": float(h.get("score") or 0.0),
                    "rationale": "fallback top-scoring hit",
                }
            )
    merged.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    out: List[Dict[str, Any]] = []
    seen = set()
    for ev in merged:
        key = (ev["lane"], ev["id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
        if len(out) >= k:
            break
    return out


def run_llm_two_pass(
    *,
    query: str,
    semantic_hits: List[Dict[str, Any]],
    ts_hits: List[Dict[str, Any]],
    overlap: Dict[str, Any],
    source_reference: Dict[str, str],
    ollama_url: str,
    compress_model: str,
    synth_model: str,
    temperature: float,
    timeout: float,
    route_plan: Optional[Dict[str, Any]] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    extra_context_label: str = "patient_timeline_summary",
    compress_num_ctx: Optional[int] = None,
    synth_num_ctx: Optional[int] = None,
    compress_evidence_k: int = 8,
) -> Dict[str, Any]:
    """Two-pass synthesis: compress (summary + top evidence) -> final synthesis."""
    _log("🧩", f"Two-pass synth enabled (compress={compress_model} -> synth={synth_model})")
    bundle: Dict[str, Any] = {
        "user_query": query,
        "semantic_hits": semantic_hits,
        "ts_hits": ts_hits,
        "id_overlap": overlap,
    }
    if route_plan:
        bundle["router_plan"] = route_plan
    if extra_context:
        bundle[extra_context_label] = extra_context

    pass1_system = (
        "You are a clinical evidence compressor for RAG. You receive JSON with a user query and two "
        "retrieval lanes (semantic + ts). Return STRICT JSON only with keys:\n"
        "- summary: concise synthesis (<=220 words)\n"
        "- top_evidence: list (max "
        + str(max(1, compress_evidence_k))
        + ") of objects: {lane, id, source, source_id, title, rationale}\n"
        "Rules:\n"
        "1) Evidence ids must exist in provided hits.\n"
        "2) Prioritize diversity across sources and include the strongest contradictory/qualifying evidence.\n"
        "3) No markdown. JSON only."
    )
    pass1_user = json.dumps(bundle, indent=2, default=str)[:50000]
    t1 = time.monotonic()
    raw_pass1 = _ollama_chat(
        ollama_url,
        compress_model,
        [{"role": "system", "content": pass1_system}, {"role": "user", "content": pass1_user}],
        timeout=timeout,
        temperature=temperature,
        num_ctx=compress_num_ctx,
    )
    pass1_elapsed = round(time.monotonic() - t1, 3)

    parsed: Dict[str, Any] = {}
    parse_error: Optional[str] = None
    try:
        parsed = json.loads(raw_pass1)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw_pass1)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception as exc:  # noqa: BLE001
                parse_error = str(exc)
        else:
            parse_error = "no_json_object_found"

    summary_text = str(parsed.get("summary") or "").strip()
    selected = parsed.get("top_evidence") if isinstance(parsed.get("top_evidence"), list) else []

    sem_by_id = {int(h["id"]): h for h in semantic_hits if h.get("id") is not None}
    ts_by_id = {int(h["id"]): h for h in ts_hits if h.get("id") is not None}
    selected_evidence: List[Dict[str, Any]] = []
    reduced_sem: List[Dict[str, Any]] = []
    reduced_ts: List[Dict[str, Any]] = []
    seen_sel = set()

    for item in selected:
        try:
            lane = str(item.get("lane") or "").strip().lower()
            rid = int(item.get("id"))
        except Exception:
            continue
        key = (lane, rid)
        if key in seen_sel:
            continue
        hit = sem_by_id.get(rid) if lane == "semantic" else ts_by_id.get(rid) if lane == "ts" else None
        if not hit:
            continue
        seen_sel.add(key)
        selected_evidence.append(
            {
                "lane": lane,
                "id": rid,
                "source": hit.get("source"),
                "source_id": hit.get("source_id"),
                "title": hit.get("title"),
                "score": float(hit.get("score") or 0.0),
                "rationale": str(item.get("rationale") or "")[:220],
            }
        )
        if lane == "semantic":
            reduced_sem.append(hit)
        elif lane == "ts":
            reduced_ts.append(hit)
        if len(selected_evidence) >= max(1, compress_evidence_k):
            break

    if not selected_evidence:
        _log("⚠️", "Two-pass compressor returned no valid evidence; using score fallback")
        selected_evidence = _pick_fallback_evidence(
            semantic_hits,
            ts_hits,
            k=max(1, compress_evidence_k),
        )
        reduced_sem = [sem_by_id[e["id"]] for e in selected_evidence if e["lane"] == "semantic" and e["id"] in sem_by_id]
        reduced_ts = [ts_by_id[e["id"]] for e in selected_evidence if e["lane"] == "ts" and e["id"] in ts_by_id]

    if not summary_text:
        summary_text = "Compression pass produced no summary text."

    dossier = {
        "summary": summary_text,
        "top_evidence": selected_evidence,
        "n_selected": len(selected_evidence),
        "compress_model": compress_model,
        "compress_elapsed_sec": pass1_elapsed,
    }
    merged_extra = dict(extra_context) if extra_context else {}
    merged_extra["two_pass_dossier"] = dossier
    merged_extra["two_pass_raw_summary"] = summary_text

    reduced_overlap = _overlap([int(h["id"]) for h in reduced_sem], [int(h["id"]) for h in reduced_ts])
    pass2 = run_llm(
        query=query,
        semantic_hits=reduced_sem,
        ts_hits=reduced_ts,
        overlap=reduced_overlap,
        source_reference=source_reference,
        ollama_url=ollama_url,
        model=synth_model,
        temperature=temperature,
        timeout=timeout,
        route_plan=route_plan,
        extra_context=merged_extra,
        extra_context_label=extra_context_label,
        num_ctx=synth_num_ctx,
    )
    pass2["selected_evidence_count"] = len(selected_evidence)

    return {
        "mode": "two_pass",
        "compress_pass": {
            "model": compress_model,
            "elapsed_sec": pass1_elapsed,
            "summary": summary_text,
            "top_evidence": selected_evidence,
            "raw": raw_pass1,
            "parse_error": parse_error,
        },
        "synth_pass": pass2,
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="MKG semantic + TS retrieval harness with optional synthesis.")
    ap.add_argument("query", nargs="?", help="Natural-language query (or use --query-file)")
    ap.add_argument("--query-file", type=Path, help="UTF-8 file whose contents are the query")
    ap.add_argument(
        "--questions-file",
        type=Path,
        help="UTF-8 file with one query per line (# comments and blank lines ignored)",
    )
    ap.add_argument("--top-k", type=int, default=12, help="Hits per lane")
    ap.add_argument(
        "--sources",
        type=str,
        default="",
        help="Comma-separated rag_corpus.source filter (optional), e.g. icd10cm,loinc",
    )
    ap.add_argument("--embed-model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    ap.add_argument("--text-chars", type=int, default=1200, help="Max chars of text per hit in LLM payload")
    ap.add_argument("--no-llm", action="store_true", help="Skip Ollama; print retrieval JSON only")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "eoh-qwen3-14b"),
        help="Default Ollama model. Used for synthesis if --synth-model not provided.",
    )
    ap.add_argument(
        "--synth-model",
        default=os.environ.get("OLLAMA_SYNTH_MODEL") or os.environ.get("FORWARD_SYNTH_MODEL"),
        help="Override Ollama model for the final synthesis step (e.g. eoh-llama:70b).",
    )
    ap.add_argument(
        "--synth-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_NUM_CTX", "61440")),
        help="Context window for final synthesis pass.",
    )
    ap.add_argument(
        "--two-pass-synth",
        action="store_true",
        help="Run compression pass first (summary + top evidence), then final synthesis on compressed evidence.",
    )
    ap.add_argument(
        "--compress-model",
        default=os.environ.get("OLLAMA_COMPRESS_MODEL"),
        help="Model for pass-1 compression (defaults to --model when unset).",
    )
    ap.add_argument(
        "--compress-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_COMPRESS_NUM_CTX", "61440")),
        help="num_ctx for pass-1 compression model (default 61440).",
    )
    ap.add_argument(
        "--compress-evidence-k",
        type=int,
        default=8,
        help="How many evidence items pass-1 should select for pass-2 synthesis.",
    )
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--out", type=Path, help="Write full JSON result here")
    # Router-driven query expansion
    ap.add_argument(
        "--use-router",
        action="store_true",
        help="Run eoh-llama3.2-source-router first to produce expanded ts_terms + semantic_query (default ON).",
    )
    ap.add_argument(
        "--no-router",
        action="store_true",
        help="Disable source-router stage and run direct query retrieval.",
    )
    ap.add_argument(
        "--router-model",
        default=os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"),
        help="Ollama model name for the router stage.",
    )
    ap.add_argument(
        "--router-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192")),
    )
    ap.add_argument(
        "--router-max-sources",
        type=int,
        default=int(os.environ.get("ROUTER_MAX_SOURCES", "16")),
        help="Max distinct sources for plan_route (default 16).",
    )
    ap.add_argument("--router-max-modules", type=int, default=6)
    ap.add_argument(
        "--router-temperature",
        type=float,
        default=float(os.environ.get("ROUTER_TEMPERATURE", "0.27")),
        help="Source-router sampling temperature (default 0.27).",
    )
    ap.add_argument(
        "--router-restrict-sources",
        action="store_true",
        help="Restrict retrieval to router-selected sources (intersected with --sources if both set).",
    )
    ap.add_argument(
        "--router-min-terms",
        type=int,
        default=4,
        help="Minimum ts_terms accepted from router; below this we still run the per-term TS but also keep the raw-query fallback.",
    )
    ap.add_argument(
        "--no-source-coverage",
        action="store_true",
        help="Disable pinning one qualifying rag_corpus hit per filtered/routed source.",
    )
    ap.add_argument(
        "--min-ann-score",
        type=float,
        default=float(os.environ.get("MKG_MIN_ANN_SCORE", "0.12")),
        metavar="S",
        help="Minimum ANN score (1 - distance) for coverage eligibility (default 0.12).",
    )
    ap.add_argument(
        "--min-ts-score",
        type=float,
        default=float(os.environ.get("MKG_MIN_TS_SCORE", "0.02")),
        metavar="S",
        help="Minimum ts_rank for coverage eligibility (default 0.02).",
    )
    ap.set_defaults(use_router=True)
    args = ap.parse_args()
    if args.no_router:
        args.use_router = False
    return args


def run_query(
    q: str,
    *,
    psycopg=None,
    dict_row=None,
    top_k: int = 10,
    user_sources: Optional[List[str]] = None,
    embed_model: str = "BAAI/bge-base-en-v1.5",
    text_chars: int = 480,
    no_llm: bool = False,
    ollama_url: str = "http://127.0.0.1:11434",
    model: str = "eoh-llama-lucifer",
    synth_model: Optional[str] = None,
    synth_num_ctx: Optional[int] = None,
    two_pass_synth: bool = False,
    compress_model: Optional[str] = None,
    compress_num_ctx: Optional[int] = None,
    compress_evidence_k: int = 8,
    temperature: float = 0.15,
    timeout: float = 600.0,
    use_router: bool = False,
    router_model: str = "eoh-llama3.2-source-router",
    router_num_ctx: int = 8192,
    router_max_sources: int = 16,
    router_max_modules: int = 6,
    router_restrict_sources: bool = False,
    router_min_terms: int = 4,
    router_temperature: float = 0.27,
    source_coverage: bool = True,
    min_ann_score: float = 0.12,
    min_ts_score: float = 0.02,
    clinical_context: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    extra_context_label: str = "patient_timeline_summary",
) -> Dict[str, Any]:
    t0 = time.monotonic()
    """Library entry point for the MKG retrieval pipeline.

    This is what external callers (e.g. ``forward_ptv_3agent_harness``) should
    use. It mirrors ``_run_one_query`` but takes explicit kwargs and supports
    feeding an upstream ``clinical_context`` (e.g. the 70B PTV synthesis from
    the 3-agent harness) into both the router (better source/term selection)
    and the final 70B synthesis (so it can ground patient-specific claims in
    event_ids while grounding evidence claims in rag_corpus hit ids).
    """
    if psycopg is None or dict_row is None:
        import psycopg as _psycopg  # local import so module stays importable
        from psycopg.rows import dict_row as _dict_row

        psycopg = _psycopg
        dict_row = _dict_row

    if user_sources:
        user_sources = [s.strip().lower() for s in user_sources if str(s).strip()]
        _log("🧰", f"User source filter enabled ({len(user_sources)}): {', '.join(user_sources)}")
    else:
        user_sources = None
        _log("🧰", "No source filter; searching full pilot slice")

    out: Dict[str, Any] = {
        "query": q,
        "top_k": top_k,
        "sources_filter": user_sources,
        "embed_model": embed_model,
    }
    out["pilot_slice_source_reference"] = pilot_source_descriptions(sources=None)
    _log("📚", f"Loaded pilot source dictionary ({len(out['pilot_slice_source_reference'])} keys)")

    route_plan: Optional[Dict[str, Any]] = None
    embed_text = q
    ts_terms: List[str] = []
    effective_sources = user_sources
    if use_router:
        from server.mkg.router_planner import plan_route

        _log("🧭", f"Running source-router stage with {router_model}")
        route_plan = plan_route(
            q,
            ollama_url=ollama_url,
            model=router_model,
            num_ctx=router_num_ctx,
            timeout=timeout,
            temperature=router_temperature,
            max_sources=max(1, router_max_sources),
            max_modules=max(1, router_max_modules),
            clinical_context=clinical_context,
            router_min_terms=max(1, router_min_terms),
        )
        out["router_plan"] = route_plan
        if route_plan.get("semantic_query"):
            embed_text = route_plan["semantic_query"]
        ts_terms = list(route_plan.get("ts_terms") or [])
        _log(
            "🧭",
            f"Router done qtype={route_plan.get('question_type')} "
            f"ts_terms={len(ts_terms)} sources={len(route_plan.get('selected_sources') or [])}",
        )
        if router_restrict_sources:
            router_sources = [
                str(r.get("source")).strip().lower()
                for r in (route_plan.get("selected_sources") or [])
                if r.get("source")
            ]
            if router_sources:
                if user_sources:
                    intersection = [s for s in router_sources if s in set(user_sources)]
                    effective_sources = intersection or user_sources
                else:
                    effective_sources = router_sources
                _log("🧰", f"Router-restricted sources active ({len(effective_sources)})")
    out["effective_sources"] = effective_sources

    if embed_text != q:
        _log("✍️", "Embedding router-rewritten semantic query")
    t_embed = time.monotonic()
    vec, device = embed_query(embed_model, embed_text)
    out["embed_device"] = device
    out["embed_text"] = embed_text
    out["embed_sec"] = round(time.monotonic() - t_embed, 4)
    _log("✅", f"Query embedding complete in {out['embed_sec']:.4f}s")
    lit = _vec_literal(vec)

    t_db = time.monotonic()
    dsn = _dsn()
    _log("🗄️", f"Running semantic + TS retrieval (top_k={top_k})")
    ts_strategy = "raw_query"
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '120s';")
            sem_rows = ann_local(cur, lit, top_k, sources=effective_sources)
            ts_rows: List[Dict[str, Any]] = []
            if ts_terms:
                ts_rows = bm25_ts_terms(cur, ts_terms, top_k, sources=effective_sources)
                ts_strategy = f"per_term ({len(ts_terms)} terms)"
                if not ts_rows or len(ts_terms) < router_min_terms:
                    _log("🔁", "Per-term TS empty/thin; merging raw-query fallback")
                    raw_rows = bm25_ts(cur, q, top_k, sources=effective_sources)
                    by_id: Dict[Any, Dict[str, Any]] = {r["id"]: r for r in ts_rows}
                    for r in raw_rows:
                        rid = r["id"]
                        if rid not in by_id or float(r.get("score") or 0) > float(
                            by_id[rid].get("score") or 0
                        ):
                            by_id[rid] = r
                    ts_rows = sorted(
                        by_id.values(),
                        key=lambda r: float(r.get("score") or 0.0),
                        reverse=True,
                    )[:top_k]
                    ts_strategy = f"per_term+raw_fallback ({len(ts_terms)} terms)"
            else:
                ts_rows = bm25_ts(cur, q, top_k, sources=effective_sources)

            ts_fallback_q = ((route_plan.get("semantic_query") if route_plan else None) or q).strip()
            cov_stats: Dict[str, Any] = {}
            if (
                source_coverage
                and effective_sources
                and isinstance(effective_sources, list)
            ):
                sem_rows, ts_rows, cov_stats = ensure_source_coverage_retrieval(
                    cur,
                    lit,
                    sem_rows,
                    ts_rows,
                    required_sources=effective_sources,
                    ts_terms=ts_terms,
                    ts_query_fallback=ts_fallback_q,
                    top_k=top_k,
                    min_ann_score=min_ann_score,
                    min_ts_score=min_ts_score,
                    per_source_fetch_limit=max(16, top_k),
                )
                out["source_coverage"] = cov_stats
                if cov_stats.get("missing_sources"):
                    _log(
                        "📎",
                        "Source coverage: no qualifying hit for "
                        f"{cov_stats['missing_sources']} (ANN≥{min_ann_score}, TS≥{min_ts_score}).",
                    )
                elif cov_stats.get("extra_ann_fetches") or cov_stats.get("extra_ts_fetches"):
                    _log(
                        "📎",
                        f"Source coverage: pinned extra ANN={cov_stats.get('extra_ann_fetches')} "
                        f"TS={cov_stats.get('extra_ts_fetches')} "
                        f"(lane_cap={cov_stats.get('lane_cap')}).",
                    )
            elif source_coverage:
                out["source_coverage"] = {
                    "enabled": False,
                    "skipped_reason": "no_effective_source_list",
                }
            else:
                out["source_coverage"] = {"enabled": False, "skipped_reason": "disabled"}
    out["db_sec"] = round(time.monotonic() - t_db, 4)
    out["ts_strategy"] = ts_strategy
    out["ts_terms_used"] = ts_terms
    _log(
        "📊",
        f"DB done in {out['db_sec']:.4f}s (semantic={len(sem_rows)} ts={len(ts_rows)} via {ts_strategy})",
    )

    sem_compact = [_compact_hit(r, text_chars=text_chars) for r in sem_rows]
    ts_compact = [_compact_hit(r, text_chars=text_chars) for r in ts_rows]
    overlap = _overlap([h["id"] for h in sem_compact], [h["id"] for h in ts_compact])
    out["semantic_hits"] = sem_compact
    out["ts_hits"] = ts_compact
    out["overlap"] = overlap
    _log("🔀", f"Overlap computed (both={len(overlap['both'])} jaccard={overlap['jaccard']:.3f})")

    # Stitch clinical_context into extra_context if caller passed only the raw string.
    eff_extra = dict(extra_context) if extra_context else None
    if clinical_context and not eff_extra:
        eff_extra = {"summary_markdown": clinical_context}

    if not no_llm:
        ref = pilot_source_descriptions(sources=None)
        synth = synth_model or model
        compress = compress_model or model
        _log("🧪", f"Running Ollama synthesis pass model={synth}")
        try:
            if two_pass_synth:
                out["llm"] = run_llm_two_pass(
                    query=q,
                    semantic_hits=sem_compact,
                    ts_hits=ts_compact,
                    overlap=overlap,
                    source_reference=ref,
                    ollama_url=ollama_url,
                    compress_model=compress,
                    synth_model=synth,
                    temperature=temperature,
                    timeout=timeout,
                    route_plan=route_plan,
                    extra_context=eff_extra,
                    extra_context_label=extra_context_label,
                    compress_num_ctx=compress_num_ctx,
                    synth_num_ctx=synth_num_ctx,
                    compress_evidence_k=max(1, int(compress_evidence_k)),
                )
                synth_elapsed = ((out["llm"].get("synth_pass") or {}).get("elapsed_sec") or 0)
                _log("📝", f"Two-pass synth done (pass2={synth_elapsed}s)")
            else:
                out["llm"] = run_llm(
                    query=q,
                    semantic_hits=sem_compact,
                    ts_hits=ts_compact,
                    overlap=overlap,
                    source_reference=ref,
                    ollama_url=ollama_url,
                    model=synth,
                    temperature=temperature,
                    timeout=timeout,
                    route_plan=route_plan,
                    extra_context=eff_extra,
                    extra_context_label=extra_context_label,
                    num_ctx=synth_num_ctx,
                )
                _log("📝", f"LLM synthesis done in {out['llm'].get('elapsed_sec', 0)}s")
        except Exception as exc:  # noqa: BLE001
            out["llm"] = {"error": str(exc), "model": synth}
            _log("⚠️", f"LLM synthesis failed: {exc}")
    else:
        _log("⏭️", "Skipping LLM synthesis (no_llm=True)")

    out["elapsed_sec"] = round(time.monotonic() - t0, 3)
    _log("⏱️", f"run_query done elapsed_sec={out['elapsed_sec']:.3f}")
    return out


def _run_one_query(
    *,
    q: str,
    args: argparse.Namespace,
    psycopg,
    dict_row,
) -> Dict[str, Any]:
    """Thin CLI adapter that maps argparse args onto :func:`run_query`."""
    user_sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()] or None
    return run_query(
        q,
        psycopg=psycopg,
        dict_row=dict_row,
        top_k=args.top_k,
        user_sources=user_sources,
        embed_model=args.embed_model,
        text_chars=args.text_chars,
        no_llm=args.no_llm,
        ollama_url=args.ollama_url,
        model=args.model,
        synth_model=args.synth_model,
        synth_num_ctx=args.synth_num_ctx,
        two_pass_synth=args.two_pass_synth,
        compress_model=args.compress_model,
        compress_num_ctx=args.compress_num_ctx,
        compress_evidence_k=args.compress_evidence_k,
        temperature=args.temperature,
        timeout=args.timeout,
        use_router=args.use_router,
        router_model=args.router_model,
        router_num_ctx=args.router_num_ctx,
        router_max_sources=args.router_max_sources,
        router_max_modules=args.router_max_modules,
        router_restrict_sources=args.router_restrict_sources,
        router_min_terms=args.router_min_terms,
        router_temperature=args.router_temperature,
        source_coverage=not args.no_source_coverage,
        min_ann_score=args.min_ann_score,
        min_ts_score=args.min_ts_score,
    )


def _load_queries(args: argparse.Namespace) -> List[str]:
    if args.questions_file:
        _log("📚", f"Reading questions file: {args.questions_file}")
        qs: List[str] = []
        for raw in args.questions_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            qs.append(line)
        return qs
    if args.query_file:
        _log("📄", f"Reading query from file: {args.query_file}")
        q = args.query_file.read_text(encoding="utf-8").strip()
        return [q] if q else []
    q = (args.query or "").strip()
    return [q] if q else []


def main() -> None:
    args = _parse_args()
    _log("🚀", "Starting MKG retrieval harness")
    import psycopg
    from psycopg.rows import dict_row

    queries = _load_queries(args)
    if not queries:
        print("error: provide query, --query-file, or --questions-file", file=sys.stderr)
        sys.exit(2)
    _log("❓", f"Loaded {len(queries)} question(s)")

    if len(queries) == 1:
        _log("🧪", "Single-query mode")
        t_single = time.monotonic()
        out = _run_one_query(q=queries[0], args=args, psycopg=psycopg, dict_row=dict_row)
        text = json.dumps(out, indent=2, default=str)
        _log("📦", f"Emitting JSON output ({len(text)} chars)")
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
            _log("💾", f"Wrote output file: {args.out}")
        _log("⏱️", f"single-query total elapsed_sec={time.monotonic() - t_single:.3f}")
        _log("🏁", "Harness run complete")
        return

    _log("📚", "Batch mode enabled")
    started = time.monotonic()
    runs: List[Dict[str, Any]] = []
    for i, q in enumerate(queries, start=1):
        _log("➡️", f"Batch question {i}/{len(queries)}: {q[:90]}")
        t_item = time.monotonic()
        run = _run_one_query(q=q, args=args, psycopg=psycopg, dict_row=dict_row)
        run["batch_index"] = i
        run["batch_elapsed_sec"] = round(time.monotonic() - t_item, 3)
        _log("⏱️", f"batch item {i}/{len(queries)} elapsed_sec={run['batch_elapsed_sec']:.3f}")
        runs.append(run)

    batch_out: Dict[str, Any] = {
        "batch": {
            "n_questions": len(queries),
            "elapsed_sec": round(time.monotonic() - started, 3),
            "model": args.model,
            "synth_model": args.synth_model or args.model,
            "two_pass_synth": bool(args.two_pass_synth),
            "compress_model": (args.compress_model or args.model) if args.two_pass_synth else None,
            "compress_num_ctx": args.compress_num_ctx if args.two_pass_synth else None,
            "compress_evidence_k": args.compress_evidence_k if args.two_pass_synth else None,
            "router_model": args.router_model if args.use_router else None,
            "use_router": bool(args.use_router),
            "router_restrict_sources": bool(args.router_restrict_sources),
            "embed_model": args.embed_model,
        },
        "runs": runs,
    }
    text = json.dumps(batch_out, indent=2, default=str)
    _log("📦", f"Emitting batch JSON output ({len(text)} chars)")
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        _log("💾", f"Wrote output file: {args.out}")
    _log("🏁", "Harness run complete")


if __name__ == "__main__":
    main()
