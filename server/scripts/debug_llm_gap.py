# server/scripts/debug_llm_gap.py

import asyncio
import os
import json

from openai import OpenAI

from server.api.rag_stream_routes import _llm_expand_terms_for_slot  # adjust import if it lives elsewhere

CLIENT = OpenAI()

Q = """
32-year-old woman with pelvic abscess after appendectomy...
(put the exact clinical question text you used here)
""".strip()

SLOT = {
    "vocabulary": "icd10cm",
    "slot_label": "Pelvic abscess",   # or whatever the grader produced
}

BASE_TERMS = [
    "pelvic abscess",
    # include exactly what you see in missing_slots[x]["search_terms"]
]

async def main():
    expanded = await _llm_expand_terms_for_slot(
        q=Q,
        slot=SLOT,
        base_terms=BASE_TERMS,
        model=os.environ.get("CHAT_MODEL", "gpt-4.1-mini"),
    )
    print("=== INPUT ===")
    print("vocab:", SLOT["vocabulary"])
    print("slot_label:", SLOT["slot_label"])
    print("base_terms:", BASE_TERMS)
    print("\n=== OUTPUT expanded_terms ===")
    print(json.dumps(expanded, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
