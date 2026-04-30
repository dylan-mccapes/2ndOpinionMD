# FORWARD MKG Batch-10 Rerun Extract Summary

Source JSON: `receipts/receipts/FORWARD_KNOWLEDGE_GR APH_RETRIEVAL_HARNESS_BATCH10_RERUN_20260425.json`

## Batch Metadata
- `n_questions`: `10`
- `elapsed_sec`: `174.637`
- `model`: `eoh-llama`
- `embed_model`: `BAAI/bge-base-en-v1.5`

## First Run (Q1) Extract
- `query`: `First-line therapy for T2DM with CKD considerations`
- `top_k`: `10`
- `sources_filter`: `null` (no source restriction)
- `embed_model`: `BAAI/bge-base-en-v1.5`
- `pilot_slice_source_reference`: present (full pilot source dictionary included in payload)
- `embed_device`: `cuda`
- `embed_sec`: `54.5539`
- `db_sec`: `7.8234`

## Notes
- The run payload confirms GPU path for embedding (`embed_device=cuda`).
- The question-level payload includes both retrieval lanes (`semantic_hits`, `ts_hits`) and overlap diagnostics.
