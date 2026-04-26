#!/usr/bin/env python3
"""
MKG retrieval test harness: one user query → semantic (embedding_local) + TS (websearch_to_tsquery)
against ``public.rag_corpus``, then optional synthesis with Ollama (default ``eoh-llama-lucifer``).

The harness supports an optional **router-driven query expansion** stage that calls the
``eoh-llama3.2-source-router`` model first to produce an expanded ``semantic_query`` for ANN
and a list of concrete ``ts_terms`` for per-term Postgres FTS retrieval. This mirrors the
``/ask_stream`` production pattern (``extract_qna_terms`` -> ``search_source_ts_for_terms``),
which dramatically improves TS recall on dense vocabularies (RxNorm, SNOMED, LOINC).

A separate ``--synth-model`` flag (or ``OLLAMA_SYNTH_MODEL`` env) lets the final synthesis
step use a heavier model, e.g. ``eoh-llama:70b``, without rerunning retrieval.

Env (same as portal embed scripts):
  SYNC_DATABASE_URL or DATABASE_URL
  LOCAL_EMBED_MODEL — default BAAI/bge-base-en-v1.5
  OLLAMA_URL — default http://127.0.0.1:11434
  OLLAMA_MODEL — default eoh-llama-lucifer (planning/default synth)
  OLLAMA_SYNTH_MODEL — optional override for the synthesis step (e.g. eoh-llama:70b)
  OLLAMA_NUM_CTX — synthesis context size (default 16384; bump to 32768 for 8B and 8192 for 70B)
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
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.mkg.portalnode_pilot_sources import pilot_source_descriptions


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


def _ollama_chat(url: str, model: str, messages: List[Dict[str, str]], *, timeout: float, temperature: float) -> str:
    import requests

    num_ctx = max(2048, int(os.environ.get("OLLAMA_NUM_CTX", "16384")))
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


def embed_query(model_name: str, text: str) -> Tuple[List[float], str]:
    from sentence_transformers import SentenceTransformer
    import torch

    device = os.environ.get("LOCAL_EMBED_DEVICE")
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    _log("🧠", f"Loading embedding model={model_name} on device={device}")
    st = SentenceTransformer(model_name, device=device)
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
    system = (
        "You are a clinical knowledge synthesis expert evaluating dual-lane retrieval from a medical "
        "knowledge graph (rag_corpus). You receive JSON with two ranked lists: dense semantic "
        "(BGE/local cosine) and PostgreSQL FTS (websearch_to_tsquery), plus rag_source_reference.\n\n"
        "SYNTHESIS RULES (follow strictly):\n"
        "1. SYNTHESIZE — do NOT copy or paraphrase hit text verbatim. Extract clinical meaning and "
        "   integrate it into your own reasoning. A good summary states what the evidence implies, "
        "   not just what it says.\n"
        "2. Compare the two lanes: note where they agree, where they diverge, and what the divergence "
        "   means for clinical confidence.\n"
        "3. For treatment/management/planning queries, explicitly state first-line and alternative "
        "   options, evidence grade, and any contraindications present in the hits.\n"
        "4. If a lane returned no results, explain why (e.g., lexical mismatch) and what that gap "
        "   implies for retrieval quality — do not silently skip it.\n"
        "5. Only reference ids present in the JSON.\n\n"
        "Output markdown with exactly these headings:\n"
        "## Summary\n## Overlap\n## Best semantic hit\n## Best TS hit\n## Query refinement\n"
        "Keep total response under 600 words."
    )
    user = (
        "Synthesize the clinical evidence in this dual-lane retrieval bundle. "
        "Do not copy text — reason from it.\n\n"
        + json.dumps(bundle, indent=2, default=str)
    )
    t0 = time.monotonic()
    text = _ollama_chat(
        ollama_url,
        model,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        timeout=timeout,
        temperature=temperature,
    )
    return {"model": model, "elapsed_sec": round(time.monotonic() - t0, 3), "markdown": text}


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="MKG semantic + TS retrieval harness with optional eoh-llama-lucifer.")
    ap.add_argument("query", nargs="?", help="Natural-language query (or use --query-file)")
    ap.add_argument("--query-file", type=Path, help="UTF-8 file whose contents are the query")
    ap.add_argument(
        "--questions-file",
        type=Path,
        help="UTF-8 file with one query per line (# comments and blank lines ignored)",
    )
    ap.add_argument("--top-k", type=int, default=10, help="Hits per lane")
    ap.add_argument(
        "--sources",
        type=str,
        default="",
        help="Comma-separated rag_corpus.source filter (optional), e.g. icd10cm,loinc",
    )
    ap.add_argument("--embed-model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    ap.add_argument("--text-chars", type=int, default=480, help="Max chars of text per hit in LLM payload")
    ap.add_argument("--no-llm", action="store_true", help="Skip Ollama; print retrieval JSON only")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "eoh-llama-lucifer"),
        help="Default Ollama model. Used for synthesis if --synth-model not provided.",
    )
    ap.add_argument(
        "--synth-model",
        default=os.environ.get("OLLAMA_SYNTH_MODEL"),
        help="Override Ollama model for the final synthesis step (e.g. eoh-llama:70b).",
    )
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--out", type=Path, help="Write full JSON result here")
    # Router-driven query expansion
    ap.add_argument(
        "--use-router",
        action="store_true",
        help="Run eoh-llama3.2-source-router first to produce expanded ts_terms + semantic_query.",
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
    ap.add_argument("--router-max-sources", type=int, default=8)
    ap.add_argument("--router-max-modules", type=int, default=6)
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
    return ap.parse_args()


def _run_one_query(
    *,
    q: str,
    args: argparse.Namespace,
    psycopg,
    dict_row,
) -> Dict[str, Any]:
    user_sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()] or None
    if user_sources:
        _log("🧰", f"User source filter enabled ({len(user_sources)}): {', '.join(user_sources)}")
    else:
        _log("🧰", "No --sources filter; searching full pilot slice")

    out: Dict[str, Any] = {
        "query": q,
        "top_k": args.top_k,
        "sources_filter": user_sources,
        "embed_model": args.embed_model,
    }
    # Full PortalNode pilot allowlist (scripts/portalnode_rag_slice_sources.txt) → LLM-facing blurbs
    out["pilot_slice_source_reference"] = pilot_source_descriptions(sources=None)
    _log("📚", f"Loaded pilot source dictionary ({len(out['pilot_slice_source_reference'])} keys)")

    # 1) Optional router pass (TS expansion + semantic rewrite + source plan)
    route_plan: Optional[Dict[str, Any]] = None
    embed_text = q
    ts_terms: List[str] = []
    effective_sources = user_sources
    if args.use_router:
        from server.mkg.router_planner import plan_route

        _log("🧭", f"Running source-router stage with {args.router_model}")
        route_plan = plan_route(
            q,
            ollama_url=args.ollama_url,
            model=args.router_model,
            num_ctx=args.router_num_ctx,
            timeout=args.timeout,
            max_sources=max(1, args.router_max_sources),
            max_modules=max(1, args.router_max_modules),
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

        if args.router_restrict_sources:
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

    # 2) Embedding (use router-rewritten query if available)
    if embed_text != q:
        _log("✍️", "Embedding router-rewritten semantic query")
    t_embed = time.monotonic()
    vec, device = embed_query(args.embed_model, embed_text)
    out["embed_device"] = device
    out["embed_text"] = embed_text
    out["embed_sec"] = round(time.monotonic() - t_embed, 4)
    _log("✅", f"Query embedding complete in {out['embed_sec']:.4f}s")
    lit = _vec_literal(vec)

    # 3) Retrieval (semantic ANN + TS lane). TS lane uses per-term retrieval when terms exist.
    t_db = time.monotonic()
    dsn = _dsn()
    _log("🗄️", f"Running semantic + TS retrieval (top_k={args.top_k})")
    ts_strategy = "raw_query"
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '120s';")
            sem_rows = ann_local(cur, lit, args.top_k, sources=effective_sources)

            ts_rows: List[Dict[str, Any]] = []
            if ts_terms:
                ts_rows = bm25_ts_terms(cur, ts_terms, args.top_k, sources=effective_sources)
                ts_strategy = f"per_term ({len(ts_terms)} terms)"
                if not ts_rows or len(ts_terms) < args.router_min_terms:
                    _log("🔁", "Per-term TS empty/thin; merging raw-query fallback")
                    raw_rows = bm25_ts(cur, q, args.top_k, sources=effective_sources)
                    by_id: Dict[Any, Dict[str, Any]] = {r["id"]: r for r in ts_rows}
                    for r in raw_rows:
                        rid = r["id"]
                        if rid not in by_id or float(r.get("score") or 0) > float(by_id[rid].get("score") or 0):
                            by_id[rid] = r
                    ts_rows = sorted(
                        by_id.values(),
                        key=lambda r: float(r.get("score") or 0.0),
                        reverse=True,
                    )[: args.top_k]
                    ts_strategy = f"per_term+raw_fallback ({len(ts_terms)} terms)"
            else:
                ts_rows = bm25_ts(cur, q, args.top_k, sources=effective_sources)
    out["db_sec"] = round(time.monotonic() - t_db, 4)
    out["ts_strategy"] = ts_strategy
    out["ts_terms_used"] = ts_terms
    _log(
        "📊",
        f"DB done in {out['db_sec']:.4f}s (semantic={len(sem_rows)} ts={len(ts_rows)} via {ts_strategy})",
    )

    sem_compact = [_compact_hit(r, text_chars=args.text_chars) for r in sem_rows]
    ts_compact = [_compact_hit(r, text_chars=args.text_chars) for r in ts_rows]
    overlap = _overlap([h["id"] for h in sem_compact], [h["id"] for h in ts_compact])
    out["semantic_hits"] = sem_compact
    out["ts_hits"] = ts_compact
    out["overlap"] = overlap
    _log("🔀", f"Overlap computed (both={len(overlap['both'])} jaccard={overlap['jaccard']:.3f})")

    if not args.no_llm:
        ref = pilot_source_descriptions(sources=None)
        synth_model = args.synth_model or args.model
        _log("🧪", f"Running Ollama synthesis pass model={synth_model}")
        try:
            out["llm"] = run_llm(
                query=q,
                semantic_hits=sem_compact,
                ts_hits=ts_compact,
                overlap=overlap,
                source_reference=ref,
                ollama_url=args.ollama_url,
                model=synth_model,
                temperature=args.temperature,
                timeout=args.timeout,
                route_plan=route_plan,
            )
            _log("📝", f"LLM synthesis done in {out['llm'].get('elapsed_sec', 0)}s")
        except Exception as exc:  # noqa: BLE001
            out["llm"] = {"error": str(exc), "model": synth_model}
            _log("⚠️", f"LLM synthesis failed: {exc}")
    else:
        _log("⏭️", "Skipping LLM synthesis (--no-llm)")

    return out


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
        out = _run_one_query(q=queries[0], args=args, psycopg=psycopg, dict_row=dict_row)
        text = json.dumps(out, indent=2, default=str)
        _log("📦", f"Emitting JSON output ({len(text)} chars)")
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
            _log("💾", f"Wrote output file: {args.out}")
        _log("🏁", "Harness run complete")
        return

    _log("📚", "Batch mode enabled")
    started = time.monotonic()
    runs: List[Dict[str, Any]] = []
    for i, q in enumerate(queries, start=1):
        _log("➡️", f"Batch question {i}/{len(queries)}: {q[:90]}")
        run = _run_one_query(q=q, args=args, psycopg=psycopg, dict_row=dict_row)
        run["batch_index"] = i
        runs.append(run)

    batch_out: Dict[str, Any] = {
        "batch": {
            "n_questions": len(queries),
            "elapsed_sec": round(time.monotonic() - started, 3),
            "model": args.model,
            "synth_model": args.synth_model or args.model,
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
