import os, json, psycopg2, psycopg2.extras as pe
from dotenv import dotenv_values
from openai import OpenAI

def get_sync_database_url():
    """Get sync database URL, auto-converting from async URL if needed"""
    cfg = dotenv_values(os.path.join("server",".env"))
    sync_url = cfg.get("SYNC_DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url
    
    async_url = cfg.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if async_url and "+asyncpg" in async_url:
        return async_url.replace("postgresql+asyncpg://", "postgresql://")
    return async_url

DATABASE_URL = (
    os.getenv("SYNC_DATABASE_URL")
    or cfg.get("SYNC_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or cfg.get("DATABASE_URL")
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBED_MODEL","text-embedding-3-small")
BATCH = int(os.getenv("EMBED_BATCH","256"))
client = OpenAI(api_key=OPENAI_API_KEY)

def main():
    if not DATABASE_URL or not OPENAI_API_KEY:
        raise SystemExit("Set DATABASE_URL/SYNC_DATABASE_URL and OPENAI_API_KEY")
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    total_embedded = 0
    while True:
        cur.execute("""
          SELECT id, COALESCE(title,'') || E'\n\n' || COALESCE(text,'') AS doc
          FROM public.rag_corpus
          WHERE embedding IS NULL
          LIMIT 50000
        """)
        rows = cur.fetchall()
        if not rows: 
            break
            
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i+BATCH]
            ids   = [r[0] for r in chunk]
            docs  = [r[1] for r in chunk]
            
            try:
                embs = client.embeddings.create(model=MODEL, input=docs).data
                vecs = [json.dumps(e.embedding) for e in embs]
                pe.execute_values(cur, """
                  UPDATE public.rag_corpus AS rc
                  SET embedding = data.embedding::vector
                  FROM (VALUES %s) AS data(id, embedding)
                  WHERE rc.id = data.id::bigint
                """, list(zip(ids, vecs)), page_size=64)
                conn.commit()
                total_embedded += len(chunk)
                print(f"Embedded {total_embedded} rows so far...")
            except Exception as e:
                print(f"Error embedding batch: {e}")
                conn.rollback()
                break
    
    conn.close()
    print(f"Total embedded: {total_embedded} rows")

if __name__ == "__main__":
    main()
