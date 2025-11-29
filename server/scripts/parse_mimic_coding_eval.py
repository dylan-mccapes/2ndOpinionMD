#!/usr/bin/env python
import glob
import json
import os
import re
import sys

import psycopg2


OUTDIR = os.environ.get("MIMIC_CODING_EVAL_DIR", "/tmp/mimic_coding_eval")
DB_NAME = os.environ.get("PGDATABASE", "2ndopinionmd")

# These events are meta / plumbing; we want the coding_result payload instead.
IGNORE_EVENTS = {
    "start",
    "status",
    "phase_start",
    "phase_end",
    "matches",
    "valyu_debug",
}


def parse_sse_file(path: str):
    """Parse an SSE log file and return the most relevant JSON payload.

    Strategy:

      - Prefer the last event whose name is NOT in IGNORE_EVENTS.
      - Special case: if there is a coding_result event, return that first.
      - If none, fall back to the last event with valid JSON.
    """
    events = []
    event_name = None
    data_lines = []

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            # Blank line = end of event block
            if line == "":
                if event_name is not None and data_lines:
                    data_str = "\n".join(
                        l[5:].lstrip() if l.startswith("data:") else l
                        for l in data_lines
                    )
                    payload = None
                    try:
                        payload = json.loads(data_str)
                    except Exception:
                        # Not JSON – ignore
                        pass
                    events.append((event_name, payload, data_str))
                event_name = None
                data_lines = []
                continue

            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line)
            else:
                # Sometimes there might be lines without prefixes – treat as data
                data_lines.append("data:" + line)

        # Flush last block if file doesn't end with a blank line
        if event_name is not None and data_lines:
            data_str = "\n".join(
                l[5:].lstrip() if l.startswith("data:") else l
                for l in data_lines
            )
            payload = None
            try:
                payload = json.loads(data_str)
            except Exception:
                pass
            events.append((event_name, payload, data_str))

    # 1) Prefer coding_result event (coding_mode output)
    for name, payload, _ in events:
        if name == "coding_result" and payload is not None:
            return name, payload, None

    # 2) Fallback: last JSON event, preferring non-ignored
    valid_events = [e for e in events if e[1] is not None]
    if not valid_events:
        return None

    candidates = [e for e in valid_events if e[0] not in IGNORE_EVENTS]
    if candidates:
        return candidates[-1]

    return valid_events[-1]


def main():
    pattern = os.path.join(OUTDIR, "eval_*.sse")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No SSE files found in {OUTDIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files)} SSE files in {OUTDIR}")

    conn = psycopg2.connect(dbname=DB_NAME)
    conn.autocommit = False
    cur = conn.cursor()

    updated = 0

    for path in files:
        m = re.search(r"eval_(\d+)\.sse$", os.path.basename(path))
        if not m:
            print(f"Skipping {path}: cannot extract eval_id")
            continue
        eval_id = int(m.group(1))

        parsed = parse_sse_file(path)
        if parsed is None:
            print(f"[eval_id={eval_id}] No JSON payload found")
            continue

        event_name, payload, _data_str = parsed
        print(f"[eval_id={eval_id}] Using event '{event_name}'")

        # Default: no codes
        pred_codes: list[str] = []
        pred_versions: list[int | None] = []

        # If this is our new coding_result event, extract codes
        if event_name == "coding_result" and isinstance(payload, dict):
            raw_codes = payload.get("codes") or []

            if isinstance(raw_codes, list):
                for item in raw_codes:
                    if isinstance(item, dict):
                        code = (item.get("code") or "").strip()
                        version = item.get("version")
                    else:
                        code = str(item).strip()
                        version = None

                    if not code:
                        continue

                    pred_codes.append(code)
                    pred_versions.append(None if version is None else int(version))

        # Always store full payload in pred_raw
        if pred_codes:
            # We have codes → set pred_icd_* explicitly
            cur.execute(
                """
                UPDATE eval.coding_eval_results_mimic4
                SET pred_raw = %s,
                    pred_icd_codes = %s,
                    pred_icd_versions = %s
                WHERE eval_id = %s
                """,
                (json.dumps(payload), pred_codes, pred_versions, eval_id),
            )
        else:
            # No codes → just stash pred_raw; leave pred_icd_* alone
            cur.execute(
                """
                UPDATE eval.coding_eval_results_mimic4
                SET pred_raw = %s
                WHERE eval_id = %s
                """,
                (json.dumps(payload), eval_id),
            )

        if cur.rowcount == 0:
            print(f"[eval_id={eval_id}] No row in results table to update")
        else:
            updated += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Updated pred_raw for {updated} evals.")


if __name__ == "__main__":
    main()