"""Per-chatbot session log: append-only JSONL + best-effort search.

Each turn is one JSON object on its own line so that ``rg`` / ``grep`` and
naive substring search all work. A small ``__meta.json`` sidecar holds the
session header (graph_hash, models, started_at).

Search strategy:
1. If ``rg`` (ripgrep) is on PATH, use it for token search and read full
   matched lines back as JSON.
2. Otherwise, score every line with a token-overlap heuristic (case-insensitive
   token IoU + small bigram boost) and return the top-k.

The module is dependency-free beyond stdlib so it cannot break the chatbot
when `rg` is absent.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_TOKEN_RX = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_DEFAULT_DIR = Path(os.environ.get("CHATBOT_SESSION_DIR", "artifacts/chatbot_sessions"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RX.findall(text or "")]


def _bigrams(toks: List[str]) -> List[str]:
    return [f"{a}_{b}" for a, b in zip(toks, toks[1:])]


@dataclass
class SessionLog:
    """Append-only chatbot session storage with searchable JSONL body."""

    session_id: str
    graph_hash: str
    graph_path: str
    models: Dict[str, str]
    base_dir: Path = field(default_factory=lambda: _DEFAULT_DIR)

    @property
    def jsonl_path(self) -> Path:
        return self.base_dir / f"{self.session_id}.jsonl"

    @property
    def meta_path(self) -> Path:
        return self.base_dir / f"{self.session_id}__meta.json"

    @classmethod
    def create(
        cls,
        *,
        graph_hash: str,
        graph_path: str,
        models: Dict[str, str],
        session_id: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ) -> "SessionLog":
        sid = (session_id or _stamp()).strip().replace("/", "_").replace("\\", "_")
        bd = (base_dir or _DEFAULT_DIR).expanduser().resolve()
        bd.mkdir(parents=True, exist_ok=True)
        sl = cls(
            session_id=sid,
            graph_hash=graph_hash,
            graph_path=graph_path,
            models=dict(models or {}),
            base_dir=bd,
        )
        if not sl.meta_path.exists():
            sl.meta_path.write_text(
                json.dumps(
                    {
                        "session_id": sid,
                        "started_at": _now_iso(),
                        "graph_hash": graph_hash,
                        "graph_path": graph_path,
                        "models": dict(models or {}),
                        "schema": "chatbot_session.v1",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return sl

    @classmethod
    def open_existing(cls, session_id: str, *, base_dir: Optional[Path] = None) -> Optional["SessionLog"]:
        bd = (base_dir or _DEFAULT_DIR).expanduser().resolve()
        meta = bd / f"{session_id}__meta.json"
        if not meta.is_file():
            return None
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            return None
        return cls(
            session_id=str(data.get("session_id") or session_id),
            graph_hash=str(data.get("graph_hash") or ""),
            graph_path=str(data.get("graph_path") or ""),
            models=dict(data.get("models") or {}),
            base_dir=bd,
        )

    # -- writes -----------------------------------------------------------------

    def n_turns(self) -> int:
        if not self.jsonl_path.is_file():
            return 0
        n = 0
        with self.jsonl_path.open("r", encoding="utf-8") as fh:
            for _ in fh:
                n += 1
        return n

    def append_turn(self, turn: Dict[str, Any]) -> Dict[str, Any]:
        """Append a turn, return the stored object (with assigned ``turn_id``)."""
        idx = self.n_turns() + 1
        turn_id = f"{self.session_id}#t{idx:04d}"
        record: Dict[str, Any] = {
            "turn_id": turn_id,
            "turn_index": idx,
            "session_id": self.session_id,
            "graph_hash": self.graph_hash,
            "ts": _now_iso(),
        }
        record.update(turn or {})
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return record

    # -- reads ------------------------------------------------------------------

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.jsonl_path.is_file():
            return []
        out: List[Dict[str, Any]] = []
        with self.jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def get_turn(self, turn_id: str) -> Optional[Dict[str, Any]]:
        for t in self.read_all():
            if t.get("turn_id") == turn_id or str(t.get("turn_index")) == str(turn_id):
                return t
        return None

    # -- search -----------------------------------------------------------------

    def _has_ripgrep(self) -> bool:
        return shutil.which("rg") is not None

    def _ripgrep_lines(self, query: str, *, max_lines: int = 50) -> List[str]:
        rg = shutil.which("rg")
        if not rg or not self.jsonl_path.is_file():
            return []
        toks = _tokens(query)[:8] or [query.strip()]
        if not toks:
            return []
        # ripgrep -e tok1 -e tok2 ... acts as OR; -i case-insensitive
        cmd = [rg, "-i", "-N", "--no-heading", "-m", str(max_lines)]
        for t in toks:
            cmd += ["-e", re.escape(t)]
        cmd.append(str(self.jsonl_path))
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception as exc:  # noqa: BLE001
            print(f"[session_log] ripgrep failed: {exc}", file=sys.stderr)
            return []
        if r.returncode not in (0, 1):
            return []
        return [ln for ln in r.stdout.splitlines() if ln.strip()]

    def _score_line(self, query_toks: List[str], query_bigs: List[str], turn: Dict[str, Any]) -> float:
        text_blob = " ".join(
            str(turn.get(k) or "")
            for k in ("question", "gap_report", "final_report", "router_plan_semantic_query")
        )
        toks = _tokens(text_blob)
        if not toks:
            return 0.0
        tset = set(toks)
        qset = set(query_toks)
        if not qset:
            return 0.0
        inter = qset & tset
        iou = len(inter) / max(1, len(qset | tset))
        bset = set(_bigrams(toks))
        bg = len(set(query_bigs) & bset) / max(1, len(query_bigs)) if query_bigs else 0.0
        return iou + 0.25 * bg

    def search(
        self,
        query: str,
        *,
        k: int = 5,
        prefer_ripgrep: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return up to ``k`` matching turns ranked by token overlap.

        Always returns full turn dicts. ``rg`` is used to pre-filter candidate
        lines when present; final scoring is the same Python heuristic.
        """
        if not self.jsonl_path.is_file():
            return []
        q = (query or "").strip()
        if not q:
            return []
        query_toks = _tokens(q)
        query_bigs = _bigrams(query_toks)

        candidates: List[Dict[str, Any]] = []
        used_rg = False
        if prefer_ripgrep and self._has_ripgrep():
            for ln in self._ripgrep_lines(q):
                try:
                    candidates.append(json.loads(ln))
                except Exception:
                    continue
            used_rg = True

        if not candidates:
            candidates = self.read_all()

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for t in candidates:
            score = self._score_line(query_toks, query_bigs, t)
            if score > 0.0:
                scored.append((score, t))

        scored.sort(key=lambda kv: (-kv[0], -int(kv[1].get("turn_index") or 0)))
        out: List[Dict[str, Any]] = []
        for sc, t in scored[:k]:
            obj = dict(t)
            obj["__retrieval_score"] = round(sc, 4)
            obj["__retrieval_method"] = "ripgrep+score" if used_rg else "score_only"
            out.append(obj)
        return out

    def compact_turn(self, turn: Dict[str, Any], *, text_chars: int = 600) -> Dict[str, Any]:
        """Slim a turn for inclusion in another model's user payload."""
        def _clip(s: Any, n: int) -> str:
            s = "" if s is None else str(s)
            return s if len(s) <= n else s[: n - 3] + "..."

        return {
            "turn_id": turn.get("turn_id"),
            "turn_index": turn.get("turn_index"),
            "ts": turn.get("ts"),
            "question": _clip(turn.get("question"), 320),
            "router_plan_semantic_query": _clip(turn.get("router_plan_semantic_query"), 320),
            "gap_report": _clip(turn.get("gap_report"), text_chars),
            "final_report": _clip(turn.get("final_report"), text_chars),
            "score": turn.get("__retrieval_score"),
            "method": turn.get("__retrieval_method"),
        }


def compact_turns(turns: Iterable[Dict[str, Any]], *, text_chars: int = 600) -> List[Dict[str, Any]]:
    """Stateless helper for callers that already have turn dicts."""
    sl = SessionLog(session_id="_", graph_hash="", graph_path="", models={})
    return [sl.compact_turn(t, text_chars=text_chars) for t in turns]
