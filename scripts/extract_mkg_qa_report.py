#!/usr/bin/env python3
"""Extract Q&A summaries and sources from MKG harness receipt text."""

from __future__ import annotations

import re
from pathlib import Path


INPUT_PATH = Path(
    r"c:\2OPMD\2ndOpinionMD-MVP\receipts\FORWARD_KNOWLEDGE_GRAPH_10_QUETION_HARNESS_NASCENT_RUN_20250425.MD"
)
OUT_MD = Path(
    r"c:\2OPMD\2ndOpinionMD-MVP\receipts\FORWARD_MKG_QA_COLLECTION_20250425.md"
)


def main() -> None:
    text = INPUT_PATH.read_text(encoding="utf-8", errors="replace")
    # Parse batch metadata from embedded JSON payload.
    n_questions = re.search(r'"n_questions"\s*:\s*(\d+)', text)
    elapsed = re.search(r'"elapsed_sec"\s*:\s*([0-9.]+)', text)
    model = re.search(r'"model"\s*:\s*"([^"]+)"', text)
    embed_model = re.search(r'"embed_model"\s*:\s*"([^"]+)"', text)

    # Each run ends with "batch_index": N.
    runs = re.findall(
        r'\{\s*"query"\s*:\s*".*?"\s*,.*?"batch_index"\s*:\s*\d+\s*\}',
        text,
        flags=re.S,
    )

    lines: list[str] = []
    lines.append("# FORWARD MKG Q&A Collection")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append(f"- Questions: {n_questions.group(1) if n_questions else len(runs)}")
    lines.append(f"- Elapsed sec: {elapsed.group(1) if elapsed else 'n/a'}")
    lines.append(f"- LLM model: {model.group(1) if model else 'n/a'}")
    lines.append(f"- Embedding model: {embed_model.group(1) if embed_model else 'n/a'}")
    lines.append("")

    for i, block in enumerate(runs, start=1):
        q_m = re.search(r'"query"\s*:\s*"((?:\\.|[^"])*)"', block, flags=re.S)
        q = bytes((q_m.group(1) if q_m else "").replace('\\"', '"'), "utf-8").decode(
            "unicode_escape"
        )

        md_m = re.search(r'"markdown"\s*:\s*"((?:\\.|[^"])*)"', block, flags=re.S)
        if md_m:
            answer = bytes(md_m.group(1), "utf-8").decode("unicode_escape")
        else:
            answer = "_No LLM summary available in this run._"

        sem_block_m = re.search(
            r'"semantic_hits"\s*:\s*\[(.*?)\]\s*,\s*"ts_hits"', block, flags=re.S
        )
        ts_block_m = re.search(
            r'"ts_hits"\s*:\s*\[(.*?)\]\s*,\s*"overlap"', block, flags=re.S
        )
        sem_src = re.findall(
            r'"source"\s*:\s*"([^"]+)"', sem_block_m.group(1) if sem_block_m else ""
        )
        ts_src = re.findall(
            r'"source"\s*:\s*"([^"]+)"', ts_block_m.group(1) if ts_block_m else ""
        )
        sem_sources = list(dict.fromkeys(sem_src))[:5]
        ts_sources = list(dict.fromkeys(ts_src))[:5]

        lines.append(f"## Q{i}: {q}")
        lines.append("")
        lines.append("### Sources Used")
        lines.append(
            "- Semantic top sources: "
            + (", ".join(sem_sources) if sem_sources else "none")
        )
        lines.append(
            "- TS top sources: " + (", ".join(ts_sources) if ts_sources else "none")
        )
        lines.append("")
        lines.append("### LLM Summary")
        lines.append(answer)
        lines.append("")

    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
