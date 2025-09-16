import os, json, psycopg2, psycopg2.extras as pe
from dotenv import dotenv_values
from openai import OpenAI

cfg = dotenv_values(os.path.join("server",".env"))
DATABASE_URL = cfg.get("DATABASE_URL") or os.getenv("DATABASE_URL")
OPENAI_API_KEY = cfg.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBED_MODEL","text-embedding-3-small")
BATCH = int(os.getenv("EMBED_BATCH","256"))

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_rows(cur, limit=50000):
    cur.execute("""
      SELECT id, COALESCE(title,'') || E'\n\n' || COALESCE(body,'') AS doc
      FROM public.medical_knowledge
      WHERE embedding IS NULL
      LIMIT %s
    """, (limit,))
    return cur.fetchall()

def main():
    if not DATABASE_URL or not OPENAI_API_KEY:
        raise SystemExit("Set DATABASE_URL and OPENAI_API_KEY")
    conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
    while True:
        rows = fetch_rows(cur)
        if not rows: break
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i+BATCH]
            ids   = [r[0] for r in chunk]
            docs  = [r[1] for r in chunk]
            embs = client.embeddings.create(model=MODEL, input=docs).data
            vecs = [json.dumps(e.embedding) for e in embs]
            pe.execute_values(cur, """
              UPDATE public.medical_knowledge AS mk
              SET embedding = data.embedding::vector
              FROM (VALUES %s) AS data(id, embedding)
              WHERE mk.id = data.id::bigint
            """, list(zip(ids, vecs)), page_size=64)
            conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
