"""
embeddings.py — cached sentence-transformer embeddings for graph events.

One NPZ cache per ``(graph_hash, model_name)`` under
``artifacts/ptv_toolkit_embeddings/``.  First access encodes every event's
text; subsequent accesses are a memory-mapped load (<50 ms).

The embedded text per event prefers ``card.one_line`` (then title, then
``preview``), prefixed with ``event_type`` and ``timestamp`` — aligned
with what tools return in compact cards.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .graph import GraphHandle

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"
CACHE_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "ptv_toolkit_embeddings"

# Bump when the text composition in ``_event_text`` changes so old caches
# invalidate automatically (embeddings computed on the old text would be
# silently wrong).
TEXT_REV = "v2-oneline"

_MODEL_CACHE: Dict[str, object] = {}


def _get_model(model_name: str):
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    from sentence_transformers import SentenceTransformer
    logger.info("[ptv_toolkit] loading sentence-transformers model %s", model_name)
    m = SentenceTransformer(model_name)
    _MODEL_CACHE[model_name] = m
    return m


def _event_text(ev: Dict) -> str:
    """Compact, denoised text for one event (~= what the agent will see).

    Priority for the narrative slot:
      1. card.one_line    — scrubbed, 1-line clinical summary when available
      2. card.title       — normalized human label
      3. preview[:360]    — raw text fallback

    The agent sees ``one_line`` in every tool-result card, so embedding the
    same string avoids the ranking/display mismatch where ST ranked a
    different string than the agent ever read.
    """
    ann = ev.get("annotations") or {}
    card = ann.get("card") or {}
    one_line = str(card.get("one_line") or "").strip()
    title = str(card.get("title") or "").strip()
    narrative = one_line or title or str(ev.get("preview") or "")[:360]
    parts: List[str] = [
        str(ev.get("event_type") or ""),
        str(ev.get("timestamp") or "unknown"),
        title if (one_line and title and title != one_line) else "",
        narrative,
    ]
    return " | ".join(p for p in parts if p).strip()


@dataclass
class EmbeddingStore:
    graph_hash: str
    model_name: str
    event_ids: List[str]
    matrix: np.ndarray          # (n_events, dim), float32, L2-normalized
    dim: int

    def encode_query(self, query: str) -> np.ndarray:
        model = _get_model(self.model_name)
        vec = model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        return vec.astype(np.float32)[0]

    def search(
        self,
        query: str,
        k: int,
        *,
        allowed_event_ids: Optional[set] = None,
    ) -> List[Tuple[str, float]]:
        if self.matrix.size == 0:
            return []
        q = self.encode_query(query)
        scores = self.matrix @ q  # cosine (matrix is L2-normalized)
        if allowed_event_ids is not None:
            mask = np.array(
                [eid in allowed_event_ids for eid in self.event_ids],
                dtype=bool,
            )
            if not mask.any():
                return []
            scores = np.where(mask, scores, -1.0)
        k = max(1, min(k, len(scores)))
        idx = np.argpartition(-scores, kth=k - 1)[:k]
        ranked = sorted(((int(i), float(scores[i])) for i in idx), key=lambda kv: -kv[1])
        return [(self.event_ids[i], s) for i, s in ranked if s > -0.5]


def get_or_build_store(
    gh: GraphHandle,
    model_name: str = DEFAULT_MODEL,
    *,
    force_rebuild: bool = False,
) -> EmbeddingStore:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    tag = model_name.replace("/", "_")
    cache_file = CACHE_ROOT / f"{gh.graph_hash}__{tag}__{TEXT_REV}.npz"

    if cache_file.exists() and not force_rebuild:
        try:
            with np.load(cache_file, allow_pickle=False) as data:
                event_ids = list(data["event_ids"])
                matrix = data["matrix"].astype(np.float32)
            return EmbeddingStore(
                graph_hash=gh.graph_hash,
                model_name=model_name,
                event_ids=event_ids,
                matrix=matrix,
                dim=int(matrix.shape[1]) if matrix.ndim == 2 else 0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ptv_toolkit] failed to load cache %s: %s", cache_file, exc)

    event_ids = list(gh.events.keys())
    texts = [_event_text(gh.events[eid]) for eid in event_ids]
    if not texts:
        return EmbeddingStore(gh.graph_hash, model_name, [], np.zeros((0, 0), dtype=np.float32), 0)

    model = _get_model(model_name)
    batch = int(os.environ.get("PTV_TOOLKIT_EMBED_BATCH", "64"))
    show_bar = os.environ.get("PTV_TOOLKIT_EMBED_PROGRESS", "1").strip() not in ("0", "false", "no")
    # First full-graph encode is CPU/GPU-heavy and can look "stuck" in logs
    # when the progress bar is disabled — keep it on by default.
    print(
        f"[ptv_toolkit] embedding {len(texts)} events (batch={batch}, "
        f"model={model_name}) — first run only; saving to {cache_file.name} …",
        flush=True,
    )
    matrix = model.encode(
        texts,
        batch_size=batch,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=show_bar,
    ).astype(np.float32)

    np.savez_compressed(cache_file, event_ids=np.array(event_ids), matrix=matrix)
    logger.info("[ptv_toolkit] embedded %d events -> %s", len(event_ids), cache_file.name)

    return EmbeddingStore(
        graph_hash=gh.graph_hash,
        model_name=model_name,
        event_ids=event_ids,
        matrix=matrix,
        dim=int(matrix.shape[1]) if matrix.ndim == 2 else 0,
    )
