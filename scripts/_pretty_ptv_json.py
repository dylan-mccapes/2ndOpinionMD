#!/usr/bin/env python3
"""Re-format a Patient Timeline Vision JSON dump for editors (indent, UTF-8).

Repairs a bad export where **literal** two-character ``\\n`` / ``\\r`` / ``\\t``
appear **between** JSON tokens (invalid JSON), while leaving all characters
**inside** JSON strings unchanged (so real ``\\n`` escapes inside strings stay
intact for ``json.loads``).

Also collapses doubled backslashes before a quote (e.g. ``11\\"`` inches).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def _needs_literal_ws_repair(s: str) -> bool:
    return len(s) >= 3 and s[0] == "{" and s[1] == "\\" and s[2] in "nrt"


def _repair_literal_newlines_outside_strings(s: str) -> str:
    """Replace literal ``\\n`` / ``\\r`` / ``\\t`` only outside JSON strings."""
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if in_string:
            if escaped:
                out.append(c)
                escaped = False
            elif c == "\\":
                out.append(c)
                escaped = True
            elif c == '"':
                out.append(c)
                in_string = False
            else:
                out.append(c)
            i += 1
            continue
        if c == '"':
            out.append(c)
            in_string = True
        elif c == "\\" and i + 1 < n and s[i + 1] == "n":
            out.append("\n")
            i += 2
            continue
        elif c == "\\" and i + 1 < n and s[i + 1] == "r":
            out.append("\r")
            i += 2
            continue
        elif c == "\\" and i + 1 < n and s[i + 1] == "t":
            out.append("\t")
            i += 2
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _collapse_doubled_backslash_before_quote(s: str) -> str:
    r"""Collapse ``\\"`` → ``\"`` repeatedly until stable (fixes ``11\\"`` inches)."""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\\{2}(?=")', r"\\", s)
    return s


def _loads_repaired(s: str) -> object:
    last_err: json.JSONDecodeError | None = None
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        last_err = e

    # Collapse ``11\\"`` → ``11\"`` *before* newline repair so the string-state
    # scanner does not treat the inch ``"`` as closing the JSON string early.
    s = _collapse_doubled_backslash_before_quote(s)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        last_err = e

    if _needs_literal_ws_repair(s):
        s = _repair_literal_newlines_outside_strings(s)
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            last_err = e

    assert last_err is not None
    raise last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path, help="Input JSON file (PTV graph dump)")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input with .bak backup)",
    )
    ap.add_argument("--indent", type=int, default=2)
    args = ap.parse_args()

    src: Path = args.path
    if not src.is_file():
        print(f"not found: {src}", file=sys.stderr)
        return 1

    raw = src.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    if raw.lstrip().startswith("(") and ")" in raw.lstrip()[:120]:
        lines = raw.splitlines()
        while lines and not lines[0].lstrip().startswith("{"):
            lines.pop(0)
        raw = "\n".join(lines)

    try:
        data = _loads_repaired(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON after repair attempts: {e}", file=sys.stderr)
        return 1

    out = args.output
    if out is None:
        bak = src.with_suffix(src.suffix + ".bak")
        shutil.copy2(src, bak)
        out = src
        print(f"backup: {bak}", file=sys.stderr)

    out.write_text(
        json.dumps(data, indent=args.indent, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
