"""Quick smoke test for server.timeline.pdf_sectionizer against the truncated fixture."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Import the sectionizer module directly so we don't pull in pydantic-dependent siblings.
import importlib.util, sys as _sys
_spec = importlib.util.spec_from_file_location(
    "pdf_sectionizer", str(ROOT / "server" / "timeline" / "pdf_sectionizer.py")
)
_sectionizer = importlib.util.module_from_spec(_spec)
_sys.modules["pdf_sectionizer"] = _sectionizer
_spec.loader.exec_module(_sectionizer)
sectionize_pages = _sectionizer.sectionize_pages
pack_chapters_into_batches = _sectionizer.pack_chapters_into_batches
estimate_batch_seconds = _sectionizer.estimate_batch_seconds

SRC = ROOT / "data" / "NormanEricRoberts_decrypted_truncated.pages.json"
d = json.loads(SRC.read_text())
pages = [(p["page_num"], p.get("text") or "") for p in d["pages"]]
chapters = sectionize_pages(pages, total_pages=d.get("total_pages"))

print(f"input pages: {len(pages)}  chapters: {len(chapters)}")
kind_counts = Counter(c.kind for c in chapters)
print(f"chapter kinds: {dict(kind_counts)}")

print("\nfirst 12 chapters:")
for c in chapters[:12]:
    print(
        f"  {c.chapter_id:<50s}  kind={c.kind:<8s}  "
        f"pages={len(c.pages):>3d}  chars={c.char_len:>6d}  tokens≈{c.est_tokens:>5d}  "
        f"label={c.label!r}"
    )

# Packing — Ollama 60% fill at 32k context ≈ 78 KB per batch, 40-page cap.
# Ollama 60% × 32k tokens × 4 chars/token, minus ~1200-token system reserve.
max_chars_ollama = int((32768 * 0.60 - 1200) * 4)
print(f"\nOllama batch char budget (60% × 32k): {max_chars_ollama:,}")
batches = pack_chapters_into_batches(
    chapters, max_chars=max_chars_ollama, max_pages_per_batch=40
)
total_eta = sum(
    estimate_batch_seconds(len(b.pages), b.char_len, model="eoh-llama3.1:8b") for b in batches
)
print(f"Ollama batches: {len(batches)}  total ETA ~{total_eta:.0f}s ({total_eta/60:.1f} min)")
for i, b in enumerate(batches[:8]):
    print(
        f"  [{i:02d}] primary={b.primary_chapter_id:<50s}  "
        f"chapters={len(b.chapter_ids):<2d}  pages={len(b.pages):<3d}  chars={b.char_len:>6d}  "
        f"split={b.split_note or '-'}"
    )

# GPT-4.1 packing — 60% × 1M ≈ 2.5M input chars → almost always 1 batch.
max_chars_gpt41 = 60 * 1024 * 1024 // 25  # 60% × 1M tokens × 4 chars
batches_gpt41 = pack_chapters_into_batches(chapters, max_chars=600_000, max_pages_per_batch=None)
total_eta_gpt41 = sum(
    estimate_batch_seconds(len(b.pages), b.char_len, model="gpt-4.1") for b in batches_gpt41
)
print(f"\nGPT-4.1 batches @ 600k chars/batch: {len(batches_gpt41)}  total ETA ~{total_eta_gpt41:.0f}s")
