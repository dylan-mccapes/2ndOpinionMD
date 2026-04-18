#!/usr/bin/env python3
"""
Smoke-test flows used by **Epistemic Vault** (root ``index.html``), not the React SPA.

Prerequisites
---------------
- API running, e.g. ``uvicorn server.api.app_postgres:app --host 0.0.0.0 --port 8000``
- Postgres + asyncpg pool + ``ehr`` schema (same as normal app)
- Account: **email already verified** (complete registration + verify-email, or mark ``is_verified`` in DB)

Usage::

  python server/scripts/test_epistemic_vault_flow.py --base http://localhost:8000 \\
      --email you@example.com --password 'YourPassword'

Steps exercised
----------------
1. ``GET /api/health``
2. ``POST /api/session/instantiate`` → session token (same as index.html “Start Session”)
3. ``POST /api/timeline/mock-events`` → small mock PTV ingest
4. ``POST /api/journal/entry`` → text journal (+ optional PRO JSON)
5. ``POST /api/timeline/artifact`` → tiny text file as ``patient_artifact`` (no big timeline PDF pipeline)

Open the vault UI at ``{base}/`` or ``{base}/index.html`` (served by the API in dev).
"""
from __future__ import annotations

import argparse
import io
import sys
from typing import Any, Dict

import httpx


def main() -> int:
    p = argparse.ArgumentParser(description="Epistemic Vault API smoke test")
    p.add_argument("--base", default="http://localhost:8000", help="API origin (no trailing slash)")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(timeout=120.0) as client:
        r = client.get(f"{base}/api/health")
        if r.status_code != 200:
            print("health failed:", r.status_code, r.text[:500])
            return 1
        print("health:", r.json())

        r = client.post(
            f"{base}/api/session/instantiate",
            json={"email": args.email, "password": args.password},
        )
        if r.status_code != 200:
            print("session/instantiate failed:", r.status_code, r.text[:800])
            print("Hint: account must be email-verified and password correct.")
            return 1
        sess: Dict[str, Any] = r.json()
        token = sess.get("session_token")
        if not token:
            print("no session_token in response:", sess)
            return 1
        print("session ok, timeline_id:", sess.get("timeline_id"))
        auth = {"Authorization": f"Bearer {token}"}

        r = client.post(
            f"{base}/api/timeline/mock-events",
            headers={**auth, "Content-Type": "application/json"},
            json={
                "events": [
                    {"title": "Script mock — clinic visit", "event_type": "visit"},
                    {"title": "Script mock — lab result", "event_type": "lab"},
                ]
            },
        )
        if r.status_code != 200:
            print("mock-events failed:", r.status_code, r.text[:800])
            return 1
        print("mock-events:", r.json())

        r = client.post(
            f"{base}/api/journal/entry",
            headers={**auth, "Content-Type": "application/json"},
            json={
                "text": "Vault script journal line.",
                "patient_reported_outcomes": [{"instrument": "SCRIPT", "note": "smoke"}],
            },
        )
        if r.status_code != 201:
            print("journal/entry failed:", r.status_code, r.text[:800])
            return 1
        print("journal/entry:", r.json())

        fd = io.BytesIO(b"Sample vault artifact for PTV (text).\nLine 2.\n")
        r = client.post(
            f"{base}/api/timeline/artifact",
            headers=auth,
            files={"file": ("vault_smoke.txt", fd, "text/plain")},
            data={"document_type": "note", "notes": "from test_epistemic_vault_flow.py"},
        )
        if r.status_code != 200:
            print("timeline/artifact failed:", r.status_code, r.text[:800])
            return 1
        print("timeline/artifact:", r.json())

    print("\nDone. Open the vault in a browser:", f"{base}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
