#!/usr/bin/env python3
import asyncio
import json
import sys

import httpx

API_BASE = "https://2ndopinionmd.ai"

HF_GLP1_QUERY = (
    "In adults with heart failure (with and without type 2 diabetes), "
    "what is the impact of GLP-1 receptor agonists on clinical outcomes "
    "(mortality, HF hospitalization, NYHA class, ejection fraction, and quality of life) "
    "between 2015 and 2025, and how do major guidelines and regulatory bodies currently "
    "position these agents in HF management?"
)

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"{API_BASE}/api/rag/ask",
            params={
                "q": HF_GLP1_QUERY,
                "limit": 10,
                "ctx_k": 24,
                "with_llm": 1,
                "llm_mode": "chunk",
                "use_valyu": 1,
                "valyu_mode": "search",
                "valyu_sources": "valyu/valyu-pubmed",
                "valyu_boost": 3.0,
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    print("=== ai_response ===")
    print(payload.get("answer", "NO answer field; check schema"))

    print("\n=== supporting_documents_by_source ===")
    print(json.dumps(payload.get("supporting_documents_by_source", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(main())

