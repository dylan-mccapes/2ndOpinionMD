#!/usr/bin/env python3
import asyncio, os
# Reuse the fast generic runner
from embed_rag_source_async import main as _main

if __name__ == "__main__":
    # Let env override, but default to mimic4_note
    os.environ.setdefault("EMBED_SOURCE", "mimic4_note")
    asyncio.run(_main())
