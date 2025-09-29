# server/scripts/embed_rag_source.py
import os, time
import psycopg2
from openai import OpenAI

SOURCE = os.environ.get("SOURCE", "cdc_opioid")
MODEL  = os.environ.get("EMBED_MODEL", "text-embedding-3-small")

client = OpenAI()  # needs OPENAI_API_KEY
dsn = os.environ["SYNC_DATABASE_URL"]

conn = psycopg2.connect(dsn)
conn.autocommit = False
cur = conn.cursor()

# Only rows with NULL embeddings
cur.execute("""
  SELECT id, text
  FROM public.rag_corpus
  WHERE source = %s AND embedding IS NULL
  ORDER BY id
""", (SOURCE,))
rows = cur.fetchall()

def batches(seq, n=64):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

count = 0
skipped_empty = 0

for raw_batch in batches(rows, 64):
    # Filter out empties/whitespace-only and trim length defensively
    batch = []
    for rid, txt in raw_batch:
        t = (txt or "").strip()
        if not t:
            skipped_empty += 1
            continue
        # trim by characters to stay well below token limits
        t = t[:8000]
        batch.append((rid, t))

    if not batch:
        # nothing to embed in this chunk
        continue

    ids   = [r[0] for r in batch]
    texts = [r[1] for r in batch]

    resp = client.embeddings.create(model=MODEL, input=texts)
    for rid, item in zip(ids, resp.data):
        vec = item.embedding
        # pgvector wants brackets: [x,y,...]
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
        cur.execute(
            "UPDATE public.rag_corpus SET embedding = %s::vector WHERE id = %s",
            (vec_literal, rid),
        )
        count += 1

    conn.commit()
    time.sleep(0.05)

cur.close(); conn.close()
print(f"Embedded {count} rows for source={SOURCE}. Skipped empty texts: {skipped_empty}.")
