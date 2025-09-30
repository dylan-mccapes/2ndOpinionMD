# server/scripts/rag_upsert_from_cdc.py
import psycopg2, os
SQL = """
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT 'cdc_opioid' AS source,
       d.title || COALESCE(' — '||s.heading,'') AS title,
       s.text_plain AS text,
       now()
FROM guidelines.cdc_sections s
JOIN guidelines.cdc_docs d ON d.doc_id = s.doc_id
ON CONFLICT DO NOTHING;
"""
if __name__ == "__main__":
    conn = psycopg2.connect(os.environ["SYNC_DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    cur.close(); conn.close()

