#!/usr/bin/env python3
"""
Run table-driven diagnostic rule tests.

Sources:
  - rules:   guidelines.diagnostic_rules(rule_key, rule_json, ...)
  - tests:   guidelines.diagnostic_rule_tests(test_id, rule_key, patient_facts, expected_label)

Semantics:
  - A test with expected_label IN ('n/a', NULL, '') is treated as a SMOKE test:
      * We execute the rule to ensure it runs and returns a label, but we do NOT assert equality.
      * Such tests always count as passed unless evaluation errors.
  - Any other expected_label is a HARD test:
      * We require exact string equality with the returned 'label' (case-sensitive).
      * A mismatch is a FAIL.

CLI:
  PYTHONPATH=. ./server/scripts/run_diagnostic_rule_tests.py [--only RULE_KEY] [--format text|json]

Examples:
  PYTHONPATH=. python3 server/scripts/run_diagnostic_rule_tests.py
  PYTHONPATH=. python3 server/scripts/run_diagnostic_rule_tests.py --only mcdonald_2017
  PYTHONPATH=. python3 server/scripts/run_diagnostic_rule_tests.py --format json
"""

import os
import sys
import json
import argparse
from collections import defaultdict

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# We call the same evaluator used by the API endpoint.
from server.utils.diagnostic_rule_eval import evaluate


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def dburl() -> str:
    # Reuse same pattern as other scripts in repo
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    # psycopg2, not asyncpg
    return url.replace("+asyncpg", "")


def fetch_tests(conn, only_rule_key: str | None):
    sql = """
        SELECT
          t.test_id,
          t.rule_key,
          t.patient_facts,
          t.expected_label,
          r.rule_json
        FROM guidelines.diagnostic_rule_tests t
        JOIN guidelines.diagnostic_rules r USING (rule_key)
    """
    params = []
    if only_rule_key:
        sql += " WHERE t.rule_key = %s"
        params.append(only_rule_key)
    sql += " ORDER BY t.test_id"

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return rows


def is_smoke(expected_label) -> bool:
    if expected_label is None:
        return True
    s = str(expected_label).strip().lower()
    return s == "" or s == "n/a"


def main():
    ap = argparse.ArgumentParser(description="Run diagnostic rule tests.")
    ap.add_argument("--only", help="Limit to a specific rule_key", default=None)
    ap.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = ap.parse_args()

    conn = psycopg2.connect(dburl())

    try:
        rows = fetch_tests(conn, args.only)

        results = []
        totals = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "smoke": 0,
            "hard_total": 0,
            "hard_passed": 0,
            "hard_failed": 0,
        }
        by_rule = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "smoke": 0})
        failures = []

        for r in rows:
            test_id = r["test_id"]
            rule_key = r["rule_key"]
            expected_label = r["expected_label"]
            facts = r["patient_facts"] or {}
            rule_json = r["rule_json"]

            totals["total"] += 1
            by_rule[rule_key]["total"] += 1

            smoke = is_smoke(expected_label)
            if smoke:
                totals["smoke"] += 1
                by_rule[rule_key]["smoke"] += 1

            # Evaluate rule
            error = None
            details = None
            actual_label = None
            ok = False

            try:
                details = evaluate(rule_json, facts or {})
                actual_label = details.get("label")
                if smoke:
                    # Smoke tests: only exercise the rule; count as passed unless evaluation raised
                    ok = True
                else:
                    # Hard assertion: exact string equality (case-sensitive) with expected_label
                    totals["hard_total"] += 1
                    if actual_label == expected_label:
                        ok = True
                        totals["hard_passed"] += 1
                    else:
                        ok = False
                        totals["hard_failed"] += 1
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                ok = False
                if not smoke:
                    totals["hard_total"] += 1
                    totals["hard_failed"] += 1

            # Update global pass/fail counts
            if ok:
                totals["passed"] += 1
                by_rule[rule_key]["passed"] += 1
            else:
                totals["failed"] += 1
                by_rule[rule_key]["failed"] += 1

            # Console line output (text mode)
            if args.format == "text":
                if error:
                    print(f"[ERROR] test_id={test_id} rule={rule_key} error='{error}'")
                else:
                    if smoke:
                        # Match the examples you posted
                        print(f"[SMOKE] test_id={test_id} rule={rule_key} actual='{actual_label}'")
                    else:
                        if ok:
                            print(f"[PASS] test_id={test_id} rule={rule_key} expected='{expected_label}' actual='{actual_label}'")
                        else:
                            print(f"[FAIL] test_id={test_id} rule={rule_key} expected='{expected_label}' actual='{actual_label}'")

            result_row = {
                "test_id": test_id,
                "rule_key": rule_key,
                "expected_label": expected_label,
                "actual_label": actual_label,
                "ok": ok,
                "smoke": smoke,
                "error": error,
                "details": details,
            }
            results.append(result_row)
            if not ok and not smoke:
                failures.append(result_row)

        summary = {
            **totals,
            "by_rule": dict(by_rule),
            "failures": failures,
        }

        if args.format == "text":
            # Match the block you showed earlier
            print("\nSummary:")
            print(f"  total={totals['total']}  passed={totals['passed']}  failed={totals['failed']}  smoke={totals['smoke']}")
            print(f"  hard_total={totals['hard_total']}  hard_passed={totals['hard_passed']}  hard_failed={totals['hard_failed']}")
            print("  by_rule:")
            for rk in sorted(by_rule.keys()):
                br = by_rule[rk]
                print(f"    {rk}: total={br['total']} passed={br['passed']} failed={br['failed']} smoke={br['smoke']}")
            if failures:
                print("  failures:")
                for f in failures:
                    print(f"    test_id={f['test_id']} rule={f['rule_key']} expected='{f['expected_label']}' actual='{f['actual_label']}'")
        else:
            # JSON format identical to what you printed previously
            out = {"results": results, "summary": summary}
            print(json.dumps(out, indent=2))

        # Exit code: non-zero if any hard failures
        if summary["hard_failed"] > 0:
            sys.exit(1)
        sys.exit(0)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
