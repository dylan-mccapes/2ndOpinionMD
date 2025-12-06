# server/scripts/test_valyu_deepsearch.py
"""
Direct Valyu deepsearch smoke tests using valyu_client.search().

This bypasses the router and EoH pipeline, so if something fails here, it's
definitely in valyu_client or Valyu itself.

Usage:
  source server/venv312/bin/activate
  python -m server.scripts.test_valyu_deepsearch
"""

import asyncio
from typing import Any, Dict, List

from server.api import valyu_client

TEST_QUERIES: List[Dict[str, Any]] = [
    {
        "id": "sle_pregnancy_flare",
        "query": "systemic lupus erythematosus flare pregnancy",
        "sources": ["valyu/valyu-pubmed"],
    },
    {
        "id": "ra_treat_to_target",
        "query": "treat to target rheumatoid arthritis guideline TNF inhibitor non-TNF biologic JAK inhibitor",
        "sources": ["valyu/valyu-pubmed"],
    },
    {
        "id": "ra_ild",
        "query": "rheumatoid arthritis associated interstitial lung disease pregnancy DMARD safety",
        "sources": ["valyu/valyu-pubmed"],
    },
    {
        "id": "ckd_glp1_sglt2",
        "query": "CKD type 2 diabetes GLP-1 receptor agonist versus SGLT2 inhibitor kidney outcomes",
        "sources": ["valyu/valyu-pubmed"],
    },
]


async def run_one(case: Dict[str, Any]) -> None:
    print("=" * 80)
    print(f"[{case['id']}] {case['query']}")
    print("-" * 80)

    out = await valyu_client.search(
        case["query"],
        k=3,
        included_sources=case.get("sources"),
        return_contents=True,
        fast_mode=False,
    )

    if not out.get("success"):
        print(f"ERROR: {out.get('error')}  status={out.get('status_code')}")
        body = out.get("body")
        if body:
            print(f"Body keys: {list(body.keys())}")
        return

    meta = out.get("valyu_meta") or {}
    print("tx_id:", meta.get("tx_id"))
    print("total_deduction_dollars:", meta.get("total_deduction_dollars"))
    print("results_by_source:", meta.get("results_by_source"))
    print("-" * 80)

    results = out.get("results", [])
    if not results:
        print("No normalized results returned.")
        return

    for i, r in enumerate(results, start=1):
        print(f"Result {i}:")
        print("  title:", r.get("title"))
        print("  url:", r.get("url"))
        print("  score:", r.get("score"))
        print("  publication_date:", r.get("publication_date"))
        snippet = r.get("snippet") or ""
        print("  snippet:", (snippet[:200] + "...") if len(snippet) > 200 else snippet)
        print()


async def main() -> None:
    for case in TEST_QUERIES:
        await run_one(case)


if __name__ == "__main__":
    asyncio.run(main())
