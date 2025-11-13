# server/scripts/n2c2_ap_rag_upsert.py
#!/usr/bin/env python3
import os, psycopg
DSN = os.getenv("SYNC_DATABASE_URL","postgresql://localhost/2ndopinionmd")

SQL = """
INSERT INTO rag_corpus (source, title, text)
SELECT
  'n2c2_t3_ap' AS source,
  CONCAT(label, ': ', left(assessment,80), ' \u2192 ', left(plan_item,80)) AS title,
  CONCAT(assessment, E'\nPlan: ', plan_item) AS text
FROM text.v_n2c2_ap_pairs
ON CONFLICT DO NOTHING;
"""
with psycopg.connect(DSN) as conn, conn.cursor() as cur:
    cur.execute(SQL)
    print(f"Inserted {cur.rowcount} n2c2 A&P rows into rag_corpus.")
