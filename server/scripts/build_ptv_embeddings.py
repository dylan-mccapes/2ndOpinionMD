"""Eagerly build (or refresh) the per-graph PTV semantic embedding cache.

The toolkit normally builds the SentenceTransformers cache lazily on the first
``semantic_search`` call. That makes the first chatbot/harness turn pay a 30-70 s
cold load, which is annoying during interactive sessions.

This script walks one or more PTV JSON files, loads each graph, and forces a
build via ``server.ptv_toolkit.embeddings.get_or_build_store`` so the cache file
``artifacts/ptv_toolkit_embeddings/<graph_hash>__<model>__<TEXT_REV>.npz``
exists before the chatbot is launched.

Examples (PowerShell)::

    # Embed every PTV JSON under the synthetic cohort folder
    python -m server.scripts.build_ptv_embeddings --dir artifacts/forward_kaleb_package_20260423/synthetic_pro_cohort

    # Embed a single graph (default model: all-MiniLM-L6-v2 / 384-dim)
    python -m server.scripts.build_ptv_embeddings --graph artifacts/forward_kaleb_package_20260423/synthetic_pro_cohort/ptv_synth_P1_early_responder.json

    # Force a rebuild
    python -m server.scripts.build_ptv_embeddings --dir artifacts/forward_exemplar_5pt --force
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit.embeddings import (  # noqa: E402
    CACHE_ROOT,
    DEFAULT_MODEL,
    TEXT_REV,
    get_or_build_store,
)
from server.ptv_toolkit.graph import load_graph  # noqa: E402


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def _collect_graphs(args: argparse.Namespace) -> List[Path]:
    out: List[Path] = []
    for g in args.graph or []:
        p = Path(g).expanduser().resolve()
        if not p.is_file():
            _log("⚠️", f"skip (missing): {p}")
            continue
        out.append(p)
    for d in args.dir or []:
        dp = Path(d).expanduser().resolve()
        if not dp.is_dir():
            _log("⚠️", f"skip (missing dir): {dp}")
            continue
        out.extend(sorted(dp.glob("ptv_*.json")))
        out.extend(sorted(dp.glob("PTV_*.json")))
    seen: set = set()
    deduped: List[Path] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        deduped.append(p)
    return deduped


def _embed_one(path: Path, *, model: str, force: bool) -> dict:
    t0 = time.monotonic()
    gh = load_graph(path)
    cache_tag = model.replace("/", "_")
    cache_file = CACHE_ROOT / f"{gh.graph_hash}__{cache_tag}__{TEXT_REV}.npz"
    pre_existed = cache_file.exists()
    store = get_or_build_store(gh, model_name=model, force_rebuild=force)
    elapsed = round(time.monotonic() - t0, 3)
    return {
        "path": str(path),
        "graph_hash": gh.graph_hash,
        "n_events": len(gh.events),
        "n_embedded": len(store.event_ids),
        "dim": store.dim,
        "model": model,
        "cache_file": str(cache_file),
        "pre_existed": pre_existed,
        "force_rebuild": bool(force),
        "elapsed_sec": elapsed,
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--graph",
        action="append",
        default=[],
        metavar="PATH",
        help="Path to a single PTV JSON. Can be repeated.",
    )
    ap.add_argument(
        "--dir",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory containing PTV JSONs (matches ptv_*.json / PTV_*.json). Can be repeated.",
    )
    ap.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"SentenceTransformer model. Default: {DEFAULT_MODEL} (384-dim).",
    )
    ap.add_argument("--force", action="store_true", help="Force rebuild even if cache exists.")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    graphs = _collect_graphs(args)
    if not graphs:
        _log("❌", "no graphs supplied; pass --graph PATH or --dir DIR")
        return 2

    _log("📦", f"cache root: {CACHE_ROOT}")
    _log("🧠", f"model: {args.model} (text_rev={TEXT_REV}) force={args.force}")

    total = 0
    for p in graphs:
        try:
            rep = _embed_one(p, model=args.model, force=args.force)
        except Exception as exc:  # noqa: BLE001
            _log("⚠️", f"{p.name}: {exc}")
            continue
        flag = "REBUILT" if (rep["force_rebuild"] or not rep["pre_existed"]) else "ALREADY-CACHED"
        _log(
            "✅",
            f"{p.name} hash={rep['graph_hash']} n={rep['n_embedded']}/{rep['n_events']} "
            f"dim={rep['dim']} {flag} in {rep['elapsed_sec']}s",
        )
        total += 1

    _log("🏁", f"done — {total}/{len(graphs)} graphs embedded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
