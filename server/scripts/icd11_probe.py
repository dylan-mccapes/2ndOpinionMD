#!/usr/bin/env python3
import os, requests, json

RELEASE = os.getenv("ICD11_RELEASE", "2024-01")
BASE = f"https://id.who.int/icd/release/11/{RELEASE}/mms"
HEADERS = {"Accept":"application/json","Accept-Language":"en","API-Version":"v2"}

def token():
    r = requests.post(
        "https://icdaccessmanagement.who.int/connect/token",
        headers={"Content-Type":"application/x-www-form-urlencoded"},
        data={"grant_type":"client_credentials","scope":"icdapi_access",
              "client_id":os.getenv("WHO_CLIENT_ID"),
              "client_secret":os.getenv("WHO_CLIENT_SECRET")},
        timeout=30,
    )
    print("token status:", r.status_code)
    print("token body:", r.text[:160], "...")
    r.raise_for_status()
    return r.json()["access_token"]

def main():
    tok = token()
    r = requests.get(BASE, headers={**HEADERS, "Authorization": f"Bearer {tok}"}, timeout=60)
    print("root status:", r.status_code)
    root = r.json()

    # inline link count
    child_links = root.get("_links",{}).get("child")
    if isinstance(child_links, dict): child_links = [child_links]
    inline_count = len(child_links or [])

    # children endpoint meta
    r2 = requests.get(BASE.rstrip("/") + "/children?offset=0&limit=1",
                      headers={**HEADERS, "Authorization": f"Bearer {tok}"}, timeout=60)
    ep_status = r2.status_code
    meta = {}
    try:
        meta = r2.json()
    except Exception:
        pass

    print(json.dumps({
      "release": RELEASE,
      "mms_url": BASE,
      "inline_child_links": inline_count,
      "children_endpoint_status": ep_status,
      "children_endpoint_keys": list(meta.keys()) if isinstance(meta, dict) else "n/a"
    }, indent=2))

if __name__ == "__main__":
    main()
