#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
from pathlib import Path

here = Path(__file__).resolve().parent
server_env = here.parent / ".env"
if server_env.exists(): load_dotenv(server_env)
root_env = here.parent.parent / ".env"
if root_env.exists(): load_dotenv(root_env)

def dsn():
    url = os.getenv("DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")
    return (url or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd").replace("+asyncpg", "")

SQL = """
WITH cards AS (
  SELECT
    ilx_id,
    preferred_label,
    definition,
    array_to_string(synonyms, '; ') AS syns,
    COALESCE(category,'Neurology') AS cat,
    'NeuroLex: '||preferred_label||' ['||ilx_id||']' AS title,
    trim(both ' ' FROM concat_ws(' ',
      COALESCE(definition,''), 'Synonyms:', COALESCE(array_to_string(synonyms, '; '), ''),
      'Category:', COALESCE(category,'Neurology')
    )) AS text
  FROM ontology.neurolex_terms
)
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT 'neurolex', c.title, c.text,
       to_tsvector('english', c.title||' '||c.text)
FROM cards c
WHERE NOT EXISTS (
  SELECT 1 FROM public.rag_corpus r WHERE r.source='neurolex' AND r.title=c.title
);

UPDATE public.rag_corpus
SET ts = to_tsvector('english', COALESCE(title,'')||' '||COALESCE(text,''))
WHERE source='neurolex' AND ts IS NULL;
"""

if __name__ == "__main__":
    conn = psycopg2.connect(dsn())
    with conn, conn.cursor() as cur:
        cur.execute(SQL)
        print("NeuroLex → rag_corpus upsert complete.")

