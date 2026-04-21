#!/usr/bin/env python3
"""
Export the FastAPI OpenAPI schema to a JSON file (no running server required).

Usage (from repo root, with venv that has FastAPI installed):
  python -m server.scripts.export_openapi
  python -m server.scripts.export_openapi -o docs/openapi.json

Makefile (uses server/venv312/bin/python):
  make openapi-export

Alternatively, with the API already running:
  curl -sS http://localhost:8000/api/openapi.json -o docs/openapi.json
  curl -sS http://localhost:8000/openapi.json -o docs/openapi.json

Interactive docs: http://localhost:8000/docs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Write FastAPI OpenAPI JSON to a file.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path (default: docs/openapi.json)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    out = args.output or (root / "docs" / "openapi.json")

    # Import after argparse so --help works without loading the app stack.
    from server.api import app_postgres  # noqa: WPS433

    spec = app_postgres.app.openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(spec.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
