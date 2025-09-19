# server/scripts/embed_table.py
import os
import json
import argparse
import psycopg2
import psycopg2.extras as pe
from psycopg2 import sql
from dotenv import load_dotenv, dotenv_values
from openai import OpenAI

# ---------- env / config helpers ----------
def _get_sync_database_url():
    """
    Resolve a sync (psycopg2) DATABASE URL. Prefer SYNC_DATABASE_URL,
    else convert DATABASE_URL if it's asyncpg.
    """
    # Load .env from project root and server/.env (best-effort)
    load_dotenv(".env")
    load_dotenv("server/.env")
    cfg = {}
    try:
        cfg.update(dotenv_values(".env") or {})
        cfg.update(dotenv_values("server/.env") or {})
    except Exception:
        pass

    sync_url = os.getenv("SYNC_DATABASE_URL") or cfg.get("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_url = os.getenv("DATABASE_URL") or cfg.get("DATABASE_URL")
    if db_url and "+asyncpg" in db_url:
        return db_url.replace("postgresql+asyncpg://", "postgresql://")
    return db_url


# ---------- main embed logic ----------
def parse_args():
    p = argparse.ArgumentParser(description="Embed rows for a table using OpenAI embeddings and store into a pgvector column.")
    p.add_argument("--table", required=True, help="Target table (schema.table or table)")
    p.add_argument("--id-col", required=True, help="Primary key column name")
    p.add_argument("--text-col", required=True, help="Text column to embed")
    p.add_argument("--embedding-col", required=True, help="Vector column to write (pgvector)")
    p.add_argument("--where", default=None, help="Additional WHERE clause (without 'WHERE')")
    p.add_argument("--batch", type=int, default=int(os.getenv("EMBED_BATCH", "256")), help="Embedding batch size")
    p.add_argument("--model", default=os.getenv("EMBED_MODEL", "text-embedding-3-small"), help="OpenAI embedding model")
    return p.parse_args()


def _qualify_table(table_str):
    if "." in table_str:
        schema, table = table_str.split(".", 1)
    else:
        schema, table = "public", table_str
    return schema, table


def fetch_batch(cur, schema, table, id_col, text_col, emb_col, where_clause, limit):
    """
    Fetch a batch of rows needing embeddings.
    Returns list of (id_as_text, text_document).
    """
    # SELECT <id_col>::text AS id, <text_col> AS doc FROM <schema>.<table>
    # WHERE <emb_col> IS NULL [AND (<where_clause>)] LIMIT %s;
    base = sql.SQL("""
        SELECT {id_col}::text AS id, {text_col} AS doc
        FROM {schema}.{table}
        WHERE {emb_col} IS NULL
    """).format(
        id_col=sql.Identifier(id_col),
        text_col=sql.Identifier(text_col),
        schema=sql.Identifier(schema),
        table=sql.Identifier(table),
        emb_col=sql.Identifier(emb_col),
    )

    if where_clause:
        q = base + sql.SQL(" AND (") + sql.SQL(where_clause) + sql.SQL(") ") + sql.SQL("LIMIT %s")
        cur.execute(q, (limit,))
    else:
        q = base + sql.SQL(" LIMIT %s")
        cur.execute(q, (limit,))

    return cur.fetchall()


def run():
    args = parse_args()

    db_url = _get_sync_database_url()
    if not db_url:
        raise SystemExit("Set SYNC_DATABASE_URL or DATABASE_URL in your environment or .env")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise SystemExit("Set OPENAI_API_KEY in your environment or .env")

    client = OpenAI(api_key=openai_key)
    schema, table = _qualify_table(args.table)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    total = 0
    while True:
        rows = fetch_batch(cur, schema, table, args.id_col, args.text_col, args.embedding_col, args.where, args.batch)
        if not rows:
            break

        # Chunk rows for embedding API
        for i in range(0, len(rows), args.batch):
            chunk = rows[i:i + args.batch]
            ids = [r[0] for r in chunk]          # already text via ::text
            docs = [r[1] or "" for r in chunk]   # ensure no None

            try:
                # Create embeddings
                resp = client.embeddings.create(model=args.model, input=docs)
                vecs = [json.dumps(e.embedding) for e in resp.data]  # store as JSON string → cast to vector in SQL

                # UPDATE <schema>.<table> AS mk
                # SET <embedding_col> = data.emb::vector
                # FROM (VALUES %s) AS data(id, emb)
                # WHERE mk.<id_col>::text = data.id
                update_sql = sql.SQL("""
                    UPDATE {schema}.{table} AS mk
                    SET {emb_col} = data.emb::vector
                    FROM (VALUES %s) AS data(id, emb)
                    WHERE mk.{id_col}::text = data.id
                """).format(
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    emb_col=sql.Identifier(args.embedding_col),
                    id_col=sql.Identifier(args.id_col),
                )

                # Prepare (id, emb_json) pairs; ids are already text
                pairs = list(zip(ids, vecs))
                pe.execute_values(cur, update_sql.as_string(conn), pairs, page_size=64)
                conn.commit()

                total += len(chunk)
                print(f"Embedded {total} rows so far...")

            except Exception as e:
                print(f"Error embedding batch: {e}")
                conn.rollback()
                # don't break hard—try next batch; if it's a permanent issue, loop will finish
                continue

    cur.close()
    conn.close()
    print(f"Total embedded: {total} rows")


if __name__ == "__main__":
    run()

