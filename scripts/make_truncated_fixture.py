#!/usr/bin/env python3
"""Cut the first N pages from data/NormanEricRoberts_decrypted_from_browser.pages.json.

Creates data/NormanEricRoberts_decrypted_truncated.pages.json for fast
dev iteration on the chapter-aware ingest pipeline without paying for the
full 4,223-page record.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=200)
    ap.add_argument(
        "--src",
        default="data/NormanEricRoberts_decrypted_from_browser.pages.json",
    )
    ap.add_argument(
        "--dst",
        default="data/NormanEricRoberts_decrypted_truncated.pages.json",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = root / args.src
    dst = root / args.dst
    with src.open("r", encoding="utf-8") as f:
        d = json.load(f)

    n = max(1, int(args.pages))
    pages = d["pages"][:n]
    out = {
        "source_pdf": "NormanEricRoberts_decrypted_truncated.pdf",
        "source_sha256": d.get("source_sha256"),
        "extracted_at": d.get("extracted_at"),
        "total_pages": len(pages),
        "pages_with_text": sum(1 for p in pages if (p.get("text") or "").strip()),
        "needs_ocr": [p["page_num"] for p in pages if not (p.get("text") or "").strip()],
        "elapsed_seconds": None,
        "pages": pages,
        "truncation_note": (
            f"first {n} pages of NormanEricRoberts_decrypted ({d.get('total_pages')} total) "
            "for fast dev iteration of the chapter-aware ingest pipeline"
        ),
    }

    with dst.open("w", encoding="utf-8") as f:
        json.dump(out, f)

    print(
        f"wrote {dst} ({os.path.getsize(dst)//1024} KB)  pages_with_text={out['pages_with_text']}  "
        f"needs_ocr={len(out['needs_ocr'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
