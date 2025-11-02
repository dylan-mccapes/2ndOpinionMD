#!/usr/bin/env python3
# v2: BFS that follows both inline _links.child and paginated .../children
import os, sys, time, collections
from typing import Any, Dict, Iterable, List, Optional
import requests
import psycopg2, psycopg2.extras

DSN     = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
RELEASE = os.getenv("ICD11_RELEASE", "2024-01")
LINEAR  = os.getenv("ICD11_LINEARIZATION", "MMS")
BASE    = f"https://id.who.int/icd/release/11/{RELEASE}/mms"

# progress / throttles
MAX_ROWS = int(os.getenv("ICD11_MAX", "0") or "0")        # 0 = no cap
TICK     = int(os.getenv("ICD11_TICK", "250") or "250")
PAGE     = int(os.getenv("ICD11_PAGE", "200") or "200")   # children page size

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en",
    "API-Version": "v2",
}

def token() -> str:
    cid = os.getenv("WHO_CLIENT_ID"); sec = os.getenv("WHO_CLIENT_SECRET")
    if not cid or not sec: raise RuntimeError("WHO_CLIENT_ID / WHO_CLIENT_SECRET not set")
    r = requests.post(
        "https://icdaccessmanagement.who.int/connect/token",
        headers={"Content-Type":"application/x-www-form-urlencoded"},
        data={"grant_type":"client_credentials","scope":"icdapi_access",
              "client_id":cid,"client_secret":sec},
        timeout=30,
    )
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok: raise RuntimeError("WHO token missing in response")
    return tok

def api_get(url: str, tok: str) -> Dict[str, Any]:
    r = requests.get(url, headers={**HEADERS, "Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code >= 500:
        time.sleep(1.0)
        r = requests.get(url, headers={**HEADERS, "Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GET {url} -> {r.status_code}: {r.text!r}")
    return r.json()

def _textish(x: Any) -> Optional[str]:
    if x is None: return None
    if isinstance(x, str): 
        s = x.strip()
        return s or None
    if isinstance(x, dict):
        for k in ("@value","value","label","title","name"):
            v = x.get(k)
            if isinstance(v, str) and v.strip(): return v.strip()
    return None

def _code_from_any(v: Any) -> Optional[str]:
    if isinstance(v, dict):
        for k in ("code","theCode","id","@id","url"):
            if k in v: return _code_from_any(v[k])
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s: return None
        if s.startswith("http"):
            s = s.rstrip("/")
            return s.rsplit("/", 1)[-1] or None
        return s
    return None

def parent_code_from_links(obj: Dict[str, Any]) -> Optional[str]:
    links = obj.get("_links") or obj.get("links") or {}
    if not isinstance(links, dict): return None
    p = links.get("parent")
    href = None
    if isinstance(p, dict):
        href = p.get("href") or p.get("@id") or p.get("id")
    elif isinstance(p, list) and p:
        cand = p[0]
        if isinstance(cand, dict):
            href = cand.get("href") or cand.get("@id") or cand.get("id")
    return _code_from_any(href) if isinstance(href, str) else None

def inline_child_hrefs(obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    links = obj.get("_links") or obj.get("links") or {}
    if isinstance(links, dict):
        ch = links.get("child")
        if isinstance(ch, dict):
            href = ch.get("href") or ch.get("@id") or ch.get("id")
            if isinstance(href, str): out.append(href)
        elif isinstance(ch, list):
            for it in ch:
                if isinstance(it, dict):
                    href = it.get("href") or it.get("@id") or it.get("id")
                    if isinstance(href, str): out.append(href)
    # some payloads include a top-level 'children' array
    ch2 = obj.get("children")
    if isinstance(ch2, list):
        for it in ch2:
            if isinstance(it, dict):
                href = it.get("href") or it.get("@id") or it.get("id")
                if isinstance(href, str): out.append(href)
    return out

def children_endpoint(url: str) -> str:
    return url.rstrip("/") + "/children"

def iter_children_list(url: str, tok: str, page: int) -> Iterable[str]:
    """
    Page through .../children. Items usually carry '@id'/id or href.
    """
    off = 0
    while True:
        u = f"{children_endpoint(url)}?offset={off}&limit={page}"
        obj = api_get(u, tok)
        items = obj.get("items") or obj.get("children") or []
        if isinstance(items, dict): items = [items]
        got = 0
        for it in items:
            got += 1
            href = None
            if isinstance(it, dict):
                href = it.get("href") or it.get("@id") or it.get("id")
            if isinstance(href, str): yield href
        # pagination guards
        total = obj.get("total") or obj.get("count") or None
        if got == 0: break
        off += got
        if total is not None and off >= int(total): break

UPSERT_SQL = """
INSERT INTO ontology.icd11(code, title, definition, parent_code, release, linearization)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (code, release, linearization)
DO UPDATE SET
  title       = EXCLUDED.title,
  definition  = EXCLUDED.definition,
  parent_code = EXCLUDED.parent_code;
"""

ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS ontology.icd11 (
  code           text NOT NULL,
  title          text,
  definition     text,
  parent_code    text,
  release        text,
  linearization  text DEFAULT 'MMS'
);
CREATE UNIQUE INDEX IF NOT EXISTS icd11_uniq_code_rel_lin
  ON ontology.icd11 (code, release, linearization);
CREATE INDEX IF NOT EXISTS icd11_parent_idx
  ON ontology.icd11 (parent_code);
"""

def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(ENSURE_SQL)
    conn.commit()

def crawl(conn, tok: str) -> int:
    """
    BFS over concepts. For each node:
      1) GET detail and upsert
      2) enqueue children from (a) inline links, (b) the paginated .../children endpoint
    """
    seen: set[str] = set()
    q = collections.deque([BASE])
    n = 0
    with conn.cursor() as cur:
        while q:
            url = q.popleft()
            if url in seen: continue
            seen.add(url)

            obj = api_get(url, tok)

            code = _code_from_any(obj.get("code") or obj.get("theCode") or obj.get("id") or obj.get("@id") or obj.get("url")) \
                   or _code_from_any(url)
            title = _textish(obj.get("title") or obj.get("titleSynonym"))
            definition = _textish(obj.get("definition") or obj.get("definitionText") or obj.get("narrative"))
            parent_code = parent_code_from_links(obj)

            if code:
                cur.execute(UPSERT_SQL, (code, title, definition, parent_code, RELEASE, LINEAR))
                n += 1
                if TICK and n % TICK == 0:
                    print(f"inserted {n} …", flush=True)
                if MAX_ROWS and n >= MAX_ROWS:
                    break

            # (a) inline children (if any)
            for href in inline_child_hrefs(obj):
                if isinstance(href, str):
                    if href.startswith("http"): q.append(href)
                    else: q.append(requests.compat.urljoin("https://id.who.int/", href))

            # (b) paginated children endpoint (works even when inline child links are absent)
            for href in iter_children_list(url, tok, PAGE):
                if href.startswith("http"): q.append(href)
                else: q.append(requests.compat.urljoin("https://id.who.int/", href))

    conn.commit()
    return n

def main():
    os.makedirs("server/logs", exist_ok=True)
    print(f">> Loading ICD-11 (REL={RELEASE}) ...", flush=True)
    tok = token()
    # quick root GET to fail fast if headers/creds are wrong
    _ = api_get(BASE, tok)
    with psycopg2.connect(DSN) as conn:
        ensure_schema(conn)
        count = crawl(conn, tok)
        print(f">> DONE rows={count}", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
