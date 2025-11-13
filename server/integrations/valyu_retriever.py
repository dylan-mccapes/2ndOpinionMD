import os, asyncio
from typing import Dict, Any

def is_enabled() -> bool:
    return bool(os.getenv("VALYU_API_KEY"))

async def search_valyu(q: str, k: int = 8) -> Dict[str, Any]:
    if not is_enabled():
        return {"matches": [], "meta": {"reason": "no_api_key"}}
    # lazy import so module loads without the SDK installed
    from valyu import Valyu
    client = Valyu(api_key=os.getenv("VALYU_API_KEY"))
    loop = asyncio.get_event_loop()
    def _call():
        return client.search(query=q, max_num_results=k,
                             search_type="proprietary",
                             response_length="short",
                             is_tool_call=True, price_limit=0.50)
    resp = await loop.run_in_executor(None, _call)
    out = []
    for r in resp.get("results", []):
        out.append({
            "id": r.get("id") or r.get("url"),
            "source": "valyu_web",
            "title": r.get("title"),
            "url": r.get("url"),
            "subtype": r.get("source_type"),
            "published": r.get("publication_date"),
            "score": r.get("relevance_score"),
            "content": r.get("content"),
        })
    return {"matches": out, "meta": {
        "tx_id": resp.get("tx_id"),
        "cost": resp.get("total_cost_dollars"),
        "total": resp.get("total_results")
    }}

