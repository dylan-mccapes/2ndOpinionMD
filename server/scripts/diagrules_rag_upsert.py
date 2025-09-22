#!/usr/bin/env python3
import os, json, psycopg2
from datetime import date
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT, ".env"))
DBURL = (os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd").replace("+asyncpg","")

def _fmt_rule_text(row):
    """
    Render a concise, searchable text block for RAG.
    Keep the first ~2-3 screens worth; evaluator JSON stays in meta.
    """
    title   = row["title"] or ""
    org     = row["org"] or ""
    cond    = row["condition"] or ""
    ver     = row["version"] or ""
    pub     = row["published_date"] or ""
    notes   = row.get("notes") or ""
    urls    = row.get("source_urls") or []

    # Short explainer derived from rule_json keys (dont expand all logic)
    rj = row.get("rule_json") or {}
    logic = rj.get("logic", {})
    outputs = rj.get("outputs", {})

    lines = []
    lines.append(f"{title}  {org} ({ver})")
    lines.append(f"Condition: {cond}")
    if pub:
        lines.append(f"Published: {pub}")
    if notes:
        lines.append(f"Notes: {notes}")
    if outputs:
        lines.append(f"Outputs: {json.dumps(outputs, ensure_ascii=False)}")
    # Very light peek into the logic for keywordability
    if isinstance(logic, dict):
        # Only list the top-level operators to seed BM25 keywords
        ops = ", ".join(sorted(k for k in logic.keys()))
        lines.append(f"Logic: top operators = {ops}")

    if urls:
        lines.append("Sources: " + " | ".join(urls[:4]))
    lines.append("")  # spacer
    lines.append("Summary:")
    lines.append(f"This row represents a diagnostic classification rule for {cond} derived from {org} guidance. Use evaluator for structured application; this text is for search/retrieval context.")

    return "\n".join(lines)

def main():
    conn = psycopg2.connect(DBURL)
    with conn, conn.cursor() as cur:
        cur.execute("""
            SELECT rule_key, title, org, condition, version, published_date, rule_json, notes, source_urls
            FROM guidelines.diagnostic_rules
        """)
        rules = cur.fetchall()
        cols = [d[0] for d in cur.description]

        upserted = 0
        for r in rules:
            row = dict(zip(cols, r))
            text = _fmt_rule_text(row)
            meta = {
                "type": "diagnostic_rule",
                "rule_key": row["rule_key"],
                "org": row["org"],
                "condition": row["condition"],
                "version": row["version"],
                "published_date": row["published_date"].isoformat() if isinstance(row["published_date"], (date,)) else row["published_date"],
                "source_urls": row.get("source_urls") or [],
                "rule_json": row.get("rule_json") or {},
            }
            title = f"ACR/EULAR: {row['condition']}  {row['title']} ({row.get('version','')})".strip()

            # Insert/update into rag_corpus
            cur.execute("""
                INSERT INTO public.rag_corpus (source, title, text, meta, ts)
                VALUES (%s, %s, %s, %s::jsonb,
                        to_tsvector('english', coalesce(%s,'') || ' ' || coalesce(%s,'')))
                ON CONFLICT DO NOTHING
            """, ('acr_eular', title, text, json.dumps(meta), title, text))

            # If already existed, refresh text/title/meta (idempotent upsert-ish)
            cur.execute("""
                UPDATE public.rag_corpus
                SET title = %s,
                    text  = %s,
                    meta  = %s::jsonb,
                    ts    = to_tsvector('english', coalesce(%s,'') || ' ' || coalesce(%s,''))
                WHERE source='acr_eular' AND (meta->>'rule_key') = %s
            """, (title, text, json.dumps(meta), title, text, row["rule_key"]))

            upserted += 1

    print(f"Upserted {upserted} ACR/EULAR rules into rag_corpus.")
    conn.close()

if __name__ == "__main__":
    main()

