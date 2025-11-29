#!/usr/bin/env python
import json
import re
import sys

import psycopg2


DB_NAME = "2ndopinionmd"

# Loose-ish matcher for ICD9/10-style codes:
# - 3–7 chars
# - uppercase letters, digits, dot, or X
ICD_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{2,6}$")


def collect_strings(obj):
    """Recursively collect all string leaves from a JSON-like structure."""
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, list):
        for x in obj:
            out.extend(collect_strings(x))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(collect_strings(v))
    return out


def normalize_code(code: str) -> str:
    """
    Normalize ICD codes for comparison.

    - Uppercase
    - Strip whitespace
    - Remove dots, hyphens, and other non-alphanumerics

    Examples:
      'K65.1' -> 'K651'
      'k651 ' -> 'K651'
    """
    if not code:
        return ""
    code = code.upper().strip()
    code = re.sub(r"[^A-Z0-9]", "", code)
    return code


def compute_metrics(gold_codes, pred_codes):
    """
    Compute precision/recall/F1 with normalized codes.

    Returns a dict:
      {
        "precision": float,
        "recall": float,
        "f1": float,
        "tp": [original-code strings],
        "fp": [...],
        "fn": [...],
      }
    """
    # Map normalized -> original for gold/pred
    gold_map = {}
    for c in gold_codes or []:
        norm = normalize_code(c)
        if not norm:
            continue
        # keep first original we see for that norm key
        gold_map.setdefault(norm, c)

    pred_map = {}
    for c in pred_codes or []:
        norm = normalize_code(c)
        if not norm:
            continue
        pred_map.setdefault(norm, c)

    gold_keys = set(gold_map.keys())
    pred_keys = set(pred_map.keys())

    tp_keys = sorted(gold_keys & pred_keys)
    fp_keys = sorted(pred_keys - gold_keys)
    fn_keys = sorted(gold_keys - pred_keys)

    tp = [gold_map[k] for k in tp_keys]
    fp = [pred_map[k] for k in fp_keys]
    fn = [gold_map[k] for k in fn_keys]

    tp_count = len(tp_keys)
    fp_count = len(fp_keys)
    fn_count = len(fn_keys)

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) else 0.0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def main():
    # Optionally allow a single eval_id as CLI arg
    eval_filter = None
    if len(sys.argv) == 2:
        try:
            eval_filter = int(sys.argv[1])
        except ValueError:
            print("If provided, arg must be an integer eval_id", file=sys.stderr)
            sys.exit(1)

    conn = psycopg2.connect(dbname=DB_NAME)
    cur = conn.cursor()

    # If we're inspecting a single eval, check whether note-level gold exists
    if eval_filter is not None:
        cur2 = conn.cursor()
        cur2.execute(
            """
            SELECT 1
            FROM eval.coding_eval_note_gold
            WHERE eval_id = %s
            LIMIT 1;
            """,
            (eval_filter,),
        )
        if cur2.fetchone():
            print("Using note-level gold from eval.coding_eval_note_gold")
        cur2.close()

    if eval_filter is None:
        cur.execute(
            """
            SELECT eval_id,
                   hadm_id,
                   gold_icd_codes,
                   pred_raw
            FROM eval.coding_eval_results_mimic4
            WHERE pred_raw IS NOT NULL
            ORDER BY eval_id DESC
            LIMIT 10;
            """
        )
    else:
        cur.execute(
            """
            SELECT eval_id,
                   hadm_id,
                   gold_icd_codes,
                   pred_raw
            FROM eval.coding_eval_results_mimic4
            WHERE eval_id = %s;
            """,
            (eval_filter,),
        )

    rows = cur.fetchall()
    if not rows:
        print("No rows found with pred_raw populated")
        cur.close()
        conn.close()
        return

    for eval_id, hadm_id, gold_codes, pred_raw in rows:
        print("=" * 80)
        print(f"eval_id={eval_id}, hadm_id={hadm_id}")

        # Encounter-level (MIMIC) gold codes
        gold_codes = list(gold_codes or [])
        print(f"  ENCOUNTER GOLD ({len(gold_codes)}): {gold_codes}")

        # Derive predicted codes:
        # 1) If pred_raw has "codes", prefer that.
        # 2) Otherwise, fall back to ICD-like strings in the JSON.
        pred_codes: list[str] = []

        if isinstance(pred_raw, dict):
            raw_codes = pred_raw.get("codes")
            if isinstance(raw_codes, list) and raw_codes:
                for item in raw_codes:
                    if isinstance(item, dict):
                        code = (item.get("code") or "").strip()
                    else:
                        code = str(item).strip()
                    if code:
                        pred_codes.append(code)

        # Fallback: scan entire pred_raw for ICD-like strings
        if not pred_codes:
            strings = collect_strings(pred_raw)
            pred_codes = sorted({s for s in strings if ICD_RE.match(s)})

        print(f"  PRED ({len(pred_codes)}): {pred_codes}")

        # --------------------------------------------------------------------
        # Encounter-level metrics (MIMIC gold vs preds)
        # --------------------------------------------------------------------
        enc_metrics = compute_metrics(gold_codes, pred_codes)
        print("  ENCOUNTER-LEVEL METRICS (MIMIC gold vs preds)")
        print(f"    precision={enc_metrics['precision']:.3f}, "
              f"recall={enc_metrics['recall']:.3f}, "
              f"f1={enc_metrics['f1']:.3f}")
        print(f"    TP ({len(enc_metrics['tp'])}): {enc_metrics['tp']}")
        print(f"    FP ({len(enc_metrics['fp'])}): {enc_metrics['fp']}")
        print(f"    FN ({len(enc_metrics['fn'])}): {enc_metrics['fn']}")

        # --------------------------------------------------------------------
        # Note-level gold (curated) metrics, if available
        # --------------------------------------------------------------------
        cur2 = conn.cursor()
        cur2.execute(
            """
            SELECT gold_icd10_codes
            FROM eval.coding_eval_note_gold
            WHERE eval_id = %s;
            """,
            (eval_id,),
        )
        note_row = cur2.fetchone()
        cur2.close()

        if note_row and note_row[0]:
            note_gold_codes = [c for c in note_row[0] if c]
            print(f"  NOTE GOLD ({len(note_gold_codes)}): {note_gold_codes}")

            note_metrics = compute_metrics(note_gold_codes, pred_codes)
            print("  NOTE-LEVEL METRICS (curated note_gold vs preds)")
            print(f"    precision={note_metrics['precision']:.3f}, "
                  f"recall={note_metrics['recall']:.3f}, "
                  f"f1={note_metrics['f1']:.3f}")
            print(f"    TP ({len(note_metrics['tp'])}): {note_metrics['tp']}")
            print(f"    FP ({len(note_metrics['fp'])}): {note_metrics['fp']}")
            print(f"    FN ({len(note_metrics['fn'])}): {note_metrics['fn']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()