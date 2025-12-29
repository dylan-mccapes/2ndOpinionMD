# Evidence for Data layer and storage

- `run_probe.py:0-5` → print(f"⚠️ Vision context skipped: embeddings index is neither list nor dict (type={type(embeddings_raw).__name__}).")
- `run_probe.py:0-5` → # Filter out invalid entries instead of rejecting entire index
- `run_probe.py:0-5` → print(f"⚠️ Dropped {dropped_count} invalid embedding entries from vision index")
- `run_probe.py:0-5` → # Resolve embedding context up-front so we know where the index should land
- `run_probe.py:0-5` → # Create temp filtered index file for embed_incremental.py
- `run_probe.py:0-5` → print(f"🟡 Filtered index: {after}/{before} files retained (ai_probe_index/embeddings_diff.json)")
- `run_probe.py:0-5` → print(f"📦 Resolved index via embedding context: {index_path}")
- `run_probe.py:0-5` → print(f"📦 Resolved index via resolver: {index_path}")
- `run_probe.py:0-5` → print(f"📦 Resolved index via default path: {index_path}")
- `run_probe.py:0-5` → print("⚠️ Index not found after embedding. Provide --index or ensure ai_probe_index/embeddings.json exists. Continuing without vision context.")
- `run_probe.py:0-5` → print("⚠️ Skipping vision query because no index is available.")
- `run_probe_api_docs.sh:0-5` → '{"topic": "Document Event Schema Stability requirements: how SSE event payloads are semi-structured and may evolve, frontend client requirements (tolerate unknown event types, tolerate additional fie
- `run_probe_api_docs.sh:0-5` → "event" "schema" "payload" "optional" "fields" "versioning" \
- `run_setup.py:0-5` → print("  Good: 'fix: correct embedding index format for vision context'")
- `run_coder.py:0-5` → print(f"⏭️  Skipping embedding - index was updated {age_minutes:.1f} minutes ago (recent run_probe?)")
- `invariants/invariant_loader.py:0-5` → raise RuntimeError(f"❌ Invalid invariant at index {i}: missing keys {sorted(missing)}")
- `fmp/agents/triage_agent.py:0-5` → - repo_vision (semantic index of files, entities, responsibilities)
