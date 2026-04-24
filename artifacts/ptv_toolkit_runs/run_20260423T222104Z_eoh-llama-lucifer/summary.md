# PTV toolkit harness — eoh-llama-lucifer

- Graph: `C:\2OPMD\2ndOpinionMD-MVP\artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json`
- Graph hash: `f159af9f39d05b6b`
- Questions: 2
- Elapsed: 137.59s

## Aggregate

- Plan emitted:       1/2 (50%)
- Plan route match:   1/2 (50%)
- Expanded query:     1/2
- Primary-tool match: **1/2** (50%)
- Any-tool match:     2/2 (100%)
- Valid evidence ids: 2/2 (100%)
- Keyword-match:      2/2 (100%)

## Per-question

| # | ID | Route exp → obs | Primary exp → obs | Route ✓ | Primary ✓ | Evidence ✓ | Keyword ✓ |
|---|----|------------------|--------------------|---------|-----------|------------|-----------|
| 1 | q02_icd_i10 | `code_lookup` → `None` | `code_index_lookup` → `code_index_lookup` | ❌ | ✅ | ✅ | ✅ |
| 2 | q04_semantic_back_pain | `semantic_then_bfs` → `semantic_then_bfs` | `semantic_search` → `_plan` | ✅ | ❌ | ✅ | ✅ |

## Traces

### q02_icd_i10

> How many events in this chart carry the ICD-10 code I10, and when was it first and last recorded?

Tool-call sequence: `['code_index_lookup', 'semantic_search', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 64.72s

**Answer**

The ICD-10 code I10 was first recorded on 2016-03-07 and last recorded with unknown timestamp. It is associated with hypertension.

**Evidence**: `pdf_p0091_e001`, `pdf_p0091_e0004`, `pdf_p0006_e005`

### q04_semantic_back_pain

> What does this patient's chart say about radiating low back pain?

Tool-call sequence: `['_plan', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 72.87s

**Answer**

The patient has a history of chronic low back pain, which is confirmed by multiple diagnoses and treatments.

**Evidence**: `pdf_p0091_e0002`, `pdf_p0096_e0003`
