import json, os
import psycopg2
import psycopg2.extras as pe
from dotenv import dotenv_values

# Prefer SYNC_DATABASE_URL for psycopg2; fall back to DATABASE_URL
cfg = dotenv_values(os.path.join("server", ".env"))
DATABASE_URL = os.getenv("SYNC_DATABASE_URL") or cfg.get("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or cfg.get("DATABASE_URL")
SRC = os.path.join("server", "data", "medical_data.json")

def rows():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict) and "caseStudies" in data:
            for case in data["caseStudies"]:
                return (x for x in data["caseStudies"])
        elif isinstance(data, list):
            return (x for x in data)
        else:
            return iter([data])

def pick(d):
    title = d.get("title") or d.get("name") or d.get("primaryCondition") or d.get("caseId") or None
    # Standardize on 'content' (NOT NULL in your table)
    content = d.get("content") or d.get("body") or d.get("text") or d.get("description") or d.get("summary") or None

    if not content and "symptomTimeline" in d:
        parts = []
        if d.get("primaryCondition"):
            parts.append(f"Primary Condition: {d['primaryCondition']}")
        if d.get("symptomTimeline"):
            parts.append("Symptoms: " + ("; ".join(d["symptomTimeline"]) if isinstance(d["symptomTimeline"], list) else str(d["symptomTimeline"])))
        if d.get("diagnosticZone"):
            parts.append(f"Diagnostic Zone: {d['diagnosticZone']}")
        if d.get("staxScore"):
            parts.append(f"STAX Score: {d['staxScore']}")
        content = ". ".join(parts)

    # Ensure we never violate NOT NULL on content
    if content is None:
        content = ""

    meta = {k: v for k, v in d.items() if k not in ("title", "name", "primaryCondition", "caseId", "body", "text", "description", "content", "summary", "symptomTimeline")}
    return ("curated", title, content, json.dumps(meta, ensure_ascii=False))

def main():
    if not DATABASE_URL:
        raise SystemExit("Set SYNC_DATABASE_URL or DATABASE_URL in env/server/.env")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    data_iter = rows()
    batch = [pick(d) for d in data_iter]

    if not batch:
        print("No docs found in server/data/medical_data.json")
        return

    pe.execute_values(cur, """
      INSERT INTO public.medical_knowledge (content_type, title, content, metadata)
      VALUES %s
      ON CONFLICT DO NOTHING
    """, batch, page_size=1000)

    conn.commit()
    conn.close()
    print(f"Inserted {len(batch)} docs")

if __name__ == "__main__":
    main()
