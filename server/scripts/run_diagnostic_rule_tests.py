import os, json, sys, psycopg2
from dotenv import load_dotenv

# --- Make sure we can import the 'server' package ---
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server.utils.diagnostic_rule_eval import evaluate

# --- DB config ---
load_dotenv(os.path.join(ROOT, ".env"))
DBURL = (os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd").replace("+asyncpg","")

def main():
    tests_path = os.path.join(ROOT, "data", "diagnostic_rule_tests.json")
    try:
        with open(tests_path, "r", encoding="utf-8") as f:
            tests = json.load(f)
    except Exception as e:
        print(f" Failed to read {tests_path}: {e}")
        sys.exit(2)

    conn = psycopg2.connect(DBURL)
    failures = 0
    with conn, conn.cursor() as cur:
        for t in tests:
            rk = t["rule_key"]
            cur.execute(
                "SELECT rule_json->>'name', rule_json FROM guidelines.diagnostic_rules WHERE rule_key=%s",
                (rk,)
            )
            row = cur.fetchone()
            if not row:
                print(f" {rk}: rule not found")
                failures += 1
                continue
            name, rj = row
            out = evaluate(rj, t["patient_facts"])
            ok = (out.get("label") == t["expected_label"])
            mark = "" if ok else ""
            print(f"{mark} {rk} - {name} -> {out.get('label')}")
            if not ok:
                print(f"   expected: {t['expected_label']}")
                failures += 1
    conn.close()
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
